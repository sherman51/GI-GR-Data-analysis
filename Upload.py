import streamlit as st
import pandas as pd
from google.cloud import storage
from google.oauth2 import service_account

# --- GCP Authentication ---
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
bucket_name = "testbucket352"  # Replace with your actual bucket name

# Initialize GCS client
client = storage.Client(credentials=credentials, project=st.secrets["gcp_service_account"]["project_id"])
bucket = client.bucket(bucket_name)

st.title("📁 Upload Excel Files to Dashboard")

# --- Upload Section ---
st.header("Upload Excel File (.xls or .xlsx)")
uploaded_file = st.file_uploader("Choose an Excel file", type=["xls", "xlsx"])

if uploaded_file is not None:
    file_name = uploaded_file.name

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

        st.dataframe(df.head())  # Show preview

        # Upload to GCS
        uploaded_file.seek(0)  # Reset buffer
        blob = bucket.blob(file_name)
        blob.upload_from_file(uploaded_file, content_type=content_type)

        st.success(f"Uploaded '{file_name}' to Google Cloud Storage.")

        # --- Delete all other blobs except the newly uploaded one ---
        st.info("Cleaning up old files in the bucket...")
        blobs = bucket.list_blobs()
        deleted_count = 0
        for b in blobs:
            if b.name != file_name:
                b.delete()
                deleted_count += 1

        st.success(f"Deleted {deleted_count} old file(s) from the bucket.")

    except Exception as e:
        st.error(f"Failed to read or upload Excel file: {e}")

