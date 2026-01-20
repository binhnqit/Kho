import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CẤU HÌNH & KẾT NỐI ---
st.set_page_config(page_title="Hệ Thống Quản Trị V15.9", layout="wide")

SHARED_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?output=csv"

@st.cache_data(ttl=300, show_spinner=False)
def load_unified_data(url):
    try:
        # Tải dữ liệu và xóa bỏ các khoảng trắng thừa ở đầu/cuối tên cột
        df = pd.read_csv(url, dtype=str, on_bad_lines='skip', low_memory=False)
        df.columns = [str(c).strip() for c in df.columns]
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
        st.warning("🔄 Đang kiểm tra cấu trúc dữ liệu...")
        return

    # --- 2. XỬ LÝ DỮ LIỆU BẰNG INDEX (CHỐNG LỖI TÊN CỘT) ---
    try:
        clean_f = []
        # Duyệt dữ liệu từ dòng 1 (bỏ header)
        for _, row in df_raw.iloc[1:].iterrows():
            # Sử dụng .iloc[index] để lấy dữ liệu thay vì tên cột
            ma = str(row.iloc[1]).strip() # Cột B
            if not ma or "MÃ" in ma.upper() or len(ma) < 2: continue
            
            ngay = pd.to_datetime(row.iloc[6], dayfirst=True, errors='coerce') # Cột G
            if pd.notnull(ngay):
                # Ép kiểu số an toàn cho chi phí
                cp_dk = pd.to_numeric(str(row.iloc[7]).replace(',', ''), errors='coerce') or 0 # Cột H
                cp_tt = pd.to_numeric(str(row.iloc[8]).replace(',', ''), errors='coerce') or 0 # Cột I
                
                clean_f.append({
                    "NGÀY": ngay, "NĂM": ngay.year, "THÁNG": ngay.month,
                    "MÃ_MÁY": ma, 
                    "LINH_KIỆN": str(row.iloc[3]).strip(), # Cột D
                    "VÙNG": str(row.iloc[5]).strip(),      # Cột F
                    "CP_DU_KIEN": cp_dk,
                    "CP_THUC_TE": cp_tt,
                    "CHENH_LECH": cp_tt - cp_dk
                })
        df_f = pd.DataFrame(clean_f)

        # Logic Kho Vận (Sử dụng index để phân loại)
        clean_w = []
        for _, row in df_raw.iloc[1:].iterrows():
            ma = str(row.iloc[1]).strip()
            if not ma or "MÃ" in ma.upper(): continue
            
            kttt = str(row.iloc[6]).upper()  # Kiểm tra
            sbn = str(row.iloc[9]).upper()   # Sửa ngoài
            gl = str(row.iloc[13]).upper().strip() # Giao lại
            
            if gl == "R": stt = "🟢 ĐÃ TRẢ (R)"
            elif any(x in (kttt + sbn) for x in ["THANH LÝ", "HỎNG"]): stt = "🔴 THANH LÝ"
            elif "OK" in (kttt + sbn): stt = "🔵 KHO NHẬN (ĐỢI R)"
            else: stt = "🟡 ĐANG XỬ LÝ"
            
            clean_w.append({"VÙNG": row.iloc[5], "MÃ_MÁY": ma, "TRẠNG_THÁI": stt})
        df_w = pd.DataFrame(clean_w)

    except Exception as e:
        st.error(f"❌ Lỗi xử lý cột: {e}. Vui lòng kiểm tra lại thứ tự cột trên Sheets.")
        return

    # --- 3. HIỂN THỊ (GIỮ NGUYÊN NỘI DUNG SẾP ĐÃ LÀM) ---
    st.success("✅ Hệ thống đã sẵn sàng!")
    
    t_names = ["📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🤖 AI", "📁 DỮ LIỆU", "🩺 SỨC KHỎE", "🔮 DỰ BÁO", "📦 KHO LOGISTICS"]
    tabs = st.tabs(t_names)

    with tabs[0]: # XU HƯỚNG
        if not df_f.empty:
            c1, c2 = st.columns(2)
            c1.plotly_chart(px.bar(df_f.groupby('THÁNG').size().reset_index(), x='THÁNG', y=0, title="Số ca hỏng theo tháng"), use_container_width=True)
            c2.plotly_chart(px.pie(df_f, names='VÙNG', title="Phân bổ vùng miền"), use_container_width=True)

    with tabs[1]: # TÀI CHÍNH
        if not df_f.empty:
            chart_data = df_f.groupby('LINH_KIỆN')[['CP_DU_KIEN', 'CP_THUC_TE']].sum().reset_index()
            st.plotly_chart(px.bar(chart_data, x='LINH_KIỆN', y=['CP_DU_KIEN', 'CP_THUC_TE'], barmode='group'), use_container_width=True)

    with tabs[2]: # AI
        # Sửa lỗi KeyError tại đây bằng cách gọi trực tiếp từ DataFrame đã làm sạch
        st.info(f"Tổng hợp: {len(df_f)} ca sửa chữa. Tổng chi: {df_f['CP_THUC_TE'].sum():,.0f} VNĐ.")

    with tabs[3]: st.dataframe(df_f, use_container_width=True)

    with tabs[6]: # KHO LOGISTICS
        st.subheader("📦 Quản Trị Kho Vận")
        if not df_w.empty:
            st.table(df_w.groupby(['VÙNG', 'TRẠNG_THÁI']).size().unstack
