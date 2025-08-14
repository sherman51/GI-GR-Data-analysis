import streamlit as st
import os

UPLOAD_DIR = r"C:\Users\ShermanANG\OneDrive - Singapore Storage & Warehouse Pte Ltd\Dashboardupload test"
os.makedirs(UPLOAD_DIR, exist_ok=True)

st.title("📤 Upload Excel File")
uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])

if uploaded_file:
    # Save the file to shared location
    save_path = os.path.join(UPLOAD_DIR, "latest.xlsx")
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success(f"Uploaded and saved as 'latest.xlsx'")

