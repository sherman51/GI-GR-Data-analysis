import streamlit as st
import os
import base64
import requests
from io import StringIO
import pandas as pd

# Replace with your GitHub info
GITHUB_USERNAME = "sherman51"
GITHUB_REPO = "GI-GR-Data-analysis"
GITHUB_ACCESS_TOKEN = "your_personal_access_token_here"  # Optional for private repos

# Function to upload a file to GitHub
def upload_to_github(file_name, file_content):
    """
    Uploads a file to a GitHub repository using the GitHub API.
    """
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{file_name}"
    
    # Create the content in base64 encoding
    content = base64.b64encode(file_content.encode()).decode()

    # Prepare the payload for GitHub API
    payload = {
        "message": f"Upload {file_name}",
        "content": content
    }

    # Optional: Add authentication for private repos
    headers = {
        "Authorization": f"token {GITHUB_ACCESS_TOKEN}",
    }

    # Send the request to GitHub API
    response = requests.put(url, json=payload, headers=headers)

    if response.status_code == 201:
        st.success(f"File '{file_name}' uploaded successfully to GitHub!")
        return True
    else:
        st.error(f"Failed to upload file: {response.json()['message']}")
        return False

# Streamlit app
st.title("Upload File to GitHub")

# File uploader widget
uploaded_file = st.file_uploader("Choose a file", type=["csv", "txt", "xlsx"])

if uploaded_file:
    try:
        # Try to read the file content as a string (for CSV or text files)
        file_name = uploaded_file.name
        file_content = uploaded_file.getvalue().decode("utf-8", errors='ignore')  # Graceful handling of errors
        
        # Upload the file to GitHub
        if upload_to_github(file_name, file_content):
            # Read the file into a pandas DataFrame for display
            if file_name.endswith(".csv"):
                data = pd.read_csv(StringIO(file_content))
                st.write(data)
            elif file_name.endswith(".xlsx"):
                data = pd.read_excel(StringIO(file_content))
                st.write(data)
            else:
                st.text("Uploaded file content is not displayed as it's not a CSV or Excel file.")
    except Exception as e:
        st.error(f"Error reading the file: {str(e)}")
