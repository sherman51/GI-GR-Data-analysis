from datetime import datetime, date, timedelta
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ---------- Page Config ----------
st.set_page_config(layout="wide", page_title="Outbound Dashboard")

# ---------- Inject CSS ----------
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
    # Load Excel with correct header
    df = pd.read_excel(uploaded_file, skiprows=5, header=0)
    df = df.dropna(axis=1, how="all").dropna(how="all")
    df.columns = df.columns.str.strip()

    # Ensure ExpDate is datetime
    if 'ExpDate' in df.columns:
        df['ExpDate'] = pd.to_datetime(df['ExpDate'], errors='coerce').dt.date

    # Filter data for selected date
    if 'ExpDate' in df.columns:
        df_filtered = df[df['ExpDate'] == selected_date]
    else:
        st.error("No 'ExpDate' column found in file")
        st.stop()

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
                value=df_filtered['GINo'].nunique() if 'GINo' in df_filtered.columns else "N/A"
            )

        # Order types & segments from data
        order_types = df_filtered['Type'].unique().tolist() if 'Type' in df_filtered.columns else []
        status_counts = df_filtered.groupby(['Type', 'Status']).size().unstack(fill_value=0)

        bar_fig = go.Figure()
        for status in status_counts.columns:
            bar_fig.add_trace(go.Bar(
                y=status_counts.index,
                x=status_counts[status],
                name=status,
                orientation='h'
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
        st.dataframe(status_counts)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ---------- Bottom Row ----------
    col_bottom_left, col_bottom_right = st.columns([3, 2])

    with col_bottom_left:
        st.markdown("#### 📊 Orders Over the Past 2 Weeks (Grouped Weekly)")

        df_past = df.copy()
        df_past = df_past.dropna(subset=['ExpDate'])
        df_past['Week'] = pd.to_datetime(df_past['ExpDate']).dt.to_period('W').apply(lambda r: r.start_time)

        two_weeks_ago = today - timedelta(weeks=2)
        df_past = df_past[df_past['ExpDate'] >= two_weeks_ago]

        weekly_counts = df_past.groupby('Week').agg(
            Orders_Received=('GINo', 'nunique'),
            Orders_Cancelled=('Status', lambda x: (x == '98-Cancelled').sum())
        ).reset_index()

        fig = go.Figure(data=[
            go.Bar(name='Orders Received', x=weekly_counts['Week'], y=weekly_counts['Orders_Received'], marker_color='lightgreen'),
            go.Bar(name='Orders Cancelled', x=weekly_counts['Week'], y=weekly_counts['Orders_Cancelled'], marker_color='red')
        ])
        fig.update_layout(barmode='group', xaxis_title='Week', yaxis_title='Order Count')
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

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### 💙 *Stay Safe & Well*")

else:
    st.info("Please upload an Excel file to view the dashboard.")
