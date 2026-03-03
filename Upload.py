import streamlit as st
import pandas as pd
from google.cloud import storage
from google.oauth2 import service_account
from datetime import datetime
import pytz
import re

# --- GCP Authentication ---
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
bucket_name = "testbucket352"

# Initialize GCS client
client = storage.Client(credentials=credentials, project=st.secrets["gcp_service_account"]["project_id"])
bucket = client.bucket(bucket_name)

st.title("📁 Upload Excel Files to Dashboard")

# --- Keyword Matching Function ---
def normalize(text):
    """Lowercase and remove spaces/special chars for fuzzy matching"""
    return re.sub(r'[^a-z0-9]', '', text.lower())

def find_matching_blob(bucket, workstream, uploaded_filename):
    """
    Find an existing blob in the bucket whose name matches the uploaded file
    based on shared keywords (case-insensitive, space/symbol-insensitive).
    e.g. uploaded 'GIanalysis.xlsx' matches existing 'aircon-GI analysis.xlsx'
    """
    blobs = list(bucket.list_blobs(prefix=workstream))
    normalized_upload = normalize(uploaded_filename)

    for blob in blobs:
        normalized_blob = normalize(blob.name)
        # Check if either filename contains the other (after normalization)
        if normalized_upload in normalized_blob or normalized_blob in normalized_upload:
            return blob
    return None

# --- Last Upload Tracker Function ---
def get_last_upload_info(bucket, workstream):
    """Get the last uploaded file info for a workstream"""
    blobs = list(bucket.list_blobs(prefix=workstream))
    if not blobs:
        return None, None
    latest_blob = max(blobs, key=lambda b: b.updated)
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
st.header(f"Upload Excel Files for {workstream_label.capitalize()} Workstream (.xls or .xlsx)")

uploaded_files = st.file_uploader(
    f"Choose Excel file(s) for {workstream_label.capitalize()} workstream",
    type=["xls", "xlsx"],
    accept_multiple_files=True
)

if uploaded_files:
    for uploaded_file in uploaded_files:
        original_file_name = uploaded_file.name
        file_name = f"{workstream_label}-{original_file_name}"

        try:
            if original_file_name.endswith(".xls"):
                df = pd.read_excel(uploaded_file, engine="xlrd")  # xlrd handles legacy .xls binary format
                content_type = "application/vnd.ms-excel"
            elif original_file_name.endswith(".xlsx"):
                df = pd.read_excel(uploaded_file, engine="openpyxl")
                content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            else:
                st.error(f"❌ Unsupported file format: {original_file_name}")
                continue

            st.subheader(f"📊 Preview: {original_file_name}")
            st.dataframe(df.head())

            # Upload to GCS
            uploaded_file.seek(0)
            blob = bucket.blob(file_name)
            blob.upload_from_file(uploaded_file, content_type=content_type)
            st.success(f"✅ Uploaded '{file_name}' to Google Cloud Storage.")

            # --- ✅ Delete only the matching old file ---
            matching_blob = find_matching_blob(bucket, workstream_label, original_file_name)
            if matching_blob and matching_blob.name != file_name:
                matching_blob.delete()
                st.success(f"🗑️ Deleted old matching file: '{matching_blob.name}'")
            elif matching_blob and matching_blob.name == file_name:
                st.info(f"ℹ️ No old file to delete — '{file_name}' was overwritten in place.")
            else:
                st.info(f"ℹ️ No matching old file found to delete for '{original_file_name}'.")

        except Exception as e:
            st.error(f"❌ Failed to process '{original_file_name}': {e}")

    st.rerun()
