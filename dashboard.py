import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="Hệ Thống Quản Trị V16.6", layout="wide")

URL_FINANCE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?output=csv"
URL_KHO_BAC = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv"
URL_KHO_NAM = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"

@st.cache_data(ttl=300)
def fetch_data(url):
    try:
        df = pd.read_csv(url, on_bad_lines='skip', low_memory=False)
        return df.fillna("0")
    except:
        return pd.DataFrame()

def main():
    st.sidebar.title("🛡️ CONTROL CENTER")
    if st.sidebar.button('🔄 LÀM MỚI DỮ LIỆU', type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Nạp dữ liệu
    df_f_raw = fetch_data(URL_FINANCE)
    df_kb_raw = fetch_data(URL_KHO_BAC)
    df_kn_raw = fetch_data(URL_KHO_NAM)

    # --- 2. XỬ LÝ TÀI CHÍNH ---
    df_f = pd.DataFrame()
    if not df_f_raw.empty and len(df_f_raw.columns) > 8:
        clean_f = []
        for _, row in df_f_raw.iloc[1:].iterrows():
            ma = str(row.iloc[1]).strip()
            if not ma or "MÃ" in ma.upper(): continue
            ngay = pd.to_datetime(row.iloc[6], dayfirst=True, errors='coerce')
            if pd.notnull(ngay):
                cp = pd.to_numeric(str(row.iloc[8]).replace(',', ''), errors='coerce') or 0
                clean_f.append({
                    "NGÀY": ngay, "THÁNG": ngay.month,
                    "MÃ_MÁY": ma, "LINH_KIỆN": str(row.iloc[3]).strip(),
                    "VÙNG": str(row.iloc[5]).strip() or "KHÁC", 
                    "CP_THUC_TE": cp
                })
        df_f = pd.DataFrame(clean_f)

    if df_f.empty:
        st.warning("⚠️ Đang kết nối dữ liệu...")
        return

    # --- 3. BỘ LỌC & GIAO DIỆN ---
    vung_list = sorted(df_f['VÙNG'].unique())
    sel_vung = st.sidebar.multiselect("📍 Vùng", options=vung_list, default=vung_list)
    df_final = df_f[df_f['VÙNG'].isin(sel_vung)]

    st.title("🛡️ HỆ THỐNG QUẢN TRỊ CHIẾN LƯỢC V16.6")
    t = st.tabs(["📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🧠 AI ANALYTICS", "📁 DỮ LIỆU", "🩺 SỨC KHỎE", "📦 KHO"])

    # TAB 1: XU HƯỚNG
    with t[0]:
        c1, c2 = st.columns([2, 1])
        df_line = df_final.groupby('THÁNG')['CP_THUC_TE'].sum().reset_index()
        fig1 = px.line(df_line, x='THÁNG', y='CP_THUC_TE', title="Biến động chi phí", markers=True)
        c1.plotly_chart(fig1, use_container_width=True)
        fig2 = px.pie(df_final, names='VÙNG', hole=0.4, title="Tỷ lệ vùng miền")
        c2.plotly_chart(fig2, use_container_width=True)

    # TAB 2: TÀI CHÍNH
    with t[1]:
        df_bar = df_final.groupby('LINH_KIỆN')['CP_THUC_TE'].sum().sort_values(ascending=False).reset_index()
        # Rút ngắn câu lệnh để tránh lỗi Syntax ngắt dòng
        fig3 = px.bar(df_bar, x='LINH_KIỆN', y='CP_THUC_TE', color='CP_THUC_TE', title="Chi phí linh kiện")
        st.plotly_chart(fig3, use_container_width=True)

    # TAB 3: AI ANALYTICS
    with t[2]:
        tong = df_final['CP_THUC_TE'].sum()
        st.metric("TỔNG CHI THỰC TẾ", f"{tong:,.0f} VNĐ")
        st.info(f"AI: Ghi nhận {len(df_final)} vụ việc sửa chữa.")

    # TAB 4: DỮ LIỆU
    with t[3]:
        st.dataframe(df_final, use_container_width=True)

    # TAB 5: SỨC KHỎE
    with t[4]:
        df_h = df_f.groupby('MÃ_MÁY').agg({'NGÀY': 'count', 'CP_THUC_TE': 'sum'}).reset_index()
        df_h.columns = ['Mã Máy', 'Lần hỏng', 'Tổng phí']
        st.dataframe(df_h.sort_values('Lần hỏng', ascending=False), use_container_width=True)

    # TAB 6: KHO
    with t[5]:
        wh = []
        for r_name, r_df in [("MIỀN BẮC", df_kb_raw), ("ĐÀ NẴNG", df_kn_raw)]:
            if not r_df.empty:
                for _, r in r_df.iloc[1:].iterrows():
                    m_id = str(r.iloc[1]).strip()
                    if m_id and "MÃ" not in m_id.upper():
                        wh.append({"VÙNG": r_name, "MÃ_MÁY": m_id, "TRẠNG_THÁI": "CHỜ XỬ LÝ"})
        if wh:
            st.table(pd.DataFrame(wh).groupby(['VÙNG', 'TRẠNG_THÁI']).size().unstack(fill_value=0))

if __name__ == "__main__":
    main()
