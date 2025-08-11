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

        # Check if required columns exist
        required_columns = ['ExpDate', 'Priority']
        if all(col in df.columns for col in required_columns):
            fig = px.bar(
                df,
                x='ExpDate',
                y='Priority',
                text='Priority',
                color='ExpDate',
                color_discrete_sequence=px.colors.sequential.Plasma_r,
                title="Fruit Priority Overview",
            )

            fig.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(size=14),
                title_x=0.5,
                margin=dict(l=40, r=40, t=60, b=40),
            )

            fig.update_traces(texttemplate='%{text}', textposition='outside')

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("The uploaded file must contain 'ExpDate' and 'Priority' columns.")

    except Exception as e:
        st.error(f"Error reading file: {e}")

