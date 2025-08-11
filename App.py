import streamlit as st
import pandas as pd
import numpy as np
import datetime

uploaded_file = st.sidebar.file_uploader("Choose an XLSX file", type=['xlsx'])

if uploaded_file:

    df_raw = pd.read_excel(uploaded_file, skiprows=5)
    st.table(df_raw)


    





