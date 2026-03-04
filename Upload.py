import streamlit as st
import pandas as pd
from google.cloud import storage
from google.oauth2 import service_account
from datetime import datetime
import pytz

# --- GCP Authentication ---
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
bucket_name = "testbucket352"  # Replace with your actual bucket name

# Initialize GCS client
client = storage.Client(credentials=credentials, project=st.secrets["gcp_service_account"]["project_id"])
bucket = client.bucket(bucket_name)

st.title("📁 Upload Excel Files to Dashboard")

# --- Last Upload Tracker Function ---
def get_last_upload_info(bucket, workstream):
    """Get the last uploaded file info for a workstream"""
    blobs = list(bucket.list_blobs(prefix=workstream))

    if not blobs:
        return None, None

    # Get the most recently updated blob
    latest_blob = max(blobs, key=lambda b: b.updated)

    # Convert to Singapore timezone
    sg_tz = pytz.timezone('Asia/Singapore')
    upload_time = latest_blob.updated.astimezone(sg_tz)

    return latest_blob.name, upload_time

# --- Workstream Label Section ---
st.header("Workstream Label")
workstream_label = st.selectbox("Choose your workstream", ["aircon", "coldroom"])

# --- Display Last Upload Info ---
st.markdown("---")
last_file, last_time = get_last_upload_info(bucket, workstream_label)

if last_file and last_time:
    st.markdown("**📂 Last Uploaded File:**")
    st.text_input(
        "Last Uploaded File",
        value=last_file,
        disabled=True,
        label_visibility="collapsed",
        key="filename_display"
    )

    col1, col2 = st.columns(2)
    with col1:
        st.metric("📅 Upload Date", last_time.strftime("%d %b %Y"))
    with col2:
        st.metric("🕐 Upload Time", last_time.strftime("%I:%M:%S %p"))
else:
    st.info(f"ℹ️ No files found for {workstream_label.capitalize()} workstream")

st.markdown("---")

# --- Upload Section ---
st.header(f"Upload Excel File for {workstream_label.capitalize()} Workstream (.xls or .xlsx)")
uploaded_file = st.file_uploader(
    f"Choose an Excel file for {workstream_label.capitalize()} workstream",
    type=["xls", "xlsx"]
)

if uploaded_file is not None:
    original_file_name = uploaded_file.name  # Get the original file name

    # Automatically prepend the workstream label to the file name
    file_name = f"{workstream_label}-{original_file_name}"

    try:
        # ✅ FIX: Detect true file format by sniffing raw bytes (not just extension)
        raw_bytes = uploaded_file.read()
        uploaded_file.seek(0)  # Reset after sniffing

        # Detect actual format from file signature / content
        is_xlsx_zip = raw_bytes[:4] == b'PK\x03\x04'                        # ZIP = real .xlsx
        is_xls_biff = raw_bytes[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1' # BIFF = real .xls
        is_xml_html = raw_bytes[:20].lower().strip().startswith((            # XML/HTML disguised as .xls
            b'<?xml', b'<html', b'\r\n<xml', b'\n<xml', b'<xml'
        ))

        if is_xlsx_zip or original_file_name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file, engine="openpyxl")
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif is_xls_biff:
            df = pd.read_excel(uploaded_file, engine="xlrd")
            content_type = "application/vnd.ms-excel"
        elif is_xml_html:
            # XML/HTML disguised as .xls — read as HTML table
            import io
            tables = pd.read_html(io.BytesIO(raw_bytes))
            if not tables:
                st.error("❌ Could not find any table data in the file.")
                st.stop()
            df = tables[0]
            content_type = "application/vnd.ms-excel"
        else:
            st.error("❌ Unsupported or corrupt file format. Please upload a valid .xls or .xlsx file.")
            st.stop()

        st.subheader("📊 Preview of uploaded data:")
        st.dataframe(df.head())  # Show preview

        # Upload to GCS with the new name
        uploaded_file.seek(0)  # Reset buffer
        blob = bucket.blob(file_name)
        blob.upload_from_file(uploaded_file, content_type=content_type)
        st.success(f"✅ Uploaded '{file_name}' to Google Cloud Storage.")

        # --- Remove existing workstream-related files ---
        st.info(f"🧹 Cleaning up old {workstream_label} file(s) in the bucket...")

        blobs = bucket.list_blobs(prefix=workstream_label)
        deleted_count = 0
        for b in blobs:
            if b.name.startswith(workstream_label) and b.name != file_name:
                b.delete()
                deleted_count += 1

        st.success(f"✅ Deleted {deleted_count} old {workstream_label} file(s) from the bucket.")

        # Refresh the page to show updated last upload info
        st.rerun()

    except Exception as e:
        st.error(f"❌ Failed to read or upload Excel file: {e}")
