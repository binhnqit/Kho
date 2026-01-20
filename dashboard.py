import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="Hệ Thống Quản Trị V16.7", layout="wide")

URL_FINANCE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?output=csv"
URL_KHO_BAC = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv"
URL_KHO_NAM = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"

@st.cache_data(ttl=60, show_spinner=False)
def fetch_fast(url):
    try:
        # Giảm thời gian chờ và nạp dữ liệu tinh gọn
        return pd.read_csv(url, on_bad_lines='skip', low_memory=False).fillna("0")
    except:
        return pd.DataFrame()

def main():
    st.sidebar.title("🛡️ HỆ THỐNG ĐIỀU HÀNH")
    if st.sidebar.button('🔄 CẬP NHẬT NHANH', type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Nạp dữ liệu đồng thời
    with st.spinner('🚀 Đang tăng tốc kết nối Cloud...'):
        df_f_raw = fetch_fast(URL_FINANCE)
        df_kb_raw = fetch_fast(URL_KHO_BAC)
        df_kn_raw = fetch_fast(URL_KHO_NAM)

    # --- 2. XỬ LÝ TÀI CHÍNH ---
    df_f = pd.DataFrame()
    if not df_f_raw.empty:
        clean_f = []
        for _, row in df_f_raw.iloc[1:].iterrows():
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

    # --- 3. HIỂN THỊ GIAO DIỆN ---
    st.title("🛡️ HỆ THỐNG QUẢN TRỊ CHIẾN LƯỢC V16.7")
    
    if df_f.empty:
        st.error("❌ Link Tài chính không phản hồi. Sếp hãy kiểm tra lại quyền chia sẻ CSV trên Google Sheets.")
        st.stop()

    t = st.tabs(["📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🧠 AI ANALYTICS", "🩺 SỨC KHỎE", "📦 KHO"])

    with t[0]:
        c1, c2 = st.columns([2, 1])
        df_l = df_f.groupby('THÁNG')['CP'].sum().reset_index()
        c1.plotly_chart(px.line(df_l, x='THÁNG', y='CP', title="Xu hướng chi phí", markers=True), use_container_width=True)
        c2.plotly_chart(px.pie(df_f, names='VÙNG', hole=0.4, title="Tỉ lệ vùng"), use_container_width=True)

    with t[1]:
        df_b = df_f.groupby('LINH_KIỆN')['CP'].sum().sort_values(ascending=False).reset_index()
        st.plotly_chart(px.bar(df_b, x='LINH_KIỆN', y='CP', color='CP', title="Chi phí linh kiện"), use_container_width=True)

    with t[2]:
        st.metric("TỔNG CHI THỰC TẾ", f"{df_f['CP'].sum():,.0f} VNĐ")
        st.success(f"✅ Đã xử lý thành công {len(df_f)} bản ghi tài chính.")

    with t[3]:
        df_h = df_f.groupby('MÃ_MÁY').agg({'NGÀY': 'count', 'CP': 'sum'}).reset_index()
        df_h.columns = ['Mã Máy', 'Lần hỏng', 'Tổng phí']
        st.dataframe(df_h.sort_values('Lần hỏng', ascending=False), use_container_width=True)

    with t[4]:
        st.subheader("📦 Điều hành Kho & Logistics")
        wh = []
        for r_n, r_d in [("MIỀN BẮC", df_kb_raw), ("ĐÀ NẴNG", df_kn_raw)]:
            if not r_d.empty:
                for _, r in r_d.iloc[1:].iterrows():
                    m_id = str(r.iloc[1]).strip()
                    if m_id and "MÃ" not in m_id.upper():
                        wh.append({"VÙNG": r_n, "MÃ_MÁY": m_id, "STT": "ĐANG XỬ LÝ"})
        if wh:
            st.table(pd.DataFrame(wh).groupby(['VÙNG', 'STT']).size().unstack(fill_value=0))
        else:
            st.info("Dữ liệu Kho đang được đồng bộ...")

if __name__ == "__main__":
    main()
