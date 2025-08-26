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

# --- Workstream Label Section ---
st.header("Workstream Label")
workstream_label = st.selectbox("Choose your workstream", ["coldroom", "aircon"])

# --- Upload Section ---
st.header(f"Upload Excel File for {workstream_label.capitalize()} Workstream (.xls or .xlsx)")
uploaded_file = st.file_uploader(f"Choose an Excel file for {workstream_label.capitalize()} workstream", type=["xls", "xlsx"])

if uploaded_file is not None:
    file_name = uploaded_file.name  # Get the original file name

    # Check if file name starts with the selected workstream label
    if not file_name.lower().startswith(f"{workstream_label}-"):
        st.error(f"File name must start with '{workstream_label}-'. Please rename your file and try again.")
    else:
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

            # --- Remove existing workstream-related file ---
            st.info(f"Cleaning up old {workstream_label} file in the bucket...")
            blobs = bucket.list_blobs(prefix=workstream_label)  # List blobs with the workstream prefix
            deleted_count = 0
            for b in blobs:
                if b.name != file_name:  # Don't delete the newly uploaded file
                    b.delete()
                    deleted_count += 1

            st.success(f"Deleted {deleted_count} old {workstream_label} file(s) from the bucket.")

        except Exception as e:
            st.error(f"Failed to read or upload Excel file: {e}")
