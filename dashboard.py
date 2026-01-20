import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="STRATEGIC HUB V17.0", layout="wide", page_icon="🚀")

# Giao diện tối giản, chuyên nghiệp
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# LINKS DỮ LIỆU
URL_LAPTOP_LOI = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=675485241&single=true&output=csv"
URL_MIEN_BAC = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv"
URL_DA_NANG = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"

@st.cache_data(ttl=60)
def load_data(url):
    try:
        return pd.read_csv(url, on_bad_lines='skip', low_memory=False).fillna("0")
    except:
        return pd.DataFrame()

def main():
    # --- SIDEBAR CONTROL ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/906/906343.png", width=80)
        st.title("COMMAND CENTER")
        if st.button('🔄 REFRESH SYSTEM', type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.divider()
        st.write("⚙️ **CÀI ĐẶT HỆ THỐNG**")
        show_raw = st.toggle("Hiển thị dữ liệu thô")

    # LOAD DỮ LIỆU
    df_loi_raw = load_data(URL_LAPTOP_LOI)
    df_bac_raw = load_data(URL_MIEN_BAC)
    df_nam_raw = load_data(URL_DA_NANG)

    # --- 2. XỬ LÝ DỮ LIỆU TÀI CHÍNH ---
    df_f = pd.DataFrame()
    if not df_loi_raw.empty:
        f_list = []
        for _, row in df_loi_raw.iloc[1:].iterrows():
            ma = str(row.iloc[1]).strip()
            if not ma or "MÃ" in ma.upper(): continue
            ngay = pd.to_datetime(row.iloc[6], dayfirst=True, errors='coerce')
            if pd.notnull(ngay):
                cp = pd.to_numeric(str(row.iloc[8]).replace(',', ''), errors='coerce') or 0
                f_list.append({
                    "NGÀY": ngay, "THÁNG": ngay.month, "MÃ_MÁY": ma, 
                    "LINH_KIỆN": str(row.iloc[3]).strip(),
                    "VÙNG": str(row.iloc[5]).strip(), "CP": cp,
                    "KHÁCH_HÀNG": str(row.iloc[2]).strip()
                })
        df_f = pd.DataFrame(f_list)

    if df_f.empty:
        st.warning("🚀 Đang khởi động hệ thống... Vui lòng đợi trong giây lát.")
        return

    # --- 3. BỘ LỌC ĐỘNG (DASHBOARD ENGINE) ---
    vung_list = ["TẤT CẢ"] + list(df_f['VÙNG'].unique())
    selected_vung = st.sidebar.selectbox("📍 CHỌN VÙNG CHIẾN LƯỢC", vung_list)
    
    df_display = df_f.copy()
    if selected_vung != "TẤT CẢ":
        df_display = df_f[df_f['VÙNG'] == selected_vung]

    # --- 4. GIAO DIỆN CHÍNH (THE MUSK STYLE) ---
    st.title("🚀 STRATEGIC HUB V17.0")
    
    # KIPs Metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("TỔNG CHI PHÍ", f"{df_display['CP'].sum():,.0f} đ")
    with m2: st.metric("SỐ CA XỬ LÝ", f"{len(df_display)} ca")
    with m3: st.metric("TB/CA", f"{(df_display['CP'].mean()):,.0f} đ")
    with m4:
        top_lk = df_display['LINH_KIỆN'].value_counts().idxmax()
        st.metric("LỖI PHỔ BIẾN", top_lk)

    st.divider()

    tabs = st.tabs(["📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🩺 SỨC KHỎE MÁY", "📦 KHO LOGISTICS", "📁 DỮ LIỆU"])

    # TAB: XU HƯỚNG
    with tabs[0]:
        c1, c2 = st.columns([2, 1])
        with c1:
            df_trend = df_display.groupby('THÁNG')['CP'].sum().reset_index()
            fig = px.area(df_trend, x='THÁNG', y='CP', title="BIỂU ĐỒ CHI PHÍ THEO THỜI GIAN", 
                          color_discrete_sequence=['#0068c9'])
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig_pie = px.pie(df_display, names='VÙNG', title="CƠ CẤU VÙNG MIỀN", hole=0.5)
            st.plotly_chart(fig_pie, use_container_width=True)

    # TAB: TÀI CHÍNH
    with tabs[1]:
        st.subheader("💰 CHI TIẾT NGÂN SÁCH LINH KIỆN")
        df_cost = df_display.groupby('LINH_KIỆN')['CP'].sum().sort_values(ascending=False).reset_index()
        fig_bar = px.bar(df_cost, x='CP', y='LINH_KIỆN', orientation='h', 
                         color='CP', title="CHI PHÍ TÍCH LŨY THEO LOẠI")
        st.plotly_chart(fig_bar, use_container_width=True)

    # TAB: SỨC KHỎE MÁY (RADAR)
    with tabs[2]:
        st.subheader("🩺 DANH SÁCH THIẾT BỊ CẦN THANH LÝ (HỎNG > 2 LẦN)")
        health = df_f.groupby('MÃ_MÁY').agg({'NGÀY': 'count', 'CP': 'sum', 'KHÁCH_HÀNG': 'first'}).reset_index()
        health.columns = ['Mã Máy', 'Số lần hỏng', 'Tổng chi phí', 'Khách hàng']
        # Highlight máy hỏng nhiều
        st.dataframe(health[health['Số lần hỏng'] >= 2].sort_values('Số lần hỏng', ascending=False), use_container_width=True)

    # TAB: KHO LOGISTICS
    with tabs[3]:
        st.subheader("📦 TRẠNG THÁI KHO VẬN TOÀN CẦU")
        wh_data = []
        for region, raw in [("BẮC", df_bac_raw), ("NAM", df_nam_raw)]:
            if not raw.empty:
                for _, r in raw.iloc[1:].iterrows():
                    m = str(r.iloc[1]).strip()
                    if m and "MÃ" not in m.upper():
                        # Logic phân loại Elon Musk: Hiệu quả & Trực quan
                        stt_raw = str(r.iloc[6]).upper() + str(r.iloc[9]).upper()
                        stt = "🔵 ĐÃ NHẬN" if "OK" in stt_raw else "🟡 ĐANG XỬ LÝ"
                        if "HỎNG" in stt_raw or "LÝ" in stt_raw: stt = "🔴 THANH LÝ"
                        wh_data.append({"VÙNG": region, "MÃ_MÁY": m, "TRẠNG_THÁI": stt})
        
        if wh_data:
            df_wh = pd.DataFrame(wh_data)
            summary = df_wh.groupby(['VÙNG', 'TRẠNG_THÁI']).size().unstack(fill_value=0)
            st.table(summary)

    # TAB: DỮ LIỆU
    with tabs[4]:
        st.subheader("📁 TRUY XUẤT DỮ LIỆU NGUỒN")
        st.dataframe(df_display, use_container_width=True)
        if show_raw:
            st.write("Dữ liệu gốc từ Tài chính:", df_loi_raw.head())

if __name__ == "__main__":
    main()
