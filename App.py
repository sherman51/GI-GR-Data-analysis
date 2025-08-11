from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ---------- Streamlit Config ----------
st.set_page_config(layout="wide", page_title="Outbound Dashboard")

# ---------- Page Header ----------
st.markdown("### 🏥 SSW Healthcare - **Outbound Dashboard**")
st.markdown(f"**Date:** {datetime.now().strftime('%d %b %Y')}")

# ---------- File Upload ----------
uploaded_file = st.sidebar.file_uploader("📂 Upload Excel File", type=["xlsx"])

# ---------- Styling ----------
st.markdown("""
<style>
hr {
    border: none;
    height: 1px;
    background-color: #d3d3d3;
    margin: 2rem 0;
}
</style>
""", unsafe_allow_html=True)

if uploaded_file:
    # Load data
    df_raw = pd.read_excel(uploaded_file)

    
    
    # Clean empty columns and rows
    df_raw = pd.read_excel(uploaded_file, skiprows=5)
    df_raw.columns = df_raw.columns.str.strip()
    df = df_raw.dropna(axis=1, how="all")
    df.dropna(how="all", inplace=True)

    # Preview data
    st.markdown("### 🔍 Preview of Uploaded Data (after skipping 5 rows)")
    st.write("**Columns Detected:**", df_raw.columns.tolist())
    st.dataframe(df_raw.head(10))


    # Map order types
    priority_map = {
        '1-Normal': 'Scheduled',
        '2-ADHOC Normal': 'Ad-hoc Normal',
        '3-ADHOC Urgent': 'Ad-hoc Urgent',
        '4-ADHOC Critical': 'Ad-hoc Critical'
    }
    df['Order Type'] = df['Priority'].map(priority_map).fillna(df['Priority'])

    # Map status categories
    status_map = {
        '65-Packed': 'Packed',
        '75-Shipped': 'Tpt Booked',
        '98-Cancelled': 'Open'
    }
    df['Order Status'] = df['Status'].map(status_map).fillna('Open')

    # ---------- Top Row ----------
    col_left, col_right = st.columns([4, 2])

    with col_left:
        st.markdown("#### 📦 Daily Outbound Overview")
        col_date, col_metric = st.columns([2, 1])

        with col_date:
            st.metric(label="Date", value=datetime.now().strftime('%d %b %Y'))

        with col_metric:
            st.metric(label="Orders Today (by ExpDate)", value=df[df['ExpDate'].dt.date == datetime.today().date()].shape[0])

        # Build stacked bar chart by status and order type
        order_types = ['Back Orders', 'Scheduled', 'Ad-hoc Normal', 'Ad-hoc Urgent', 'Ad-hoc Critical']
        segments = ['Tpt Booked', 'Packed', 'Picked', 'Open']
        colors = ['green', 'blue', 'yellow', 'salmon']

        data = {seg: [] for seg in segments}
        for ot in order_types:
            ot_df = df[df['Order Type'] == ot]
            for seg in segments:
                count = (ot_df['Order Status'] == seg).sum()
                data[seg].append(count)

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
        df_status_table = df.groupby(['Order Status', 'Order Type']).size().unstack(fill_value=0)
        df_status_table = df_status_table.reindex(index=segments, columns=order_types, fill_value=0)
        st.dataframe(df_status_table)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ---------- Bottom Row ----------
    col_bottom_left, col_bottom_right = st.columns([3, 2])

    with col_bottom_left:
        st.markdown("#### 📊 Orders by Expiry Date (Past 14 Days)")
        recent_df = df[df['ExpDate'] >= pd.Timestamp.today() - pd.Timedelta(days=14)]

        daily_summary = recent_df.groupby(df['ExpDate'].dt.strftime("%d-%b"))['GINo'].count()
        cancelled_summary = recent_df[recent_df['Status'] == '98-Cancelled'] \
            .groupby(df['ExpDate'].dt.strftime("%d-%b"))['GINo'].count()

        dates = pd.date_range(end=datetime.today(), periods=14).strftime("%d-%b")
        orders_received = [daily_summary.get(date, 0) for date in dates]
        orders_cancelled = [cancelled_summary.get(date, 0) for date in dates]

        fig = go.Figure(data=[
            go.Bar(name='Orders Received', x=dates, y=orders_received, marker_color='lightgreen'),
            go.Bar(name='Orders Cancelled', x=dates, y=orders_cancelled, marker_color='red')
        ])
        fig.update_layout(barmode='group', xaxis_title='Expiry Date', yaxis_title='Order Count')
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

        # Calculate order accuracy
        total_expected = df['ExpectedQTY'].sum()
        total_shipped = df['ShippedQTY'].sum()
        accuracy_pct = (total_shipped / total_expected * 100) if total_expected else 0

        # Simulate back order % (variance vs expected)
        total_variance = df['VarianceQTY'].sum()
        backorder_pct = (total_variance / total_expected * 100) if total_expected else 0

        col_pie1, col_pie2 = st.columns(2)

        with col_pie1:
            st.markdown("**Back Order %**")
            fig_back_order = pie_chart(backorder_pct, "Back Order", f"{int(total_variance)} Variance")
            st.plotly_chart(fig_back_order, use_container_width=True)

        with col_pie2:
            st.markdown("**Order Accuracy %**")
            fig_order_accuracy = pie_chart(accuracy_pct, "Accuracy", f"{int(total_expected - total_shipped)} Missed")
            st.plotly_chart(fig_order_accuracy, use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ---------- Footer ----------
    st.markdown("### 💙 *Stay Safe & Well*")

else:
    st.warning("📄 Please upload an Excel file to begin.")

