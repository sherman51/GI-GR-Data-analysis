from datetime import datetime, date, timedelta
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import random

# ---------- Page Config ----------
st.set_page_config(layout="wide", page_title="Outbound Dashboard")

# ---------- Inject CSS for muted divider ----------
st.markdown(
    """
    <style>
    hr {
        border: none;
        height: 1px;
        background-color: #d3d3d3;
        margin: 2rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------- Sidebar File Upload ----------
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

# ---------- Header ----------
st.markdown("### 🏥 SSW Healthcare - **Outbound Dashboard**")
st.markdown(f"**Date:** {datetime.now().strftime('%d %b %Y')}")

if uploaded_file:
    # ---------- Data Processing ----------
    # Skip metadata rows, header starts on row 6 (index 5)
    df_raw = pd.read_excel(uploaded_file, sheet_name="Good Receive Analysis", skiprows=5)

    # Remove empty columns/rows
    df = df_raw.dropna(axis=1, how="all").dropna(how="all")
    df.columns = df.columns.str.strip()

    # Convert Date column
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # Ensure quantity columns are numeric
    for col in ["ExpectedQTY", "ShippedQTY", "VarianceQTY"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ---------- Top Row ----------
    col_left, col_right = st.columns([4, 2])

    with col_left:
        st.markdown("#### 📦 Daily Outbound Overview")

        col_date, col_metric = st.columns([2, 1])

        with col_date:
            st.metric(label="Date", value=selected_date.strftime('%d %b %Y'))

        with col_metric:
            st.metric(
                label="Daily Outbound Orders",
                value=df['GINo'].nunique() if 'GINo' in df.columns else "N/A"
            )

        order_types = [
            "Back Orders",
            "Scheduled",
            "Ad-hoc Normal",
            "Ad-hoc Urgent",
            "Ad-hoc Critical"
        ]
        segments = ["Tpt Booked", "Packed", "Picked", "Open"]
        colors = ['green', 'blue', 'yellow', 'salmon']

        data = {seg: [random.randint(1, 10) for _ in order_types] for seg in segments}

        bar_fig = go.Figure()
        for seg, color in zip(segments, colors):
            bar_fig.add_trace(go.Bar(
                y=order_types,
                x=data[seg],
                name=seg,
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

        table_data = {
            "Ad-hoc Critical": [3, 0, 3, 0],
            "Ad-hoc Urgent": [4, 2, 0, 0],
            "Ad-hoc Normal": [10, 7, 3, 0],
            "Scheduled": [5, 6, 13, 17],
            "Back Orders": [2, 4, 3, 2]
        }
        index_labels = ["Tpt Booked", "Packed", "Picked", "Open"]
        df_table = pd.DataFrame(table_data, index=index_labels)
        st.dataframe(df_table)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ---------- Bottom Row ----------
    col_bottom_left, col_bottom_right = st.columns([3, 2])

    with col_bottom_left:
        st.markdown("#### 📊 Orders Over the Past 2 Weeks (Weekly View)")

        if "Date" in df.columns and "GINo" in df.columns:
            last_2_weeks = df["Date"].max() - pd.Timedelta(days=14)
            df_recent = df[df["Date"] >= last_2_weeks].copy()

            df_recent["Week"] = df_recent["Date"].dt.isocalendar().week
            df_recent["Year"] = df_recent["Date"].dt.year

            weekly_summary = df_recent.groupby(["Year", "Week"]).agg(
                Orders_Received=("GINo", "nunique"),
                Orders_Cancelled=("Status", lambda x: (x == "98-Cancelled").sum()),
                Orders_Shipped=("ShippedQTY", lambda x: (x.fillna(0) > 0).sum())
            ).reset_index()

            weekly_summary["Week_Label"] = weekly_summary["Year"].astype(str) + "-W" + weekly_summary["Week"].astype(str)

            fig = go.Figure(data=[
                go.Bar(name="Orders Received", x=weekly_summary["Week_Label"], y=weekly_summary["Orders_Received"], marker_color="lightgreen"),
                go.Bar(name="Orders Cancelled", x=weekly_summary["Week_Label"], y=weekly_summary["Orders_Cancelled"], marker_color="red"),
                go.Bar(name="Orders Shipped", x=weekly_summary["Week_Label"], y=weekly_summary["Orders_Shipped"], marker_color="blue")
            ])
            fig.update_layout(barmode="group", xaxis_title="Week", yaxis_title="Order Count")
            st.plotly_chart(fig, use_container_width=True)

    with col_bottom_right:
        st.markdown("#### 📈 Performance Metrics")

        def pie_chart(value, label, total_label):
            fig = go.Figure(go.Pie(
                values=[value, 100 - value],
                labels=[label, 'Remaining'],
                marker_colors=['mediumseagreen', 'lightgray'],
                hole=0.7,
                textinfo='none',
                sort=False
            ))
            fig.update_layout(
                showlegend=False,
                margin=dict(t=0, b=0, l=0, r=0),
                annotations=[
                    dict(text=f"{value:.2f}%", x=0.5, y=0.5, font_size=20, showarrow=False),
                    dict(text=total_label, x=0.5, y=0.2, font_size=12, showarrow=False)
                ]
            )
            return fig

        col_pie1, col_pie2 = st.columns(2)

        with col_pie1:
            st.markdown("**Back Order < 0.50%**")
            fig_back_order = pie_chart(0.10, "Back Order", "1 of 1000 lines")
            st.plotly_chart(fig_back_order, use_container_width=True, height=200)

        with col_pie2:
            st.markdown("**Order Accuracy > 99.50%**")
            fig_order_accuracy = pie_chart(100.00, "Accuracy", "0 SLA Missed")
            st.plotly_chart(fig_order_accuracy, use_container_width=True, height=200)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ---------- Footer ----------
    st.markdown("### 💙 *Stay Safe & Well*")

else:
    st.info("Please upload an Excel file to view the dashboard.")
