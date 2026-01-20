import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CẤU HÌNH & KẾT NỐI ---
st.set_page_config(page_title="Hệ Thống Quản Trị V16.0", layout="wide")

SHARED_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?output=csv"

@st.cache_data(ttl=300, show_spinner=False)
def load_unified_data(url):
    try:
        df = pd.read_csv(url, dtype=str, on_bad_lines='skip', low_memory=False)
        return df.fillna("0")
    except:
        return pd.DataFrame()

def main():
    with st.sidebar:
        st.title("EXECUTIVE HUB")
        if st.button('🔄 ĐỒNG BỘ HỆ THỐNG', type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    df_raw = load_unified_data(SHARED_URL)
    
    if df_raw.empty or len(df_raw.columns) < 10:
        st.warning("🔄 Đang chờ nạp dữ liệu từ Google Sheets...")
        return

    # --- 2. XỬ LÝ DỮ LIỆU (FIX KEYERROR TRIỆT ĐỂ) ---
    try:
        clean_f = []
        for _, row in df_raw.iloc[1:].iterrows():
            ma_may = str(row.iloc[1]).strip() # Cột B
            if not ma_may or "MÃ" in ma_may.upper(): continue
            
            ngay = pd.to_datetime(row.iloc[6], dayfirst=True, errors='coerce') # Cột G
            if pd.notnull(ngay):
                # Ép kiểu số ngay lập tức để tránh lỗi tính toán
                cp_dk = pd.to_numeric(str(row.iloc[7]).replace(',', ''), errors='coerce') or 0
                cp_tt = pd.to_numeric(str(row.iloc[8]).replace(',', ''), errors='coerce') or 0
                
                clean_f.append([
                    ngay, ngay.year, ngay.month, ma_may, 
                    str(row.iloc[3]).strip(), # Linh kiện
                    str(row.iloc[5]).strip(), # Vùng
                    cp_dk, cp_tt, cp_tt - cp_dk
                ])
        
        # KHỞI TẠO DATAFRAME VỚI TÊN CỘT CHUẨN XÁC
        cols = ["NGÀY", "NĂM", "THÁNG", "MÃ_MÁY", "LINH_KIỆN", "VÙNG", "CP_DU_KIEN", "CP_THUC_TE", "CHENH_LECH"]
        df_f = pd.DataFrame(clean_f, columns=cols)

        # Xử lý Kho vận
        clean_w = []
        for _, row in df_raw.iloc[1:].iterrows():
            ma = str(row.iloc[1]).strip()
            if not ma or "MÃ" in ma.upper(): continue
            kttt, snb, sbn, gl = str(row.iloc[6]).upper(), str(row.iloc[7]).upper(), str(row.iloc[9]).upper(), str(row.iloc[13]).upper().strip()
            if gl == "R": stt = "🟢 ĐÃ TRẢ (R)"
            elif any(x in (kttt + sbn) for x in ["THANH LÝ", "HỎNG"]): stt = "🔴 THANH LÝ"
            elif "OK" in (kttt + snb + sbn): stt = "🔵 KHO NHẬN (ĐỢI R)"
            else: stt = "🟡 ĐANG XỬ LÝ"
            clean_w.append({"VÙNG": str(row.iloc[5]), "MÃ_MÁY": ma, "TRẠNG_THÁI": stt})
        df_w = pd.DataFrame(clean_w)

    except Exception as e:
        st.error(f"❌ Lỗi cấu trúc: {e}")
        return

    # --- 3. HIỂN THỊ GIAO DIỆN (GIỮ NGUYÊN NỘI DUNG SẾP LÀM) ---
    st.success("✅ Hệ thống đã sẵn sàng!")
    tabs = st.tabs(["📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🤖 AI", "📁 DỮ LIỆU", "🩺 SỨC KHỎE", "🔮 DỰ BÁO", "📦 KHO LOGISTICS"])

    with tabs[0]: # XU HƯỚNG
        if not df_f.empty:
            c1, c2 = st.columns(2)
            # Dùng tên cột đã được fix chuẩn ở bước trên
            c1.plotly_chart(px.bar(df_f.groupby('THÁNG').size().reset_index(name='Số ca'), x='THÁNG', y='Số ca', title="Tần suất hỏng hóc"), use_container_width=True)
            c2.plotly_chart(px.pie(df_f, names='VÙNG', title="Tỷ lệ vùng miền"), use_container_width=True)

    with tabs[1]: # TÀI CHÍNH
        if not df_f.empty:
            chart_data = df_f.groupby('LINH_KIỆN')[['CP_DU_KIEN', 'CP_THUC_TE']].sum().reset_index()
            st.plotly_chart(px.bar(chart_data, x='LINH_KIỆN', y=['CP_DU_KIEN', 'CP_THUC_TE'], barmode='group', title="Đối soát ngân sách"), use_container_width=True)

    with tabs[2]: # AI - NƠI XẢY RA LỖI KEYERROR CŨ
        if not df_f.empty:
            tong_chi = df_f['CP_THUC_TE'].sum()
            st.info(f"Tổng hợp: {len(df_f)} ca sửa chữa. Tổng chi thực tế: {tong_chi:,.0f} VNĐ.")

    with tabs[3]: st.dataframe(df_f, use_container_width=True)

    with tabs[6]: # KHO LOGISTICS
        st.subheader("📦 Quản Trị Kho Vận")
        if not df_w.empty:
            summary = df_w.groupby(['VÙNG', 'TRẠNG_THÁI']).size().unstack(fill_value=0)
            st.table(summary)

if __name__ == "__main__":
    main()
