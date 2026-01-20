import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="Hệ Thống Quản Trị V15.8", layout="wide")

SHARED_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?output=csv"

@st.cache_data(ttl=300, show_spinner=False)
def load_unified_data(url):
    try:
        # Tải dữ liệu thô
        df = pd.read_csv(url, dtype=str, on_bad_lines='skip', low_memory=False).fillna("0")
        return df
    except:
        return pd.DataFrame()

def main():
    with st.sidebar:
        st.title("EXECUTIVE HUB")
        if st.button('🔄 ĐỒNG BỘ HỆ THỐNG', type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    df_raw = load_unified_data(SHARED_URL)
    
    if df_raw.empty:
        st.warning("🔄 Đang kết nối dữ liệu...")
        return

    # --- 2. XỬ LÝ DỮ LIỆU AN TOÀN (TRÁNH KEYERROR) ---
    try:
        # Tự động xác định vị trí cột để gán lại tên chuẩn (Fix lỗi KeyError)
        # Giả định cấu trúc: Cột 1: STT, 2: Mã Máy, 3: Khách hàng, 4: Linh kiện...
        df_proc = df_raw.copy()
        
        # Đặt tên lại cho các cột quan trọng dựa theo vị trí (index) để đảm bảo logic không sai
        new_cols = {
            df_proc.columns[1]: 'MÃ_MÁY',
            df_proc.columns[2]: 'KHÁCH_HÀNG',
            df_proc.columns[3]: 'LINH_KIỆN',
            df_proc.columns[5]: 'VÙNG',
            df_proc.columns[6]: 'NGÀY',
            df_proc.columns[7]: 'CP_DU_KIEN',
            df_proc.columns[8]: 'CP_THUC_TE'
        }
        df_proc = df_proc.rename(columns=new_cols)

        # Chuyển đổi dữ liệu số và ngày tháng
        clean_f = []
        for _, row in df_proc.iloc[1:].iterrows():
            ma = str(row['MÃ_MÁY']).strip()
            if not ma or "MÃ" in ma.upper() or len(ma) < 2: continue
            
            ngay = pd.to_datetime(row['NGÀY'], dayfirst=True, errors='coerce')
            if pd.notnull(ngay):
                cp_dk = pd.to_numeric(str(row['CP_DU_KIEN']).replace(',', ''), errors='coerce') or 0
                cp_tt = pd.to_numeric(str(row['CP_THUC_TE']).replace(',', ''), errors='coerce') or 0
                clean_f.append({
                    "NGÀY": ngay, "NĂM": ngay.year, "THÁNG": ngay.month,
                    "MÃ_MÁY": ma, "LINH_KIỆN": str(row['LIN_KIỆN']).strip(),
                    "VÙNG": str(row['VÙNG']).strip(), "CP_DU_KIEN": cp_dk,
                    "CP_THUC_TE": cp_tt, "CHENH_LECH": cp_tt - cp_dk
                })
        df_f = pd.DataFrame(clean_f)
        
        # Dữ liệu Kho vận (Tận dụng df_proc đã đổi tên)
        df_w = df_proc.copy()
        # Thêm logic phân loại trạng thái (Sửa lỗi màu đỏ)
        def classify(r):
            kttt = str(r.iloc[6]).upper()
            sbn = str(r.iloc[9]).upper()
            gl = str(r.iloc[13]).upper().strip()
            if gl == "R": return "🟢 ĐÃ TRẢ (R)"
            if any(x in (kttt + sbn) for x in ["THANH LÝ", "HỎNG"]): return "🔴 THANH LÝ"
            if "OK" in (kttt + sbn): return "🔵 KHO NHẬN (ĐỢI R)"
            return "🟡 ĐANG XỬ LÝ"
        
        df_w['TRẠNG_THÁI'] = df_w.apply(classify, axis=1)

    except Exception as e:
        st.error(f"❌ Lỗi cấu trúc Sheet: {e}")
        return

    # --- 3. HIỂN THỊ (GIỮ NGUYÊN GIAO DIỆN) ---
    st.success("✅ Hệ thống đã sẵn sàng!")
    
    tabs = st.tabs(["📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🤖 AI", "📁 DỮ LIỆU", "🩺 SỨC KHỎE", "🔮 DỰ BÁO", "📦 KHO LOGISTICS"])

    with tabs[0]: # XU HƯỚNG
        if not df_f.empty:
            c1, c2 = st.columns(2)
            c1.plotly_chart(px.bar(df_f.groupby('THÁNG').size().reset_index(), x='THÁNG', y=0, title="Số ca hỏng theo tháng"), use_container_width=True)
            c2.plotly_chart(px.pie(df_f, names='VÙNG', hole=0.5, title="Phân bổ vùng"), use_container_width=True)

    with tabs[1]: # TÀI CHÍNH
        # Đã bọc trong check empty để tránh KeyError lần nữa
        if not df_f.empty:
            cost_df = df_f.groupby('LIN_KIỆN')[['CP_DU_KIEN', 'CP_THUC_TE']].sum().reset_index()
            st.plotly_chart(px.bar(cost_df, x='LIN_KIỆN', y=['CP_DU_KIEN', 'CP_THUC_TE'], barmode='group', title="Đối soát tài chính"), use_container_width=True)

    with tabs[2]: # AI
        st.info(f"Tổng hợp: {len(df_f)} ca sửa chữa. Tổng chi: {df_f['CP_THUC_TE'].sum():,.0f} VNĐ.")

    with tabs[3]: st.dataframe(df_f, use_container_width=True)

    with tabs[6]: # KHO LOGISTICS
        st.subheader("📦 Quản Trị Kho Vận")
        st.table(df_w.groupby(['VÙNG', 'TRẠNG_THÁI']).size().unstack(fill_value=0))

if __name__ == "__main__":
    main()
