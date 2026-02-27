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
client = storage.Client(
    credentials=credentials,
    project=st.secrets["gcp_service_account"]["project_id"]
)
bucket = client.bucket(bucket_name)

st.title("📁 Upload Excel Files to Dashboard")

# --- Last Upload Tracker Function (Entire Bucket) ---
def get_last_upload_info(bucket):
    """Get the most recently uploaded file in the bucket"""
    blobs = list(bucket.list_blobs())

    if not blobs:
        return None, None

    latest_blob = max(blobs, key=lambda b: b.updated)

    # Convert to Singapore timezone
    sg_tz = pytz.timezone("Asia/Singapore")
    upload_time = latest_blob.updated.astimezone(sg_tz)

    return latest_blob.name, upload_time


# --- Display Last Upload Info ---
st.markdown("---")
last_file, last_time = get_last_upload_info(bucket)

if last_file and last_time:
    st.markdown("**📂 Last Uploaded File:**")
    st.text_input(
        "Last Uploaded File",
        value=last_file,
        disabled=True,
        label_visibility="collapsed"
    )

    col1, col2 = st.columns(2)
    with col1:
        st.metric("📅 Upload Date", last_time.strftime("%d %b %Y"))
    with col2:
        st.metric("🕐 Upload Time", last_time.strftime("%I:%M:%S %p"))
else:
    st.info("ℹ️ No files found in the bucket")

st.markdown("---")

# --- Upload Section ---
st.header("Upload Excel File (.xls or .xlsx)")
uploaded_file = st.file_uploader(
    "Choose an Excel file",
    type=["xls", "xlsx"]
)

if uploaded_file is not None:
    original_file_name = uploaded_file.name  # Keep original name

    try:
        # Read file using correct engine
        if original_file_name.endswith(".xls"):
            df = pd.read_excel(uploaded_file, engine="openpyxl")
            content_type = "application/vnd.ms-excel"
        elif original_file_name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file, engine="openpyxl")
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            st.error("Unsupported file format!")
            st.stop()

        st.subheader("📊 Preview of uploaded data:")
        st.dataframe(df.head())

        # Upload to GCS with original file name
        uploaded_file.seek(0)
        blob = bucket.blob(original_file_name)
        blob.upload_from_file(uploaded_file, content_type=content_type)

        st.success(f"✅ Uploaded '{original_file_name}' to Google Cloud Storage.")

        # Refresh page to update last upload info
        st.rerun()

    except Exception as e:
        st.error(f"❌ Failed to read or upload Excel file: {e}")
