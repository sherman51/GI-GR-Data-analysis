import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.express as px


st.title("Outbound Dashboard")

# File uploader
uploaded_file = st.sidebar.file_uploader("Choose a CSV or Excel file", type=['csv', 'xlsx'])

if uploaded_file is not None:
    # Read the file
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, skiprows = 6)
        else:
            df = pd.read_excel(uploaded_file, skiprows = 6)
       
        # Show dataframe
        st.subheader("Preview of Data")
        st.dataframe(df)  # You can also use st.table(df.head()) for a static table

    except Exception as e:
        st.error(f"Error: {e}")


    # Overview of Daily Orders
    
    # Plotly Bar Chart
    fig = px.bar(
        df,
        x='Category',
        y='Sales',
        text='Sales',
        color='Category',
        color_discrete_sequence=px.colors.sequential.Plasma_r,
        title="Fruit Sales Overview",
    )
    
    # Update layout for a modern look
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=14),
        title_x=0.5,
        margin=dict(l=40, r=40, t=60, b=40),
    )
    
    # Add value labels
    fig.update_traces(texttemplate='%{text}', textposition='outside')
    
    # Display chart in Streamlit
    st.plotly_chart(fig, use_container_width=True)








