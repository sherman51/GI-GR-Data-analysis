from datetime import datetime, date, timedelta
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ------------------------ FILE UPLOAD ------------------------
uploaded_file = st.sidebar.file_uploader("Upload Excel File", type=["xlsx"])

# Define the 3 dates for selection
today = date.today()
tomorrow = today + timedelta(days=1)
day_after_tomorrow = today + timedelta(days=2)

date_options = [today, tomorrow, day_after_tomorrow]
date_labels = [d.strftime('%d %b %Y') for d in date_options]

# Sidebar selectbox for date selection
selected_label = st.sidebar.selectbox("Select ExpDate to Filter", date_labels, index=0)
selected_date = date_options[date_labels.index(selected_label)]

if uploaded_file:
    # Skip metadata rows, header starts on row 6 (index 5)
    df_raw = pd.read_excel(uploaded_file, skiprows=5)

    # Clean up
    df = df_raw.dropna(axis=1, how="all")  # Remove empty columns
    df.dropna(how="all", inplace=True)     # Remove empty rows

    # Ensure 'ExpDate' is datetime
    df['ExpDate'] = pd.to_datetime(df['ExpDate'], errors='coerce')

    # Filter dataframe by selected date (only date part)
    df1 = df[df['ExpDate'].dt.date == selected_date]

    # Make sure to handle empty filtered data
    if df1.empty:
        st.warning(f"No data available for {selected_label}.")
    else:
        # ----------- DAILY OUTBOUND ORDERS METRIC -----------
        # Unique outbound orders count (example using 'GINo' column)
        daily_orders_count = df1['GINo'].nunique() if 'GINo' in df1.columns else len(df1)

        # ----------- ORDERS BY PRIORITY AND STATUS -----------
        # Example order types and statuses from the data, adjust as needed
        order_types = df1['Priority'].dropna().unique().tolist()
        status_categories = df1['Status'].dropna().unique().tolist()

        # Create counts of statuses per priority for bar chart
        bar_data = {
            status: [len(df1[(df1['Priority'] == p) & (df1['Status'] == status)]) for p in order_types]
            for status in status_categories
        }

        colors = ['green', 'blue', 'yellow', 'salmon', 'purple']  # Expand if needed

        # ------------------------ LAYOUT ------------------------
        st.markdown("### 🏥 SSW Healthcare - **Outbound Dashboard**")
        st.markdown(f"**Date:** {datetime.now().strftime('%d %b %Y')}")

        col_left, col_right = st.columns([4, 2])
        with col_left:
            st.markdown("#### 📦 Daily Outbound Overview")
            col_date, col_metric = st.columns([2, 1])

            with col_date:
                st.metric(label="Date", value=selected_label)

            with col_metric:
                st.metric(label="Daily Outbound Orders", value=daily_orders_count)

            # Build the stacked bar chart dynamically
            bar_fig = go.Figure()
            for status, color in zip(status_categories, colors):
                bar_fig.add_trace(go.Bar(
                    y=order_types,
                    x=bar_data[status],
                    name=status,
                    orientation='h',
                    marker=dict(color=color)
                ))
            bar_fig.update_layout(
                barmode='stack',
                xaxis_title='Order Count',
                margin=dict(l=10, r=10, t=30, b=30),
                height=400
            )
            st.plotly_chart(bar_fig, use_container_width=True)

        with col_right:
            st.markdown("#### 📋 Order Status Table")
            status_table = df1.groupby(['Priority', 'Status']).size().unstack(fill_value=0)
            st.dataframe(status_table)

        # (Continue with the rest of your dashboard below...)

else:
    st.info("Please upload an Excel file to view the dashboard.")
