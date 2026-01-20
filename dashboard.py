import streamlit as st
import pandas as pd
import plotly.express as px
import io

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="STRATEGIC HUB V19.0", layout="wide", page_icon="🚀")

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
    # --- 2. SIDEBAR & NẠP DỮ LIỆU ---
    with st.sidebar:
        st.title("🚀 COMMAND CENTER")
        if st.button('🔄 REFRESH SYSTEM', type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        df_loi_raw = load_data(URL_LAPTOP_LOI)
        df_bac_raw = load_data(URL_MIEN_BAC)
        df_nam_raw = load_data(URL_DA_NANG)

        # Xử lý Tài chính (Giá trị cốt lõi)
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

        if not df_f.empty:
            st.divider()
            years = sorted(df_f['NĂM'].unique(), reverse=True)
            sel_year = st.selectbox("Chọn Năm", years)
            months = ["Tất cả"] + sorted(df_f[df_f['NĂM'] == sel_year]['THÁNG'].unique().tolist())
            sel_month = st.selectbox("Chọn Tháng", months)
            
            csv = df_f.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 TẢI BÁO CÁO TÀI CHÍNH", data=csv, file_name=f'Bao_cao_{sel_year}.csv', use_container_width=True)

    df_display = df_f[df_f['NĂM'] == sel_year]
    if sel_month != "Tất cả":
        df_display = df_display[df_display['THÁNG'] == sel_month]

    # --- 3. MÀN HÌNH CHÍNH ---
    st.title(f"🚀 STRATEGIC HUB V19.0 - {sel_year}")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TỔNG CHI PHÍ", f"{df_display['CP'].sum():,.0f} đ")
    m2.metric("TỔNG CA HƯ", f"{len(df_display)} ca")
    m3.metric("TỶ LỆ TRẢ MÁY (KHO)", "Đang đối soát...") # Sẽ cập nhật từ dữ liệu kho
    m4.metric("LOẠI LỖI CHÍNH", df_display['LINH_KIỆN'].value_counts().idxmax() if not df_display.empty else "N/A")

    tabs = st.tabs(["📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🩺 SỨC KHỎE MÁY", "📦 KHO LOGISTICS", "🧠 AI CẢNH BÁO"])

    # --- TAB 1: XU HƯỚNG (PHÂN BỔ CA HƯ) ---
    with tabs[0]:
        c1, c2 = st.columns([1, 1])
        with c1:
            fig_pie_ca = px.pie(df_display, names='VÙNG', title="TỶ LỆ PHÂN BỔ CA HƯ THEO VÙNG", hole=0.4)
            st.plotly_chart(fig_pie_ca, use_container_width=True)
        with c2:
            df_device_count = df_display['LINH_KIỆN'].value_counts().reset_index()
            fig_bar_ca = px.bar(df_device_count, x='count', y='LINH_KIỆN', orientation='h', title="THỐNG KÊ THIẾT BỊ HƯ NHIỀU NHẤT")
            st.plotly_chart(fig_bar_ca, use_container_width=True)
        
        st.write("---")
        df_trend = df_display.groupby('THÁNG')['CP'].sum().reset_index()
        st.plotly_chart(px.line(df_trend, x='THÁNG', y='CP', title="DIỄN BIẾN CHI PHÍ THEO THÁNG", markers=True), use_container_width=True)

    # --- TAB 2: TÀI CHÍNH ---
    with tabs[1]:
        st.plotly_chart(px.bar(df_display.groupby('LINH_KIỆN')['CP'].sum().reset_index().sort_values('CP'), x='CP', y='LINH_KIỆN', orientation='h', title="NGÂN SÁCH THEO LINH KIỆN"), use_container_width=True)

    # --- TAB 3: SỨC KHỎE MÁY ---
    with tabs[2]:
        st.subheader("🩺 DANH SÁCH MÁY HƯ NHIỀU LẦN (TOP RỦI RO)")
        health = df_display.groupby('MÃ_MÁY').agg({'NGÀY': 'count', 'CP': 'sum', 'KHÁCH': 'first'}).reset_index()
        health.columns = ['Mã Máy', 'Lần hỏng', 'Tổng phí', 'Khách hàng']
        st.dataframe(health[health['Lần hỏng'] >= 2].sort_values('Lần hỏng', ascending=False), use_container_width=True)

    # --- TAB 4: KHO LOGISTICS (LOGIC CHUẨN) ---
    with tabs[3]:
        st.subheader("📦 ĐỐI SOÁT KHO & TRẠNG THÁI SỬA CHỮA")
        wh_data = []
        # Logic: Cột G (index 6), I (index 8), J (index 9), L (index 11), N (index 13)
        for region, raw in [("BẮC", df_bac_raw), ("ĐÀ NẴNG", df_nam_raw)]:
            if not raw.empty:
                for _, r in raw.iloc[1:].iterrows():
                    m_id = str(r.iloc[1]).strip()
                    if not m_id or "MÃ" in m_id.upper(): continue
                    
                    # Lấy giá trị các cột theo chỉ dẫn của sếp
                    st_noi_bo = (str(r.iloc[6]) + str(r.iloc[8])).upper()
                    st_ngoai = (str(r.iloc[9]) + str(r.iloc[11])).upper()
                    st_giao = str(r.iloc[13]).upper()
                    
                    if "R" in st_giao:
                        trang_thai = "🟢 ĐÃ TRẢ CHI NHÁNH"
                    elif "OK" in st_noi_bo and "R" not in st_giao:
                        trang_thai = "🔵 ĐANG NẰM KHO NHẬN"
                    elif any(x in st_ngoai for x in ["OK", "ĐANG", "SỬA"]):
                        trang_thai = "🟡 ĐANG SỬA NGOÀI"
                    else:
                        trang_thai = "⚪ CHỜ KIỂM TRA"
                        
                    wh_data.append({"VÙNG": region, "MÃ_MÁY": m_id, "TRẠNG_THÁI": trang_thai})
        
        if wh_data:
            df_wh = pd.DataFrame(wh_data)
            
            # Thống kê tổng quan
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("KHO NHẬN TỒN", len(df_wh[df_wh['TRẠNG_THÁI']=="🔵 ĐANG NẰM KHO NHẬN"]))
            k2.metric("ĐANG SỬA NGOÀI", len(df_wh[df_wh['TRẠNG_THÁI']=="🟡 ĐANG SỬA NGOÀI"]))
            k3.metric("ĐÃ GIAO TRẢ", len(df_wh[df_wh['TRẠNG_THÁI']=="🟢 ĐÃ TRẢ CHI NHÁNH"]))
            k4.metric("TỔNG MÁY LƯU KHO", len(df_wh))

            st.write("---")
            c_wh1, c_wh2 = st.columns([2, 1])
            c_wh1.plotly_chart(px.histogram(df_wh, x="VÙNG", color="TRẠNG_THÁI", barmode="group", title="SO SÁNH KHO THEO VÙNG"), use_container_width=True)
            c_wh2.table(df_wh.groupby(['VÙNG', 'TRẠNG_THÁI']).size().unstack(fill_value=0))
        else:
            st.info("Chưa có dữ liệu kho...")

    # --- TAB 5: AI CẢNH BÁO (CHIẾN LƯỢC) ---
    with tabs[4]:
        st.subheader("🧠 TRỢ LÝ AI: DỰ ĐOÁN CHIẾN LƯỢC")
        
        # Tính toán dữ liệu cho AI
        total_machines = len(health)
        repeat_fail_rate = (len(health[health['Lần hỏng'] >= 2]) / total_machines * 100) if total_machines > 0 else 0
        avg_monthly_cost = df_trend['CP'].mean() if not df_trend.empty else 0
        
        col_ai1, col_ai2 = st.columns(2)
        with col_ai1:
            st.markdown(f"""
            ### 📊 Phân tích hiệu suất:
            * **Tỷ lệ thiết bị lỗi lặp lại:** {repeat_fail_rate:.1f}%
            * **Dự báo ngân sách tháng tới:** {avg_monthly_cost * 1.1:,.0f} đ (Dự phòng rủi ro 10%)
            * **Vùng rủi ro cao nhất:** {df_display['VÙNG'].value_counts().idxmax()}
            """)
        
        with col_ai2:
            st.markdown("### 💡 Khuyến nghị chiến lược:")
            if repeat_fail_rate > 15:
                st.error("🚨 **CẢNH BÁO:** Tỷ lệ lỗi lặp lại quá cao. Sếp cần xem lại chất lượng linh kiện đầu vào hoặc tay nghề thợ sửa ngoài.")
            else:
                st.success("✅ **ỔN ĐỊNH:** Chất lượng sửa chữa đang được duy trì tốt.")
            
            if len(df_wh[df_wh['TRẠNG_THÁI']=="🔵 ĐANG NẰM KHO NHẬN"]) > 50:
                st.warning("⚠️ **TỒN KHO:** Máy sửa xong đang ứ đọng tại kho nhận. Cần đẩy nhanh khâu giao trả (cột N) để giải phóng kho.")

if __name__ == "__main__":
    main()
