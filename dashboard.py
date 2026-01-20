import streamlit as st
import pandas as pd
import plotly.express as px
import io

# --- 1. CONFIG ---
st.set_page_config(page_title="STRATEGIC HUB V17.5", layout="wide", page_icon="🚀")

URL_LAPTOP_LOI = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=675485241&single=true&output=csv"
URL_MIEN_BAC = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv"
URL_DA_NANG = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"

@st.cache_data(ttl=60)
def load_data(url):
    try:
        return pd.read_csv(url, on_bad_lines='skip', low_memory=False).fillna("0")
    except: return pd.DataFrame()

def main():
    # --- SIDEBAR: BỘ LỌC CHUYÊN NGHIỆP ---
    with st.sidebar:
        st.title("🚀 COMMAND CENTER")
        if st.button('🔄 REFRESH SYSTEM', type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.divider()
        st.subheader("🗓️ BỘ LỌC THỜI GIAN")
        
        # Nạp dữ liệu
        df_loi_raw = load_data(URL_LAPTOP_LOI)
        df_bac_raw = load_data(URL_MIEN_BAC)
        df_nam_raw = load_data(URL_DA_NANG)
        
        # Xử lý nhanh dữ liệu tài chính để lấy năm/tháng
        f_list = []
        if not df_loi_raw.empty:
            for _, row in df_loi_raw.iloc[1:].iterrows():
                ngay = pd.to_datetime(row.iloc[6], dayfirst=True, errors='coerce')
                if pd.notnull(ngay):
                    f_list.append({
                        "NGÀY": ngay, "NĂM": ngay.year, "THÁNG": ngay.month,
                        "MÃ_MÁY": str(row.iloc[1]).strip(), "LINH_KIỆN": str(row.iloc[3]).strip(),
                        "VÙNG": str(row.iloc[5]).strip(), 
                        "CP": pd.to_numeric(str(row.iloc[8]).replace(',', ''), errors='coerce') or 0
                    })
        df_f = pd.DataFrame(f_list)

        if not df_f.empty:
            # Lọc Năm & Tháng
            years = sorted(df_f['NĂM'].unique(), reverse=True)
            sel_year = st.selectbox("Chọn Năm", years)
            
            months = ["Tất cả"] + sorted(df_f[df_f['NĂM'] == sel_year]['THÁNG'].unique().tolist())
            sel_month = st.selectbox("Chọn Tháng", months)
            
            st.divider()
            st.subheader("📥 XUẤT BÁO CÁO")
            # Tạo file CSV để tải
            csv = df_f.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 TẢI BÁO CÁO CHI TIẾT", data=csv, file_name=f'Bao_cao_{sel_year}.csv', mime='text/csv', use_container_width=True)

    # Lọc dữ liệu hiển thị
    df_display = df_f[df_f['NĂM'] == sel_year]
    if sel_month != "Tất cả":
        df_display = df_display[df_display['THÁNG'] == sel_month]

    # --- MAIN UI ---
    st.title("🚀 STRATEGIC HUB V17.5")
    
    # 4 Chỉ số cốt lõi (Elon Musk Style)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("TỔNG CHI PHÍ", f"{df_display['CP'].sum():,.0f} đ")
    c2.metric("SỐ CA XỬ LÝ", f"{len(df_display)} ca")
    c3.metric("TRUNG BÌNH/CA", f"{(df_display['CP'].mean() if len(df_display)>0 else 0):,.0f} đ")
    c4.metric("LOẠI LỖI CAO NHẤT", df_display['LINH_KIỆN'].value_counts().idxmax() if not df_display.empty else "N/A")

    st.divider()

    # --- TABS HỆ THỐNG ---
    tabs = st.tabs(["📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🩺 SỨC KHỎE MÁY", "📦 KHO LOGISTICS", "🧠 TRỢ LÝ AI & DỰ BÁO"])

    with tabs[0]: # XU HƯỚNG
        col_a, col_b = st.columns([2, 1])
        df_trend = df_display.groupby('THÁNG')['CP'].sum().reset_index()
        col_a.plotly_chart(px.area(df_trend, x='THÁNG', y='CP', title="BIỂU ĐỒ CHI PHÍ THEO THỜI GIAN"), use_container_width=True)
        col_b.plotly_chart(px.pie(df_display, names='VÙNG', hole=0.5, title="CƠ CẤU VÙNG MIỀN"), use_container_width=True)

    with tabs[1]: # TÀI CHÍNH
        df_cost = df_display.groupby('LINH_KIỆN')['CP'].sum().sort_values(ascending=False).reset_index()
        st.plotly_chart(px.bar(df_cost, x='CP', y='LINH_KIỆN', orientation='h', title="CHI PHÍ TÍCH LŨY THEO LINH KIỆN"), use_container_width=True)

    with tabs[2]: # SỨC KHỎE
        st.subheader("🩺 THIẾT BỊ CẢNH BÁO ĐỎ (HỎNG NHIỀU)")
        health = df_display.groupby('MÃ_MÁY').agg({'NGÀY': 'count', 'CP': 'sum'}).reset_index()
        health.columns = ['Mã Máy', 'Số lần hỏng', 'Tổng chi phí']
        st.dataframe(health[health['Số lần hỏng'] >= 2].sort_values('Số lần hỏng', ascending=False), use_container_width=True)

    with tabs[3]: # KHO
        st.subheader("📦 ĐỐI SOÁT KHO 2 MIỀN")
        wh_data = []
        for reg, raw in [("BẮC", df_bac_raw), ("NAM", df_nam_raw)]:
            if not raw.empty:
                for _, r in raw.iloc[1:].iterrows():
                    m = str(r.iloc[1]).strip()
                    if m and "MÃ" not in m.upper():
                        stt_raw = (str(r.iloc[6]) + str(r.iloc[9])).upper()
                        stt = "🔵 ĐÃ NHẬN" if "OK" in stt_raw else "🟡 ĐANG XỬ LÝ"
                        if "HỎNG" in stt_raw or "LÝ" in stt_raw: stt = "🔴 THANH LÝ"
                        wh_data.append({"VÙNG": reg, "MÃ_MÁY": m, "TRẠNG_THÁI": stt})
        if wh_data:
            st.table(pd.DataFrame(wh_data).groupby(['VÙNG', 'TRẠNG_THÁI']).size().unstack(fill_value=0))

    with tabs[4]: # AI & DỰ BÁO
        st.subheader("🧠 TRỢ LÝ AI ANALYTICS")
        
        # 1. Dự báo
        last_month_cp = df_trend['CP'].iloc[-1] if not df_trend.empty else 0
        forecast = last_month_cp * 1.05 # Dự báo tăng 5% dựa trên trend
        
        a1, a2 = st.columns(2)
        with a1:
            st.info(f"🔮 **Dự báo chi phí tháng tới:** {forecast:,.0f} VNĐ (Dựa trên tăng trưởng 5%)")
            st.write("---")
            st.write("🤖 **Nhận định của AI:**")
            if last_month_cp > df_trend['CP'].mean():
                st.warning("⚠️ Chi phí tháng gần nhất đang cao hơn mức trung bình. Sếp nên kiểm tra lại quy trình nhập linh kiện.")
            else:
                st.success("✅ Ngân sách đang được kiểm soát tốt.")
        
        with a2:
            st.subheader("🚨 CẢNH BÁO HỆ THỐNG")
            high_risk = health[health['Số lần hỏng'] >= 3]
            if not high_risk.empty:
                st.error(f"Phát hiện {len(high_risk)} máy hỏng trên 3 lần. Đề xuất thanh lý ngay để tối ưu chi phí.")
            else:
                st.write("Chưa phát hiện rủi ro nghiêm trọng.")

if __name__ == "__main__":
    main()
