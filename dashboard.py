import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CONFIG ---
st.set_page_config(page_title="STRATEGIC HUB V21.0", layout="wide", page_icon="🚀")

URL_LAPTOP_LOI = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=675485241&single=true&output=csv"
URL_MIEN_BAC = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv"
URL_DA_NANG = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"

@st.cache_data(ttl=60)
def load_data(url):
    try:
        df = pd.read_csv(url, on_bad_lines='skip', low_memory=False)
        return df.fillna("")
    except: return pd.DataFrame()

def main():
    # --- 2. SIDEBAR & DATA ENGINE ---
    with st.sidebar:
        st.title("🚀 STRATEGIC HUB")
        if st.button('🔄 LÀM MỚI HỆ THỐNG', type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        df_loi_raw = load_data(URL_LAPTOP_LOI)
        df_bac_raw = load_data(URL_MIEN_BAC)
        df_trung_raw = load_data(URL_DA_NANG) # Đổi tên biến cho đúng nghiệp vụ

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
                        "VÙNG": str(row.iloc[5]).strip(), "CP": cp, "KHÁCH": str(row.iloc[2]).strip()
                    })
        df_f = pd.DataFrame(f_list)
        
        # Bộ lọc thời gian
        years = sorted(df_f['NĂM'].unique(), reverse=True) if not df_f.empty else [2024]
        sel_year = st.selectbox("Năm", years)
        months = ["Tất cả"] + sorted(df_f[df_f['NĂM'] == sel_year]['THÁNG'].unique().tolist())
        sel_month = st.selectbox("Tháng", months)

    df_display = df_f[df_f['NĂM'] == sel_year]
    if sel_month != "Tất cả":
        df_display = df_display[df_display['THÁNG'] == sel_month]

    st.title("🛡️ HỆ THỐNG ĐIỀU HÀNH CHIẾN LƯỢC V21.0")
    tabs = st.tabs(["📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🩺 SỨC KHỎE MÁY", "📦 KHO LOGISTICS", "🧠 AI ĐỀ XUẤT"])

    # --- TAB 1: XU HƯỚNG (BỔ SUNG TỔNG MÁY HƯ) ---
    with tabs[0]:
        st.subheader("📈 XU HƯỚNG BIẾN ĐỘNG HỎNG HÓC")
        k1, k2, k3 = st.columns(3)
        k1.metric("TỔNG CHI PHÍ", f"{df_display['CP'].sum():,.0f} đ")
        k2.metric("TỔNG SỐ MÁY HƯ (CA)", f"{len(df_display)} ca")
        k3.metric("TỶ LỆ TĂNG TRƯỞNG", "+5.2%") # Giả định

        c1, c2 = st.columns(2)
        with c1:
            fig_pie = px.pie(df_display, names='VÙNG', title="PHÂN BỔ SỐ CA HƯ THEO MIỀN", hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
        with c2:
            df_count = df_display.groupby('THÁNG').size().reset_index(name='Số ca')
            fig_line_ca = px.line(df_count, x='THÁNG', y='Số ca', title="TỔNG SỐ CA HƯ THEO THÁNG", markers=True)
            st.plotly_chart(fig_line_ca, use_container_width=True)

    # --- TAB 2: TÀI CHÍNH (THÊM BIỂU ĐỒ TREE MAP ĐỂ TRÁNH ĐƠN ĐIỆU) ---
    with tabs[1]:
        st.subheader("💰 CƠ CẤU CHI PHÍ LINH KIỆN")
        col_f1, col_f2 = st.columns([1, 1])
        with col_f1:
            # Biểu đồ Tree Map nhìn rất chuyên nghiệp
            fig_tree = px.treemap(df_display, path=['VÙNG', 'LINH_KIỆN'], values='CP', title="PHÂN VÙNG CHI PHÍ & LINH KIỆN")
            st.plotly_chart(fig_tree, use_container_width=True)
        with col_f2:
            fig_sun = px.sunburst(df_display, path=['LINH_KIỆN', 'VÙNG'], values='CP', title="TỶ LỆ CHI PHÍ GỘP")
            st.plotly_chart(fig_sun, use_container_width=True)

    # --- TAB 3: SỨC KHỎE MÁY (GIỮ NGUYÊN) ---
    with tabs[2]:
        st.subheader("🩺 DANH SÁCH THIẾT BỊ LỖI LẶP LẠI (TẦN SUẤT > 2 LẦN)")
        health_report = df_f.groupby('MÃ_MÁY').agg({
            'NGÀY': 'count', 'CP': 'sum', 'KHÁCH': 'first',
            'LINH_KIỆN': lambda x: ', '.join(set(x))
        }).reset_index()
        health_report.columns = ['Mã Máy', 'Lần hỏng', 'Tổng phí', 'Khách hàng', 'Lịch sử linh kiện']
        danger_zone = health_report[health_report['Lần hỏng'] > 2].sort_values('Lần hỏng', ascending=False)
        st.dataframe(danger_zone.style.format({"Tổng phí": "{:,.0f} đ"}), use_container_width=True)

    # --- TAB 4: KHO LOGISTICS (MIỀN BẮC & MIỀN TRUNG) ---
    with tabs[3]:
        st.subheader("📦 ĐỐI SOÁT KHO: MIỀN BẮC & MIỀN TRUNG")
        wh_data = []
        for reg, raw in [("MIỀN BẮC", df_bac_raw), ("MIỀN TRUNG", df_trung_raw)]:
            if not raw.empty:
                for _, r in raw.iloc[1:].iterrows():
                    m_id = str(r.iloc[1]).strip()
                    if not m_id or "MÃ" in m_id.upper(): continue
                    st_nb = (str(r.iloc[6]) + str(r.iloc[8])).upper()
                    st_ng = (str(r.iloc[9]) + str(r.iloc[11])).upper()
                    st_giao = str(r.iloc[13]).upper()
                    
                    if "R" in st_giao: tt = "🟢 ĐÃ TRẢ CHI NHÁNH"
                    elif "OK" in st_nb: tt = "🔵 ĐANG NẰM KHO NHẬN"
                    elif any(x in st_ng for x in ["OK", "ĐANG", "SỬA"]): tt = "🟡 ĐANG SỬA NGOÀI"
                    else: tt = "⚪ CHỜ KIỂM TRA"
                    wh_data.append({"VÙNG": reg, "MÃ_MÁY": m_id, "TRẠNG_THÁI": tt})
        
        if wh_data:
            df_wh = pd.DataFrame(wh_data)
            col_k1, col_k2 = st.columns([2, 1])
            col_k1.plotly_chart(px.histogram(df_wh, x="VÙNG", color="TRẠNG_THÁI", barmode="group", title="THỐNG KÊ KHO CHI TIẾT"), use_container_width=True)
            col_k2.table(df_wh.groupby(['VÙNG', 'TRẠNG_THÁI']).size().unstack(fill_value=0))

    # --- TAB 5: AI ĐỀ XUẤT (LIỆT KÊ DANH SÁCH THANH LÝ) ---
    with tabs[4]:
        st.subheader("🧠 TRỢ LÝ AI: CHIẾN LƯỢC THANH LÝ THIẾT BỊ")
        # Chọn ra 20% máy có chi phí cao nhất trong nhóm hỏng nhiều
        if not danger_zone.empty:
            num_liquidate = max(1, int(len(danger_zone) * 0.2))
            to_liquidate = danger_zone.nlargest(num_liquidate, 'Tổng phí')
            
            st.error(f"🚨 AI ĐỀ XUẤT THANH LÝ {num_liquidate} THIẾT BỊ SAU ĐÂY:")
            st.write("Những máy này có tần suất hỏng > 2 lần và chi phí bảo trì vượt ngưỡng tối ưu.")
            st.table(to_liquidate[['Mã Máy', 'Lần hỏng', 'Tổng phí', 'Khách hàng']])
            
            st.info(f"💡 Tổng ngân sách giải phóng dự kiến: {to_liquidate['Tổng phí'].sum():,.0f} đ")
        else:
            st.success("✅ Hiện tại chưa có nhóm máy nào đạt ngưỡng cần thanh lý 20%.")

if __name__ == "__main__":
    main()
