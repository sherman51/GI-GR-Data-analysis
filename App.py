from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ---------- CONFIG ----------
st.set_page_config(layout="wide", page_title="Outbound Dashboard Aircon")

CONFIG = {
    "priority_map": {
        '1-Normal': 'normal',
        '2-ADHOC Normal': 'Ad-hoc Normal',
        '3-ADHOC Urgent': 'Ad-hoc Urgent',
        '4-ADHOC Critical': 'Ad-hoc Critical'
    },
    "status_map": {
        '10-Open': 'Open',
        '45-Picked': 'Picked',
        '65-Packed': 'Packed',
        '75-Shipped': 'Shipped',
        '98-Cancelled': 'Cancelled'
    },
    "order_types": ['Back Orders', 'normal', 'Ad-hoc Normal', 'Ad-hoc Urgent', 'Ad-hoc Critical'],
    "status_segments": ['Open', 'Picked', 'Packed', 'Shipped', 'Cancelled'],
    "colors": {
        'Shipped': 'green',
        'Cancelled': 'red',
        'Packed': 'blue',
        'Picked': 'yellow',
        'Open': 'salmon',
        'Ad-hoc Urgent': 'orange',
        'Ad-hoc Critical': 'crimson'
    }
}

# ---------- PAGE HEADER ----------
st.markdown(
    """
    <div style="display: flex; align-items: center; background-color: #003366; padding: 12px 16px; border-radius: 6px;">
        <img src="https://raw.githubusercontent.com/sherman51/GI-GR-Data-analysis/main/SSW%20Logo.png" 
             style="max-height:40px; height:auto; width:auto; margin-right:10px;">
        <h3 style="margin: 0; font-family: Arial, sans-serif; color: #ffffff;">
            - <b>Outbound Dashboard Aircon</b>
        </h3>
    </div>
    """,
    unsafe_allow_html=True
)

uploaded_file = st.sidebar.file_uploader("📂 Upload Excel File", type=["xlsx", "xls"])

st.markdown("""
<style>
hr { border: none; height: 1px; background-color: #d3d3d3; margin: 2rem 0; }
.metric-container {
    background-color: #f4f4f4;
    padding: 12px;
    border-radius: 8px;
    text-align: center;
}
.metric-value {
    font-size: 1.5rem;
    font-weight: bold;
}
.metric-label {
    font-size: 0.9rem;
    color: #555;
}
</style>
""", unsafe_allow_html=True)

# ---------- HELPER FUNCTIONS ----------
def load_data(file):
    file_ext = file.name.split('.')[-1].lower()
    if file_ext == 'xls':
        df = pd.read_excel(file, skiprows=6, engine='xlrd')
    else:
        df = pd.read_excel(file, skiprows=6, engine='openpyxl')

    df.columns = df.columns.str.strip()
    df.dropna(axis=1, how="all", inplace=True)
    df.dropna(how="all", inplace=True)

    for col in ['ExpDate', 'CreatedOn', 'ShippedOn']:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    df = df[df['ExpDate'].notna()]
    df['Order Type'] = df['Priority'].map(CONFIG['priority_map']).fillna(df['Priority'])
    df['Status'] = df['Status'].astype(str).str.strip()
    df['Order Status'] = df['Status'].map(CONFIG['status_map']).fillna('Open')

    return df

def pie_chart(value, label, total_label, key_prefix=""):
    fig = go.Figure(go.Pie(
        values=[value, 100 - value],
        labels=[label, 'Outstanding'],
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
    st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_pie")

# ---------- SECTION FUNCTIONS ----------
def daily_overview(df_today, key_prefix=""):
    total_order_lines = df_today.shape[0]
    unique_gino = df_today['GINo'].nunique()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"<div class='metric-container' style='background-color:#dce6dc;'>"
            f"<div class='metric-value'>{total_order_lines}</div>"
            f"<div class='metric-label'>📦 Total Order Lines</div>"
            f"</div>", unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f"<div class='metric-container' style='background-color:#e6e1dc;'>"
            f"<div class='metric-value'>{unique_gino}</div>"
            f"<div class='metric-label'>🔢 Total GINo</div>"
            f"</div>", unsafe_allow_html=True
        )

    order_types = CONFIG['order_types']
    segments = CONFIG['status_segments']
    colors = CONFIG['colors']

    data = {seg: [] for seg in segments}
    for ot in order_types:
        ot_df = df_today[df_today['Order Type'] == ot]
        for seg in segments:
            count = (ot_df['Order Status'] == seg).sum()
            data[seg].append(count)

    filtered_order_types = []
    filtered_data = {seg: [] for seg in segments}
    for idx, ot in enumerate(order_types):
        total = sum(data[seg][idx] for seg in segments)
        if total > 1:
            filtered_order_types.append(ot)
            for seg in segments:
                filtered_data[seg].append(data[seg][idx])

    bar_fig = go.Figure()
    for seg in segments:
        bar_fig.add_trace(go.Bar(
            y=filtered_order_types,
            x=filtered_data[seg],
            name=seg,
            orientation='h',
            marker=dict(color=colors[seg])
        ))

    bar_fig.update_layout(
        barmode='stack',
        xaxis_title="Order Count (log scale)",
        xaxis_type="log",
        margin=dict(l=10, r=10, t=30, b=30),
        height=400
    )

    st.plotly_chart(bar_fig, use_container_width=True, key=f"{key_prefix}_overview")

def daily_completed_pie(df_today, key_prefix=""):
    total_orders = df_today.shape[0]
    completed_orders = df_today['Order Status'].isin(['Packed', 'Shipped']).sum()
    completed_pct = (completed_orders / total_orders * 100) if total_orders else 0

    fig = go.Figure(go.Pie(
        values=[completed_pct, 100 - completed_pct],
        labels=["Completed", "Outstanding"],
        marker_colors=['mediumseagreen', 'lightgray'],
        hole=0.6,
        textinfo='none',
        sort=False
    ))

    fig.update_layout(
        width=300,
        height=300,
        margin=dict(l=10, r=10, t=30, b=10),
        annotations=[dict(text=f"{completed_pct:.1f}%", x=0.5, y=0.5, font_size=20, showarrow=False)]
    )

    st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_completed")

def order_status_matrix(df_today, key_prefix=""):
    df_status_table = df_today.groupby(['Order Type', 'Order Status']).size().unstack(fill_value=0)
    df_status_table = df_status_table.reindex(index=CONFIG['order_types'],
                                              columns=CONFIG['status_segments'],
                                              fill_value=0)
    st.dataframe(df_status_table, key=f"{key_prefix}_status")

def adhoc_orders_section(df_today, key_prefix=""):
    not_completed_df = df_today[~df_today['Status'].isin(['Packed', 'Shipped'])]
    urgent_df = not_completed_df[not_completed_df['Order Type'] == 'Ad-hoc Urgent']
    critical_df = not_completed_df[not_completed_df['Order Type'] == 'Ad-hoc Critical']

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            f"""
            <div style="background-color: #f8e5a1; color: black; font-weight: bold; padding: 10px; 
            border-radius: 8px; text-align: center; margin-bottom: 5px;">
            ⚠ Urgent Orders: {urgent_df['GINo'].nunique()}
            </div>
            """,
            unsafe_allow_html=True
        )
        if urgent_df.empty:
            st.info("No GI to display")
        else:
            st.dataframe(pd.DataFrame({"GI No": urgent_df['GINo'].unique()}), key=f"{key_prefix}_urgent")

    with col2:
        st.markdown(
            f"""
            <div style="background-color: #f5a1a1; color: black; font-weight: bold; padding: 10px; 
            border-radius: 8px; text-align: center; margin-bottom: 5px;">
            🚨 Critical Orders: {critical_df['GINo'].nunique()}
            </div>
            """,
            unsafe_allow_html=True
        )
        if critical_df.empty:
            st.info("No GI to display")
        else:
            st.dataframe(pd.DataFrame({"GI No": critical_df['GINo'].unique()}), key=f"{key_prefix}_critical")

def expiry_date_summary(df, key_prefix=""):
    recent_df = df[df['ExpDate'] >= pd.Timestamp.today() - pd.Timedelta(days=14)]
    daily_summary = recent_df.groupby(recent_df['ExpDate'].dt.strftime("%d-%b"))['GINo'].count()
    cancelled_summary = recent_df[recent_df['Status'] == '98-Cancelled'] \
        .groupby(recent_df['ExpDate'].dt.strftime("%d-%b"))['GINo'].count()
    dates = pd.date_range(end=datetime.today(), periods=14).strftime("%d-%b")
    orders_received = [daily_summary.get(date, 0) for date in dates]
    orders_cancelled = [cancelled_summary.get(date, 0) for date in dates]
    fig = go.Figure(data=[
        go.Bar(name='Orders Received', x=dates, y=orders_received, marker_color='lightgreen'),
        go.Bar(name='Orders Cancelled', x=dates, y=orders_cancelled, marker_color='indianred')
    ])
    fig.update_layout(barmode='group', xaxis_title='Expiry Date', yaxis_title='Order Count')
    st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_expiry")

def order_volume_summary(df, key_prefix=""):
    today = pd.Timestamp.today().normalize()
    recent_df = df[(df['ExpDate'] >= today - pd.Timedelta(days=14)) & (df['ExpDate'] <= today)]
    daily_counts = recent_df.groupby(recent_df['ExpDate'].dt.date)['GINo'].count()

    if daily_counts.empty:
        st.info("No orders found for the past 14 days.")
        return

    peak_day_vol = daily_counts.max()
    avg_vol = daily_counts.mean()
    low_day_vol = daily_counts.min()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='metric-container' style='background-color:#dce6dc;'><div class='metric-value'>{peak_day_vol}</div><div class='metric-label'>📈 Peak Day Volume</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='metric-container' style='background-color:#e6e1dc;'><div class='metric-value'>{avg_vol:.1f}</div><div class='metric-label'>📊 Average Daily Volume</div></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='metric-container' style='background-color:#e6dcdc;'><div class='metric-value'>{low_day_vol}</div><div class='metric-label'>📉 Lowest Day Volume</div></div>", unsafe_allow_html=True)

def performance_metrics(df, key_prefix=""):
    today = pd.Timestamp.today().normalize()
    recent_past_df = df[(df['ExpDate'] < today) & (df['ExpDate'] >= today - pd.Timedelta(days=14))]
    total_expected = recent_past_df['ExpectedQTY'].sum()
    total_shipped = recent_past_df['ShippedQTY'].sum()
    accuracy_pct = (total_shipped / total_expected * 100) if total_expected else 0
    total_variance = recent_past_df['VarianceQTY'].sum()
    backorder_pct = (total_variance / total_expected * 100) if total_expected else 0

    col1, col2 = st.columns(2)
    col1.markdown("**Back Order %**")
    pie_chart(backorder_pct, "Back Order", f"{int(total_variance)} Variance", key_prefix=f"{key_prefix}_backorder")
    col2.markdown("**Order Accuracy %**")
    missed = total_expected - total_shipped
    pie_chart(accuracy_pct, "Accuracy", f"{int(missed)} Missed", key_prefix=f"{key_prefix}_accuracy")

# ---------- MAIN ----------
if uploaded_file:
    df = load_data(uploaded_file)
    aircon_zones = ['aircon', 'controlled drug room', 'strong room']
    df = df[df['StorageZone'].astype(str).str.strip().str.lower().isin(aircon_zones)]
    # Build a smart date list
date_list = []
days_checked = 0
current_date = datetime.today().date()

while len(date_list) < 3 and days_checked < 7:  # safety limit
    weekday = current_date.weekday()  # Monday=0, Sunday=6

    if weekday == 6:  # Sunday
        current_date += timedelta(days=1)
        days_checked += 1
        continue

    if weekday == 5:  # Saturday
        df_day = df[df['ExpDate'].dt.date == current_date]
        if df_day.empty:
            # Skip to Monday
            days_to_monday = (0 - weekday) % 7  # always 2 days from Saturday
            current_date += timedelta(days=days_to_monday)
            days_checked += days_to_monday
            continue

    # Passed all checks
    date_list.append(current_date)
    current_date += timedelta(days=1)
    days_checked += 1


    # Create list of 3 dates
    date_list = [datetime.today().date() + pd.Timedelta(days=i) for i in range(3)]

    # Side-by-side columns for 3 days
    col1, col2, col3 = st.columns(3)

    # Create columns based on the number of valid dates
    cols = st.columns(len(date_list))
    
for i, (dash_date, col) in enumerate(zip(date_list, cols)):
    with col:
        df_day = df[df['ExpDate'].dt.date == dash_date]

        st.markdown(
            f"<h5 style='text-align:center; color:gray;'>{dash_date.strftime('%d %b %Y')}</h5>",
            unsafe_allow_html=True
        )

        st.markdown("##### 🚨 Urgent and Critical")
        adhoc_orders_section(df_day, key_prefix=f"day{i}")
        
        st.markdown("<hr>", unsafe_allow_html=True)  # ADD THIS

        st.markdown("##### ✅ % completion")
        daily_completed_pie(df_day, key_prefix=f"day{i}")

        st.markdown("<hr>", unsafe_allow_html=True)  # ADD THIS

        st.markdown("##### 📋 Order Status Table")
        order_status_matrix(df_day, key_prefix=f"day{i}")

        st.markdown("<hr>", unsafe_allow_html=True)  # Already here

        st.markdown("##### 📦 Orders breakdown")
        daily_overview(df_day, key_prefix=f"day{i}")

    



    st.markdown("<hr>", unsafe_allow_html=True)

    # Bottom section (once only)
    st.markdown("### 📊 Order lines (Past 14 Days)")
    order_volume_summary(df, key_prefix="overall")
    expiry_date_summary(df, key_prefix="overall")

    st.markdown("### 📈 Performance Metrics")
    performance_metrics(df, key_prefix="overall")

    st.markdown("###  *Stay Safe & Well*")
else:
    st.warning("📄 Please upload an Excel file to begin.")





