import streamlit as st
import pandas as pd
import plotly.express as px
import io

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="STRATEGIC HUB V18.0", layout="wide", page_icon="🚀")

st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    [data-testid="stSidebar"] { background-color: #f8f9fa; }
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
    except: return pd.DataFrame()

def main():
    # --- 2. SIDEBAR: ĐIỀU KHIỂN & BỘ LỌC ---
    with st.sidebar:
        st.title("🚀 COMMAND CENTER")
        if st.button('🔄 REFRESH SYSTEM', type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.divider()
        # Nạp dữ liệu thô để lấy danh sách lọc
        df_loi_raw = load_data(URL_LAPTOP_LOI)
        df_bac_raw = load_data(URL_MIEN_BAC)
        df_nam_raw = load_data(URL_DA_NANG)

        # Xử lý dữ liệu Tài chính chuẩn
        f_list = []
        if not df_loi_raw.empty:
            for _, row in df_loi_raw.iloc[1:].iterrows():
                ma = str(row.iloc[1]).strip()
                if not ma or "MÃ" in ma.upper(): continue
                ngay = pd.to_datetime(row.iloc[6], dayfirst=True, errors='coerce')
                if pd.notnull(ngay):
                    cp = pd.to_numeric(str(row.iloc[8]).replace(',', ''), errors='coerce') or 0
                    f_list.append({
                        "NGÀY": ngay, "NĂM": ngay.year, "THÁNG": ngay.month,
                        "MÃ_MÁY": ma, "LINH_KIỆN": str(row.iloc[3]).strip(),
                        "VÙNG": str(row.iloc[5]).strip(), "CP": cp,
                        "KHÁCH_HÀNG": str(row.iloc[2]).strip()
                    })
        df_f = pd.DataFrame(f_list)

        if not df_f.empty:
            st.subheader("🗓️ LỌC THỜI GIAN")
            years = sorted(df_f['NĂM'].unique(), reverse=True)
            sel_year = st.selectbox("Chọn Năm", years)
            
            months = ["Tất cả"] + sorted(df_f[df_f['NĂM'] == sel_year]['THÁNG'].unique().tolist())
            sel_month = st.selectbox("Chọn Tháng", months)
            
            st.divider()
            st.subheader("📥 XUẤT BÁO CÁO")
            csv = df_f.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 TẢI BÁO CÁO CSV", data=csv, file_name=f'Bao_cao_{sel_year}.csv', mime='text/csv', use_container_width=True)

    # Lọc dữ liệu hiển thị cho các Tab Tài chính/Xu hướng/AI
    df_display = df_f[df_f['NĂM'] == sel_year]
    if sel_month != "Tất cả":
        df_display = df_display[df_display['THÁNG'] == sel_month]

    # --- 3. MÀN HÌNH CHÍNH ---
    st.title("🚀 STRATEGIC HUB V18.0")
    
    # KPIs Top Cards
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TỔNG CHI PHÍ", f"{df_display['CP'].sum():,.0f} đ")
    m2.metric("SỐ CA XỬ LÝ", f"{len(df_display)} ca")
    m3.metric("TRUNG BÌNH/CA", f"{(df_display['CP'].mean() if len(df_display)>0 else 0):,.0f} đ")
    m4.metric("LỖI PHỔ BIẾN", df_display['LINH_KIỆN'].value_counts().idxmax() if not df_display.empty else "N/A")

    st.divider()

    tabs = st.tabs(["📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🩺 SỨC KHỎE MÁY", "📦 KHO LOGISTICS", "🧠 AI & DỰ BÁO"])

    # TAB 1: XU HƯỚNG (GIỮ NGUYÊN GIÁ TRỊ CỐT LÕI)
    with tabs[0]:
        c1, c2 = st.columns([2, 1])
        df_trend = df_display.groupby('THÁNG')['CP'].sum().reset_index()
        c1.plotly_chart(px.area(df_trend, x='THÁNG', y='CP', title="XU HƯỚNG CHI PHÍ"), use_container_width=True)
        c2.plotly_chart(px.pie(df_display, names='VÙNG', hole=0.5, title="CƠ CẤU VÙNG MIỀN"), use_container_width=True)

    # TAB 2: TÀI CHÍNH
    with tabs[1]:
        df_cost = df_display.groupby('LINH_KIỆN')['CP'].sum().sort_values(ascending=False).reset_index()
        st.plotly_chart(px.bar(df_cost, x='CP', y='LINH_KIỆN', orientation='h', title="CHI PHÍ THEO LINH KIỆN"), use_container_width=True)

    # TAB 3: SỨC KHỎE MÁY
    with tabs[2]:
        st.subheader("🩺 THIẾT BỊ CẢNH BÁO ĐỎ")
        health = df_display.groupby('MÃ_MÁY').agg({'NGÀY': 'count', 'CP': 'sum', 'KHÁCH_HÀNG': 'first'}).reset_index()
        health.columns = ['Mã Máy', 'Lần hỏng', 'Tổng phí', 'Khách hàng']
        st.dataframe(health[health['Lần hỏng'] >= 2].sort_values('Lần hỏng', ascending=False), use_container_width=True)

    # TAB 4: KHO LOGISTICS (NÂNG CẤP CHUYÊN SÂU - KHÔNG ẢNH HƯỞNG PHẦN KHÁC)
    with tabs[3]:
        st.subheader("📦 TRUNG TÂM ĐIỀU PHỐI KHO VẬN")
        wh_list = []
        for reg, raw in [("BẮC", df_bac_raw), ("NAM", df_nam_raw)]:
            if not raw.empty:
                for _, r in raw.iloc[1:].iterrows():
                    m_id = str(r.iloc[1]).strip()
                    if m_id and "MÃ" not in m_id.upper():
                        stt_info = (str(r.iloc[6]) + str(r.iloc[9])).upper()
                        if "OK" in stt_info: stt = "🔵 ĐÃ NHẬN"
                        elif "HỎNG" in stt_info or "LÝ" in stt_info: stt = "🔴 THANH LÝ"
                        else: stt = "🟡 ĐANG XỬ LÝ"
                        wh_list.append({"VÙNG": reg, "MÃ_MÁY": m_id, "TRẠNG_THÁI": stt})
        
        if wh_list:
            df_wh = pd.DataFrame(wh_list)
            k1, k2, k3 = st.columns(3)
            k1.metric("TỔNG TRONG KHO", f"{len(df_wh):,} máy")
            k2.metric("TỶ LỆ HOÀN TẤT", f"{(len(df_wh[df_wh['TRẠNG_THÁI']=='🔵 ĐÃ NHẬN'])/len(df_wh)*100):.1f}%")
            k3.metric("ĐANG TỒN ĐỌNG", f"{len(df_wh[df_wh['TRẠNG_THÁI']=='🟡 ĐANG XỬ LÝ']):,} máy")
            
            col_left, col_right = st.columns([3, 2])
            col_left.plotly_chart(px.histogram(df_wh, x="VÙNG", color="TRẠNG_THÁI", barmode="stack", title="THỐNG KÊ TRẠNG THÁI KHO"), use_container_width=True)
            col_right.table(df_wh.groupby(['VÙNG', 'TRẠNG_THÁI']).size().unstack(fill_value=0))
            
            search = st.text_input("🔍 Tra cứu nhanh mã máy trong kho:").upper()
            if search:
                res = df_wh[df_wh['MÃ_MÁY'].str.contains(search)]
                st.write(res)

    # TAB 5: AI & DỰ BÁO
    with tabs[4]:
        st.subheader("🧠 TRỢ LÝ CHIẾN LƯỢC AI")
        avg_cp = df_trend['CP'].mean() if not df_trend.empty else 0
        st.info(f"🔮 Dự báo chi phí tháng tới: {avg_cp * 1.05:,.0f} VNĐ")
        st.warning(f"🚨 Cảnh báo: Có {len(health[health['Lần hỏng'] >= 3])} thiết bị có rủi ro hỏng hóc hệ thống cao.")

if __name__ == "__main__":
    main()
