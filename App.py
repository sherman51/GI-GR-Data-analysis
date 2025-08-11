import streamlit as st
import pandas as pd
import numpy as np
import datetime


st.title("Outbound Dashboard")

# File uploader
uploaded_file = st.sidebar.file_uploader("Choose a CSV or Excel file", type=['csv', 'xlsx'])

if uploaded_file is not None:
    # Read the file
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Show dataframe
        st.subheader("Preview of Data")
        st.dataframe(df)  # You can also use st.table(df.head()) for a static table

    except Exception as e:
        st.error(f"Error: {e}")

    






