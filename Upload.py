import streamlit as st
import os

UPLOAD_DIR = "shared_uploads"

uploaded_file = st.file_uploader("Upload your file")
if uploaded_file:
    with open(os.path.join(UPLOAD_DIR, uploaded_file.name), "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success("File uploaded!")
