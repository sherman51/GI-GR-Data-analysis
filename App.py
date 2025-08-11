import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.express as px

st.title("Outbound Dashboard")

# File uploader
uploaded_file = st.sidebar.file_uploader("Choose a CSV or Excel file", type=['csv', 'xlsx'])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, skiprows=6)
        else:
            df = pd.read_excel(uploaded_file, skiprows=6)

        st.subheader("Preview of Data")
        st.dataframe(df)



    except Exception as e:
        st.error(f"Error reading file: {e}")


