import streamlit as st
import pandas as pd
from google.cloud import storage
from google.oauth2 import service_account
import pytz
import re

# --- GCP Authentication ---
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)

bucket_name = "testbucket352"

client = storage.Client(
    credentials=credentials,
    project=st.secrets["gcp_service_account"]["project_id"]
)

bucket = client.bucket(bucket_name)

st.title("📁 Upload Excel Files to Dashboard")

# --- Keyword Matching Function ---
def normalize(text):
    """Lowercase and remove spaces/special chars for fuzzy matching"""
    return re.sub(r'[^a-z0-9]', '', text.lower())

# --- Last Upload Tracker Function ---
def get_last_upload_info(bucket, workstream):
    blobs = list(bucket.list_blobs(prefix=workstream))
    if not blobs:
        return None, None

    latest_blob = max(blobs, key=lambda b: b.updated)

    sg_tz = pytz.timezone("Asia/Singapore")
    upload_time = latest_blob.updated.astimezone(sg_tz)

    return latest_blob.name, upload_time

# --- Workstream Label Section ---
st.header("Workstream Label")

workstream_label = st.selectbox(
    "Choose your workstream",
    ["aircon", "coldroom"]
)

# --- Display Last Upload Info ---
st.markdown("---")

last_file, last_time = get_last_upload_info(bucket, workstream_label)

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
    st.info(f"ℹ️ No files found for {workstream_label.capitalize()} workstream")

st.markdown("---")

# --- Upload Section ---
st.header(
    f"Upload Excel Files for {workstream_label.capitalize()} Workstream (.xls or .xlsx)"
)

uploaded_files = st.file_uploader(
    f"Choose Excel file(s) for {workstream_label.capitalize()} workstream",
    type=["xls", "xlsx"],
    accept_multiple_files=True
)

if uploaded_files:
    for uploaded_file in uploaded_files:

        original_file_name = uploaded_file.name
        file_extension = original_file_name.lower().split(".")[-1]
        file_name = f"{workstream_label}-{original_file_name}"

        try:
            # --------------------------------------------------
            # 1️⃣ Read Excel (Handles BOTH .xls and .xlsx)
            # --------------------------------------------------
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file, engine="calamine")

            # --------------------------------------------------
            # 2️⃣ Set Correct Content Type
            # --------------------------------------------------
            if file_extension == "xls":
                content_type = "application/vnd.ms-excel"
            elif file_extension == "xlsx":
                content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            else:
                st.error(f"❌ Unsupported file format: {original_file_name}")
                continue

            # --------------------------------------------------
            # 3️⃣ Preview
            # --------------------------------------------------
            st.subheader(f"📊 Preview: {original_file_name}")
            st.dataframe(df.head())

            # --------------------------------------------------
            # 4️⃣ Upload to GCS
            # --------------------------------------------------
            uploaded_file.seek(0)
            blob = bucket.blob(file_name)
            blob.upload_from_file(uploaded_file, content_type=content_type)

            st.success(f"✅ Uploaded '{file_name}' to Google Cloud Storage.")

            # --------------------------------------------------
            # 5️⃣ Delete Old Matching File (Safer Logic)
            # --------------------------------------------------
            blobs = list(bucket.list_blobs(prefix=workstream_label))
            normalized_upload = normalize(original_file_name)

            for old_blob in blobs:

                # Skip the file we just uploaded
                if old_blob.name == file_name:
                    continue

                normalized_blob = normalize(old_blob.name)

                if (
                    normalized_upload in normalized_blob
                    or normalized_blob in normalized_upload
                ):
                    old_blob.delete()
                    st.success(f"🗑️ Deleted old matching file: '{old_blob.name}'")
                    break
            else:
                st.info("ℹ️ No matching old file found.")

        except Exception as e:
            st.error(f"❌ Failed to process '{original_file_name}': {e}")

    st.rerun()
