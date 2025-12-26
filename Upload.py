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

# --- Custom CSS for filename display ---
st.markdown("""
<style>
    .filename-display {
        background-color: #f0f2f6;
        padding: 12px;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
        word-wrap: break-word;
        overflow-wrap: break-word;
        white-space: normal;
        font-family: monospace;
        font-size: 14px;
        line-height: 1.5;
    }
    .metric-label {
        font-size: 14px;
        font-weight: 600;
        color: #555;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

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
    # Display filename in a scrollable/wrappable container
    st.markdown('<div class="metric-label">📂 Last Uploaded File</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="filename-display">{last_file}</div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Display date and time in columns
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
uploaded_file = st.file_uploader(f"Choose an Excel file for {workstream_label.capitalize()} workstream", type=["xls", "xlsx"])

if uploaded_file is not None:
    original_file_name = uploaded_file.name  # Get the original file name
    
    # Automatically prepend the workstream label to the file name
    file_name = f"{workstream_label}-{original_file_name}"
    
    try:
        # Read file using correct engine
        if file_name.endswith(".xls"):
            df = pd.read_excel(uploaded_file, engine="openpyxl")
            content_type = "application/vnd.ms-excel"
        elif file_name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file, engine="openpyxl")
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            st.error("Unsupported file format!")
            st.stop()
        
        st.subheader("📊 Preview of uploaded data:")
        st.dataframe(df.head())  # Show preview
        
        # Upload to GCS with the new name
        uploaded_file.seek(0)  # Reset buffer
        blob = bucket.blob(file_name)
        blob.upload_from_file(uploaded_file, content_type=content_type)
        st.success(f"✅ Uploaded '{file_name}' to Google Cloud Storage.")
        
        # --- Remove existing workstream-related file ---
        st.info(f"🧹 Cleaning up old {workstream_label} file in the bucket...")
        
        # List blobs with the workstream prefix
        blobs = bucket.list_blobs(prefix=workstream_label)
        deleted_count = 0
        for b in blobs:
            # Delete only the file that matches the prefix and is NOT the newly uploaded file
            if b.name.startswith(workstream_label) and b.name != file_name:
                b.delete()
                deleted_count += 1
        
        st.success(f"✅ Deleted {deleted_count} old {workstream_label} file(s) from the bucket.")
        
        # Refresh the page to show updated last upload info
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Failed to read or upload Excel file: {e}")
