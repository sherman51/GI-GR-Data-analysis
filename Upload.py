import streamlit as st
import pandas as pd
import io
import re
from google.cloud import storage
from google.oauth2 import service_account
import pytz

# --- GCP Authentication ---
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
bucket_name = "testbucket352"

# Initialize GCS client
client = storage.Client(
    credentials=credentials,
    project=st.secrets["gcp_service_account"]["project_id"]
)
bucket = client.bucket(bucket_name)

st.title("📁 Upload Excel Files to Dashboard")

# --- Last Upload Tracker Function ---
def get_last_upload_info(bucket):
    """Get the last uploaded file info for any file in bucket"""
    blobs = list(bucket.list_blobs())
    if not blobs:
        return None, None
    latest_blob = max(blobs, key=lambda b: b.updated)
    sg_tz = pytz.timezone('Asia/Singapore')
    upload_time = latest_blob.updated.astimezone(sg_tz)
    return latest_blob.name, upload_time

# --- SpreadsheetML Parser ---
def parse_spreadsheetml(raw_bytes):
    from lxml import etree
    content = raw_bytes.decode('utf-8', errors='replace')
    content = re.sub(r'^.*?(<Workbook)', r'\1', content, flags=re.DOTALL)
    content = re.sub(
        r'xmlns:x="urn:schemas-\s+microsoft-com:office:excel"',
        'xmlns:x="urn:schemas-microsoft-com:office:excel"',
        content
    )
    content = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', content)
    tree = etree.fromstring(content.encode('utf-8'))
    ns = 'urn:schemas-microsoft-com:office:spreadsheet'
    rows = tree.findall(f'.//{{{ns}}}Row')
    if not rows:
        raise ValueError("No rows found in SpreadsheetML file.")
    data = []
    for row in rows:
        cells = row.findall(f'.//{{{ns}}}Data')
        data.append([c.text if c.text else '' for c in cells])
    if not data:
        raise ValueError("Parsed rows but found no cell data.")
    df = pd.DataFrame(data[1:], columns=data[0])
    return df

# --- Read Excel File ---
def read_excel_file(uploaded_file, original_file_name):
    raw_bytes = uploaded_file.read()
    uploaded_file.seek(0)

    is_xlsx = raw_bytes[:4] == b'PK\x03\x04'
    is_biff = raw_bytes[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
    is_xml  = (b'<Workbook' in raw_bytes[:500] or b'spreadsheet' in raw_bytes[:500].lower())

    if is_xlsx or original_file_name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file, engine="openpyxl")
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif is_biff:
        df = pd.read_excel(uploaded_file, engine="xlrd")
        content_type = "application/vnd.ms-excel"
    elif is_xml:
        df = parse_spreadsheetml(raw_bytes)
        content_type = "application/vnd.ms-excel"
    else:
        raise ValueError(
            "Unrecognised file format. Please upload a valid .xls or .xlsx file."
        )
    return df, content_type

# --- Workstream Selection ---
st.header("Workstream Label")
workstream_label = st.selectbox("Choose your workstream", ["aircon", "coldroom"])

# --- Display Last Upload Info ---
st.markdown("---")
last_file, last_time = get_last_upload_info(bucket)
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
    st.info("ℹ️ No files found in the bucket")

st.markdown("---")

# --- Upload Section ---
st.header(f"Upload Excel File for {workstream_label.capitalize()} Workstream (.xls or .xlsx)")
uploaded_file = st.file_uploader(
    f"Choose an Excel file for {workstream_label.capitalize()} workstream",
    type=["xls", "xlsx"]
)

if uploaded_file is not None:
    original_file_name = uploaded_file.name
    file_name = f"{workstream_label}-{original_file_name}"

    try:
        df, content_type = read_excel_file(uploaded_file, original_file_name)

        st.subheader("📊 Preview of uploaded data:")
        st.dataframe(df.head())
        st.caption(f"Total rows: {len(df):,} | Columns: {len(df.columns)}")

        # --- Upload new file ---
        uploaded_file.seek(0)
        blob = bucket.blob(file_name)
        blob.upload_from_file(uploaded_file, content_type=content_type)
        st.success(f"✅ Uploaded '{file_name}' to Google Cloud Storage.")

        # --- Cleanup old files containing 'GI' or 'Count' ---
        st.info("🧹 Cleaning up old files containing 'GI' or 'Count'...")
        blobs = list(bucket.list_blobs())
        deleted_count = 0

        for b in blobs:
            if b.name == file_name:
                continue  # skip the newly uploaded file
            if ("gi" in b.name.lower()) or ("count" in b.name.lower()):
                b.delete()
                deleted_count += 1

        st.success(f"✅ Deleted {deleted_count} old file(s) containing 'GI' or 'Count'.")

        st.rerun()

    except Exception as e:
        st.error(f"❌ Failed to read or upload Excel file: {e}")
