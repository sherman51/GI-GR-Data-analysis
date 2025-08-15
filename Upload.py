import streamlit as st
import pandas as pd
from google.cloud import storage
from google.oauth2 import service_account
from tempfile import NamedTemporaryFile

# --- GCP Authentication ---
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
bucket_name = "testbucket352"  # Replace with your actual bucket name

# Initialize GCS client
client = storage.Client(credentials=credentials, project=st.secrets["gcp_service_account"]["project_id"])
bucket = client.bucket(bucket_name)

st.title("📁 Upload and Download Excel Files to Google Cloud Storage")

# --- Upload Section ---
st.header("Upload Excel File (.xls or .xlsx)")
uploaded_file = st.file_uploader("Choose an Excel file", type=["xls", "xlsx"])

if uploaded_file is not None:
    file_name = uploaded_file.name

    try:
        # Try to read the file to verify it's a valid Excel
        if file_name.endswith(".xls"):
            df = pd.read_excel(uploaded_file, engine="xlrd")
        else:
            df = pd.read_excel(uploaded_file, engine="openpyxl")

        st.dataframe(df.head())  # Show preview

        # Upload to GCS
        uploaded_file.seek(0)  # Reset buffer
        blob = bucket.blob(file_name)
        blob.upload_from_file(uploaded_file, content_type="application/vnd.ms-excel")

        st.success(f"Uploaded '{file_name}' to Google Cloud Storage.")
    except Exception as e:
        st.error(f"Failed to read or upload Excel file: {e}")

# --- Download Section ---
st.header("Download Excel File from GCS")

# List available Excel files in bucket
blobs = list(bucket.list_blobs())
excel_files = [blob.name for blob in blobs if blob.name.endswith((".xls", ".xlsx"))]

if excel_files:
    selected_file = st.selectbox("Select a file to download", excel_files)

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
    st.info("No Excel files found in the bucket.")

