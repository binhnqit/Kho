import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CẤU HÌNH & LINK DỮ LIỆU MỚI ---
st.set_page_config(page_title="Hệ Thống Quản Trị V16.8", layout="wide")

# Link sếp vừa cung cấp
URL_LAPTOP_LOI = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=675485241&single=true&output=csv"
URL_MIEN_BAC = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv"
URL_DA_NANG = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"

@st.cache_data(ttl=60, show_spinner=False)
def load_data(url):
    try:
        df = pd.read_csv(url, on_bad_lines='skip', low_memory=False)
        return df.fillna("0")
    except:
        return pd.DataFrame()

def main():
    st.sidebar.title("🛡️ CONTROL CENTER")
    if st.sidebar.button('🔄 CẬP NHẬT DỮ LIỆU', type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Nạp dữ liệu từ 3 nguồn
    with st.spinner('🚀 Đang kết nối dữ liệu Cloud...'):
        df_loi_raw = load_data(URL_LAPTOP_LOI)
        df_bac_raw = load_data(URL_MIEN_BAC)
        df_nam_raw = load_data(URL_DA_NANG)

    # --- 2. XỬ LÝ DỮ LIỆU TÀI CHÍNH (Laptop lỗi - Thay thế) ---
    df_f = pd.DataFrame()
    if not df_loi_raw.empty:
        clean_f = []
        for _, row in df_loi_raw.iloc[1:].iterrows():
            ma = str(row.iloc[1]).strip()
            if not ma or "MÃ" in ma.upper(): continue
            ngay = pd.to_datetime(row.iloc[6], dayfirst=True, errors='coerce')
            if pd.notnull(ngay):
                cp = pd.to_numeric(str(row.iloc[8]).replace(',', ''), errors='coerce') or 0
                clean_f.append({
                    "NGÀY": ngay, "THÁNG": ngay.month, "MÃ_MÁY": ma, 
                    "LINH_KIỆN": str(row.iloc[3]).strip(),
                    "VÙNG": str(row.iloc[5]).strip() or "KHÁC", "CP": cp
                })
        df_f = pd.DataFrame(clean_f)

    # --- 3. GIAO DIỆN ---
    st.title("🛡️ HỆ THỐNG QUẢN TRỊ CHIẾN LƯỢC V16.8")
    
    if df_f.empty:
        st.error("❌ Không tìm thấy dữ liệu trong Link Laptop lỗi. Sếp kiểm tra xem Sheet 'laptop lỗi - thay thế' có dữ liệu từ dòng thứ 2 không nhé.")
        st.stop()

    tabs = st.tabs(["📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🧠 AI ANALYTICS", "🩺 SỨC KHỎE", "📦 KHO LOGISTICS"])

    with tabs[0]: # XU HƯỚNG
        c1, c2 = st.columns([2, 1])
        df_line = df_f.groupby('THÁNG')['CP'].sum().reset_index()
        c1.plotly_chart(px.line(df_line, x='THÁNG', y='CP', title="Biến động chi phí tháng", markers=True), use_container_width=True)
        c2.plotly_chart(px.pie(df_f, names='VÙNG', hole=0.4, title="Cơ cấu vùng miền"), use_container_width=True)

    with tabs[1]: # TÀI CHÍNH
        df_bar = df_f.groupby('LINH_KIỆN')['CP'].sum().sort_values(ascending=False).reset_index()
        st.plotly_chart(px.bar(df_bar, x='LINH_KIỆN', y='CP', color='CP', title="Chi phí theo linh kiện"), use_container_width=True)

    with tabs[2]: # AI
        st.metric("TỔNG CHI PHÍ THỰC TẾ", f"{df_f['CP'].sum():,.0f} VNĐ")
        st.info(f"💡 Hệ thống đang quản lý {len(df_f)} hồ sơ thay thế linh kiện lỗi.")

    with tabs[3]: # SỨC KHỎE
        df_h = df_f.groupby('MÃ_MÁY').agg({'NGÀY': 'count', 'CP': 'sum'}).reset_index()
        df_h.columns = ['Mã Máy', 'Lần hỏng', 'Tổng phí']
        st.dataframe(df_h.sort_values('Lần hỏng', ascending=False), use_container_width=True)

    with tabs[4]: # KHO LOGISTICS
        st.subheader("📦 Đối soát Kho Miền Bắc & Đà Nẵng")
        wh = []
        for vung, raw in [("MIỀN BẮC", df_bac_raw), ("ĐÀ NẴNG", df_nam_raw)]:
            if not raw.empty:
                for _, r in raw.iloc[1:].iterrows():
                    m_id = str(r.iloc[1]).strip()
                    if m_id and "MÃ" not in m_id.upper():
                        # Lấy trạng thái từ cột G (index 6) và J (index 9)
                        kttt = str(r.iloc[6]).upper()
                        sbn = str(r.iloc[9]).upper()
                        if "OK" in (kttt + sbn): stt = "🔵 KHO NHẬN"
                        elif "HỎNG" in (kttt + sbn): stt = "🔴 LỖI/HỎNG"
                        else: stt = "🟡 ĐANG XỬ LÝ"
                        wh.append({"VÙNG": vung, "MÃ_MÁY": m_id, "TRẠNG_THÁI": stt})
        if wh:
            df_wh = pd.DataFrame(wh)
            st.table(df_wh.groupby(['VÙNG', 'TRẠNG_THÁI']).size().unstack(fill_value=0))
        else:
            st.warning("Đang chờ dữ liệu từ các link Kho...")

if __name__ == "__main__":
    main()
