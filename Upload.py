import streamlit as st
import pandas as pd
import io
import re
from google.cloud import storage
from google.oauth2 import service_account
import pytz

# --- GCP Authentication ---
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
bucket_name = "testbucket352"

client = storage.Client(
    credentials=credentials,
    project=st.secrets["gcp_service_account"]["project_id"]
)
bucket = client.bucket(bucket_name)

st.title("📁 Upload Excel Files to Dashboard")


# --- Last Upload Tracker ---
def get_last_upload_info(bucket):
    """Get the most recently uploaded Excel file from the bucket."""
    blobs = [
        b for b in bucket.list_blobs()
        if b.name.lower().endswith(('.xlsx', '.xls'))
    ]
    if not blobs:
        return None, None
    latest_blob = max(blobs, key=lambda b: b.updated)
    sg_tz = pytz.timezone('Asia/Singapore')
    upload_time = latest_blob.updated.astimezone(sg_tz)
    return latest_blob.name, upload_time


# --- SpreadsheetML Parser (XML-based .xls) ---
def parse_spreadsheetml(raw_bytes):
    """
    Parse Excel XML / SpreadsheetML format files saved with .xls extension.
    Handles files exported from ERP/WMS systems that embed whitespace/newlines
    inside XML namespace URIs, which breaks standard parsers.
    """
    from lxml import etree

    content = raw_bytes.decode('utf-8', errors='replace')

    # Strip anything before <Workbook
    content = re.sub(r'^.*?(<Workbook)', r'\1', content, flags=re.DOTALL)

    # Generic fix: remove any whitespace found INSIDE any xmlns="..." URI.
    # e.g. xmlns:x="urn:schemas-    microsoft-com:office:excel"
    # This handles ALL broken namespace URIs regardless of prefix.
    content = re.sub(r'(xmlns:\w+="[^"]*?)\s+([^"]*?")', r'\1\2', content)

    # Escape bare ampersands that would break XML parsing
    content = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', content)

    try:
        tree = etree.fromstring(content.encode('utf-8'))
    except etree.XMLSyntaxError as e:
        raise ValueError(f"Failed to parse SpreadsheetML XML: {e}")

    ns = 'urn:schemas-microsoft-com:office:spreadsheet'
    rows = tree.findall(f'.//{{{ns}}}Row')

    if not rows:
        raise ValueError("No rows found in SpreadsheetML file.")

    data = []
    for row in rows:
        cells = row.findall(f'.//{{{ns}}}Data')
        data.append([c.text if c.text else '' for c in cells])

    if not data:
        raise ValueError("Parsed rows but found no cell data.")

    df = pd.DataFrame(data[1:], columns=data[0])
    return df


# --- Read Excel File (auto-detect format) ---
def read_excel_file(uploaded_file, original_file_name):
    """
    Detect and read Excel files in any of these formats:
      - .xlsx  (ZIP/OpenXML)      → openpyxl
      - .xls   binary BIFF        → xlrd
      - .xls   SpreadsheetML XML  → lxml parser
    """
    raw_bytes = uploaded_file.read()
    uploaded_file.seek(0)

    is_xlsx = raw_bytes[:4] == b'PK\x03\x04'
    is_biff = raw_bytes[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
    is_xml  = (
        b'<Workbook' in raw_bytes[:500]
        or b'spreadsheet' in raw_bytes[:500].lower()
    )

    if is_xlsx or original_file_name.lower().endswith('.xlsx'):
        buf = io.BytesIO(raw_bytes)
        df = pd.read_excel(buf, engine='openpyxl')
        content_type = (
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    elif is_biff:
        buf = io.BytesIO(raw_bytes)
        df = pd.read_excel(buf, engine='xlrd')
        content_type = 'application/vnd.ms-excel'

    elif is_xml:
        df = parse_spreadsheetml(raw_bytes)
        content_type = 'application/vnd.ms-excel'

    else:
        # Last-resort fallback — try both engines
        last_error = None
        df = None
        for engine in ['openpyxl', 'xlrd']:
            try:
                buf = io.BytesIO(raw_bytes)
                df = pd.read_excel(buf, engine=engine)
                content_type = 'application/vnd.ms-excel'
                break
            except Exception as e:
                last_error = e
                continue

        if df is None:
            raise ValueError(
                f"Unrecognised file format. Please upload a valid .xls or .xlsx file. "
                f"Last error: {last_error}"
            )

    return df, content_type


# --- Detect dashboard from filename ---
def detect_dashboard(file_name):
    """
    Route file to the correct dashboard based on its name.
      - Contains 'count' → Stock Count Dashboard
      - Contains 'gi'    → Outbound (GI) Dashboard
      - Anything else    → None (unknown)
    """
    name_lower = file_name.lower()
    if 'count' in name_lower:
        return 'Stock Count Dashboard', 'count'
    elif 'gi' in name_lower:
        return 'Outbound (GI) Dashboard', 'gi'
    else:
        return None, None


# --- Display Last Upload Info ---
st.markdown("---")
last_file, last_time = get_last_upload_info(bucket)
if last_file and last_time:
    st.markdown("**📂 Last Uploaded File:**")
    st.text_input(
        "Last Uploaded File",
        value=last_file,
        disabled=True,
        label_visibility="collapsed",
        key="filename_display"
    )
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📅 Upload Date", last_time.strftime("%d %b %Y"))
    with col2:
        st.metric("🕐 Upload Time", last_time.strftime("%I:%M:%S %p"))
else:
    st.info("ℹ️ No files found in the bucket.")

st.markdown("---")

# --- Upload Section ---
st.header("Upload Excel File (.xls or .xlsx)")
st.caption(
    "📌 The file will be automatically routed to the correct dashboard based on its name:\n\n"
    "- Files containing **'Count'** → Stock Count Dashboard\n"
    "- Files containing **'GI'** → Outbound Dashboard"
)

uploaded_file = st.file_uploader(
    "Choose an Excel file",
    type=["xls", "xlsx"]
)

if uploaded_file is not None:
    original_file_name = uploaded_file.name
    dashboard, cleanup_keyword = detect_dashboard(original_file_name)

    # --- Show detected dashboard or block if unrecognised ---
    if dashboard:
        st.info(f"📊 Detected dashboard: **{dashboard}**")
    else:
        st.warning(
            f"⚠️ Could not detect dashboard from filename **'{original_file_name}'**.\n\n"
            "Please rename the file to include **'Count'** or **'GI'** and re-upload."
        )
        st.stop()

    try:
        df, content_type = read_excel_file(uploaded_file, original_file_name)

        st.subheader("📊 Preview of uploaded data:")
        st.dataframe(df.head())
        st.caption(f"Total rows: {len(df):,} | Columns: {len(df.columns)}")

        # --- Upload new file to GCS (keep original filename) ---
        uploaded_file.seek(0)
        blob = bucket.blob(original_file_name)
        blob.upload_from_file(uploaded_file, content_type=content_type)
        st.success(f"✅ Uploaded **'{original_file_name}'** to Google Cloud Storage.")

        # --- Cleanup: only delete old files of the same dashboard type ---
        st.info(f"🧹 Cleaning up old **{dashboard}** files...")
        blobs = list(bucket.list_blobs())
        deleted_count = 0

        for b in blobs:
            if b.name == original_file_name:
                continue  # never delete the file we just uploaded
            if cleanup_keyword in b.name.lower():
                b.delete()
                deleted_count += 1

        if deleted_count:
            st.success(f"✅ Deleted {deleted_count} old file(s) for **{dashboard}**.")
        else:
            st.info("ℹ️ No old files to clean up.")

        st.rerun()

    except Exception as e:
        st.error(f"❌ Failed to read or upload Excel file: {e}")
