import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="Hệ Thống Quản Trị V16.5", layout="wide")

URL_FINANCE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?output=csv"
URL_KHO_BAC = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv"
URL_KHO_NAM = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"

@st.cache_data(ttl=300)
def fetch_data(url):
    try:
        return pd.read_csv(url, on_bad_lines='skip', low_memory=False).fillna("0")
    except:
        return pd.DataFrame()

def main():
    st.sidebar.title("🛡️ CONTROL CENTER")
    if st.sidebar.button('🔄 LÀM MỚI DỮ LIỆU', type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Nạp dữ liệu độc lập
    df_f_raw = fetch_data(URL_FINANCE)
    df_kb_raw = fetch_data(URL_KHO_BAC)
    df_kn_raw = fetch_data(URL_KHO_NAM)

    # --- 2. XỬ LÝ DỮ LIỆU TÀI CHÍNH ---
    df_f = pd.DataFrame()
    if not df_f_raw.empty and len(df_f_raw.columns) > 8:
        clean_f = []
        for _, row in df_f_raw.iloc[1:].iterrows():
            ma = str(row.iloc[1]).strip()
            if not ma or "MÃ" in ma.upper(): continue
            ngay = pd.to_datetime(row.iloc[6], dayfirst=True, errors='coerce')
            if pd.notnull(ngay):
                cp_tt = pd.to_numeric(str(row.iloc[8]).replace(',', ''), errors='coerce') or 0
                clean_f.append({
                    "NGÀY": ngay, "THÁNG": ngay.month, "NĂM": ngay.year,
                    "MÃ_MÁY": ma, "LINH_KIỆN": str(row.iloc[3]).strip(),
                    "VÙNG": str(row.iloc[5]).strip() or "CHƯA PHÂN VÙNG", 
                    "CP_THUC_TE": cp_tt
                })
        df_f = pd.DataFrame(clean_f)

    # --- 3. KIỂM TRA DỮ LIỆU ĐẦU VÀO ---
    if df_f.empty:
        st.warning("⚠️ Đang chờ nạp dữ liệu... Sếp vui lòng kiểm tra kết nối Sheets.")
        return

    # --- 4. BỘ LỌC ---
    vung_options = sorted(df_f['VÙNG'].unique())
    sel_vung = st.sidebar.multiselect("📍 Vùng Miền", options=vung_options, default=vung_options)
    df_f_filtered = df_f[df_f['VÙNG'].isin(sel_vung)]

    # --- 5. GIAO DIỆN CHÍNH ---
    st.title("🛡️ HỆ THỐNG QUẢN TRỊ CHIẾN LƯỢC V16.5")
    tabs = st.tabs(["📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🧠 AI ANALYTICS", "📁 DỮ LIỆU", "🩺 SỨC KHỎE", "📦 KHO"])

    # TAB 1: XU HƯỚNG
    with tabs[0]:
        c1, c2 = st.columns([2, 1])
        line_data = df_f_filtered.groupby('THÁNG')['CP_THUC_TE'].sum().reset_index()
        fig_line = px.line(line_data, x='THÁNG', y='CP_THUC_TE', title="Biến động chi phí", markers=True)
        c1.plotly_chart(fig_line, use_container_width=True)
        
        fig_pie = px.pie(df_f_filtered, names='VÙNG', hole=0.4, title="Tỷ lệ sự cố")
        c2.plotly_chart(fig_pie, use_container_width=True)

    # TAB 2: TÀI CHÍNH
    with tabs[1]:
        bar_data = df_f_filtered.groupby('LINH_KIỆN')['CP_THUC_TE'].sum().sort_values(ascending=False).reset_index()
        fig_bar = px.bar(bar_data, x='LINH_KIỆN', y='CP_THUC_TE', color='CP_THUC_
