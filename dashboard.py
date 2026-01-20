import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CONFIG ---
st.set_page_config(page_title="STRATEGIC HUB V20.0", layout="wide", page_icon="🚀")

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
        st.title("🚀 STRATEGIC COMMAND")
        if st.button('🔄 REFRESH DATA', type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        df_loi_raw = load_data(URL_LAPTOP_LOI)
        df_bac_raw = load_data(URL_MIEN_BAC)
        df_nam_raw = load_data(URL_DA_NANG)

        # Xử lý Tài chính
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
            years = sorted(df_f['NĂM'].unique(), reverse=True)
            sel_year = st.selectbox("Năm báo cáo", years)
            months = ["Tất cả"] + sorted(df_f[df_f['NĂM'] == sel_year]['THÁNG'].unique().tolist())
            sel_month = st.selectbox("Tháng báo cáo", months)

    # Filter hiển thị
    df_display = df_f[df_f['NĂM'] == sel_year]
    if sel_month != "Tất cả":
        df_display = df_display[df_display['THÁNG'] == sel_month]

    st.title(f"🚀 STRATEGIC HUB V20.0")
    
    tabs = st.tabs(["📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🩺 SỨC KHỎE MÁY", "📦 KHO LOGISTICS", "🧠 AI CẢNH BÁO"])

    # --- TAB 1: XU HƯỚNG ---
    with tabs[0]:
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.pie(df_display, names='VÙNG', title="PHÂN BỔ CA HƯ THEO VÙNG", hole=0.4), use_container_width=True)
        device_stat = df_display['LINH_KIỆN'].value_counts().reset_index()
        c2.plotly_chart(px.bar(device_stat, x='count', y='LINH_KIỆN', orientation='h', title="THIẾT BỊ HƯ NHIỀU NHẤT"), use_container_width=True)

    # --- TAB 2: TÀI CHÍNH ---
    with tabs[1]:
        st.plotly_chart(px.bar(df_display.groupby('LINH_KIỆN')['CP'].sum().reset_index().sort_values('CP'), x='CP', y='LINH_KIỆN', orientation='h', title="NGÂN SÁCH CHI TIẾT"), use_container_width=True)

    # --- TAB 3: SỨC KHỎE MÁY (TRỌNG TÂM KIỂM TRA) ---
    with tabs[2]:
        st.subheader("📋 PHÂN TÍCH THIẾT BỊ LỖI LẶP LẠI (TẦN SUẤT > 2 LẦN)")
        # Gom nhóm theo mã máy
        health_report = df_f.groupby('MÃ_MÁY').agg({
            'NGÀY': 'count', 
            'CP': 'sum', 
            'KHÁCH': 'first',
            'LINH_KIỆN': lambda x: ', '.join(set(x))
        }).reset_index()
        health_report.columns = ['Mã Máy', 'Tổng số lần hỏng', 'Tổng chi phí tích lũy', 'Chủ sở hữu', 'Lịch sử linh kiện']
        
        # Lọc những máy lỗi trên 2 lần
        danger_zone = health_report[health_report['Tổng số lần hỏng'] > 2].sort_values('Tổng số lần hỏng', ascending=False)
        
        if not danger_zone.empty:
            st.error(f"⚠️ Phát hiện {len(danger_zone)} thiết bị có dấu hiệu hư hỏng hệ thống (Lỗi > 2 lần)")
            
            # Highlight bảng dữ liệu
            st.dataframe(danger_zone.style.format({"Tổng chi phí tích lũy": "{:,.0f} đ"})
                         .background_gradient(subset=['Tổng số lần hỏng'], cmap='Reds'), 
                         use_container_width=True)
            
            # Biểu đồ phân tích thiệt hại của nhóm máy này
            st.plotly_chart(px.scatter(danger_zone, x="Tổng số lần hỏng", y="Tổng chi phí tích lũy", 
                                       size="Tổng chi phí tích lũy", color="Mã Máy",
                                       title="SƠ ĐỒ TƯƠNG QUAN: TẦN SUẤT HỎNG & CHI PHÍ"), use_container_width=True)
        else:
            st.success("✅ Chưa phát hiện thiết bị nào hỏng trên 2 lần trong dữ liệu hiện tại.")

    # --- TAB 4: KHO LOGISTICS ---
    with tabs[3]:
        wh_data = []
        for reg, raw in [("BẮC", df_bac_raw), ("NAM", df_nam_raw)]:
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
            col_k1.plotly_chart(px.histogram(df_wh, x="VÙNG", color="TRẠNG_THÁI", barmode="group", title="THỐNG KÊ KHO"), use_container_width=True)
            col_k2.table(df_wh.groupby(['VÙNG', 'TRẠNG_THÁI']).size().unstack(fill_value=0))

    # --- TAB 5: AI CẢNH BÁO ---
    with tabs[4]:
        st.subheader("🧠 DỰ ĐOÁN CHIẾN LƯỢC AI")
        if not danger_zone.empty:
            total_loss = danger_zone['Tổng chi phí tích lũy'].sum()
            st.warning(f"AI nhận định: Sếp đã chi {total_loss:,.0f} đ cho nhóm máy hỏng lặp lại. Đề xuất thanh lý nhóm này để giảm 20% gánh nặng bảo trì tháng tới.")
        st.info("💡 Dự báo: Dựa trên trend, linh kiện lỗi cao nhất tháng tới vẫn sẽ là " + (df_display['LINH_KIỆN'].value_counts().idxmax() if not df_display.empty else "N/A"))

if __name__ == "__main__":
    main()
