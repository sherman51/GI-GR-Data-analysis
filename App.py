from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import random

# ------------------------ FILE UPLOAD ------------------------
uploaded_file = st.sidebar.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file:
    # Skip metadata rows, header starts on row 6 (index 5)
    df_raw = pd.read_excel(uploaded_file, skiprows=5)

    # Clean up
    df = df_raw.dropna(axis=1, how="all")  # Remove empty columns
    df.dropna(how="all", inplace=True)     # Remove empty rows





# ---------- Inject CSS for muted divider ----------
st.markdown(
    """
    <style>
    hr {
        border: none;
        height: 1px;
        background-color: #d3d3d3;  /* light gray */
        margin: 2rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------- Page Config ----------
st.set_page_config(layout="wide", page_title="Outbound Dashboard")

# ---------- Header ----------
st.markdown("### 🏥 SSW Healthcare - **Outbound Dashboard**")
st.markdown(f"**Date:** {datetime.now().strftime('%d %b %Y')}")

# ---------- Top Row ----------
col_left, col_right = st.columns([4, 2])

with col_left:
    st.markdown("#### 📦 Daily Outbound Overview")

    col_date, col_metric = st.columns([2, 1])

    with col_date:
        st.metric(label="Date", value=datetime.now().strftime('%d %b %Y'))

    with col_metric:
        st.metric(label="Daily Outbound Orders", df["GINo"].nunique() if "GINo" in df.columns else "N/A")

    # Bar chart code below
    order_types = [
        "Back Orders",
        "Scheduled",
        "Ad-hoc Normal",
        "Ad-hoc Urgent",
        "Ad-hoc Critical"
    ]
    segments = ["Tpt Booked", "Packed", "Picked", "Open"]
    colors = ['green', 'blue', 'yellow', 'salmon']

    data = {
        seg: [random.randint(1, 10) for _ in order_types]
        for seg in segments
    }

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

st.markdown("<hr>", unsafe_allow_html=True)  # Muted divider

# ---------- Bottom Row ----------
col_bottom_left, col_bottom_right = st.columns([3, 2])

with col_bottom_left:
    st.markdown("#### 📊 Orders Over the Past 2 Weeks")

    dates = pd.date_range(end=datetime.today(), periods=14).strftime("%d-%b")
    orders_received = [random.randint(30, 70) for _ in range(14)]
    orders_cancelled = [random.randint(0, 10) for _ in range(14)]

    fig = go.Figure(data=[
        go.Bar(name='Orders Received', x=dates, y=orders_received, marker_color='lightgreen'),
        go.Bar(name='Orders Cancelled', x=dates, y=orders_cancelled, marker_color='red')
    ])
    fig.update_layout(barmode='group', xaxis_title='Date', yaxis_title='Order Count')
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
            annotations=[dict(text=f"{value:.2f}%", x=0.5, y=0.5, font_size=20, showarrow=False),
                         dict(text=total_label, x=0.5, y=0.2, font_size=12, showarrow=False)]
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

st.markdown("<hr>", unsafe_allow_html=True)  # Muted divider

# ---------- Footer ----------
st.markdown("### 💙 *Stay Safe & Well*")

