import streamlit as st
import pandas as pd
from google.cloud import storage
import os
from tempfile import NamedTemporaryFile

# Load service account key
GCP_SERVICE_ACCOUNT_JSON = "path/to/your-service-account.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GCP_SERVICE_ACCOUNT_JSON

# Set your bucket name
BUCKET_NAME = "your-bucket-name"

# Initialize GCS client
client = storage.Client()
bucket = client.bucket(BUCKET_NAME)

st.title("📁 Upload and Download Excel Files to Google Cloud Storage")

# --- File Upload ---
st.header("Upload Excel File (.xls or .xlsx)")
uploaded_file = st.file_uploader("Choose an Excel file", type=["xls", "xlsx"])

if uploaded_file is not None:
    file_name = uploaded_file.name
    # Validate Excel by trying to read
    try:
        if file_name.endswith(".xls"):
            df = pd.read_excel(uploaded_file, engine="xlrd")
        else:
            df = pd.read_excel(uploaded_file, engine="openpyxl")

        st.dataframe(df.head())  # Show preview

        # Upload to GCS
        blob = bucket.blob(file_name)
        uploaded_file.seek(0)  # Reset buffer
        blob.upload_from_file(uploaded_file, content_type="application/vnd.ms-excel")
        st.success(f"Uploaded '{file_name}' to Google Cloud Storage.")
    except Exception as e:
        st.error(f"Failed to process Excel file: {e}")

# --- File Retrieval ---
st.header("Download Excel File from GCS")

# List files
blobs = list(bucket.list_blobs())
excel_files = [b.name for b in blobs if b.name.endswith((".xls", ".xlsx"))]

if excel_files:
    selected_file = st.selectbox("Select file to download", excel_files)

    if st.button("Download"):
        blob = bucket.blob(selected_file)
        with NamedTemporaryFile(delete=False) as temp:
            blob.download_to_filename(temp.name)
            with open(temp.name, "rb") as f:
                st.download_button(
                    label="Click to download",
                    data=f,
                    file_name=selected_file,
                    mime="application/vnd.ms-excel"
                )
else:
    st.info("No Excel files found in bucket.")
