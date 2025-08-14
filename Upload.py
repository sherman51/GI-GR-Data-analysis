import streamlit as st
import boto3
from io import BytesIO

# AWS S3 client
s3 = boto3.client('s3')

# Streamlit UI
st.title("Upload File to S3")

uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file:
    # Convert file-like object to binary (BytesIO)
    file_bytes = BytesIO(uploaded_file.read())

    # Set the S3 bucket name and desired S3 file path
    bucket_name = "your-bucket-name"
    file_path = f"uploads/{uploaded_file.name}"

    try:
        # Upload file to S3
        s3.upload_fileobj(file_bytes, bucket_name, file_path)
        st.success(f"File uploaded successfully to {file_path} in S3!")
    except Exception as e:
        st.error(f"Failed to upload file: {e}")
