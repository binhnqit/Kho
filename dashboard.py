import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from datetime import datetime

# --- 1. KẾT NỐI ---
url = "https://cigbnbaanpebwrufzxfg.supabase.co"
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. HÀM XỬ LÝ (TRÁI TIM CỦA APP) ---
@st.cache_data(ttl=60) # Cache 1 phút để cân bằng giữa tốc độ và dữ liệu mới
def load_repair_data_final():
    try:
        res = supabase.table("repair_cases").select("*").execute()
        if not res.data: return pd.DataFrame()
        df = pd.DataFrame(res.data)

        # A. Sửa lỗi Font (Thông suốt hiển thị)
        encoding_dict = {"Miá» n Trung": "Miền Trung", "Miá» n Báº¯c": "Miền Bắc", "Miá» n Nam": "Miền Nam"}
        df['branch'] = df['branch'].replace(encoding_dict).fillna("Khác")

        # B. Ép kiểu ngày tháng - GIẢI QUYẾT MẤT NĂM 2026
        # Thử ép kiểu linh hoạt nhất có thể
        df['date_dt'] = pd.to_datetime(df['confirmed_date'], dayfirst=True, errors='coerce')
        
        # Nếu vẫn trống, thử lấy từ created_at làm phương án dự phòng cuối cùng
        if 'created_at' in df.columns:
            df['date_dt'] = df['date_dt'].fillna(pd.to_datetime(df['created_at'], errors='coerce'))

        # Lọc bỏ rác (những dòng hoàn toàn không có ngày)
        df = df.dropna(subset=['date_dt'])

        # C. Trích xuất thời gian
        df['NĂM'] = df['date_dt'].dt.year.astype(int)
        df['THÁNG'] = df['date_dt'].dt.month.astype(int)
        day_map = {'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
                   'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ Nhật'}
        df['THỨ'] = df['date_dt'].dt.day_name().map(day_map)

        # D. Xử lý Chi Phí (Thông suốt tiền tệ)
        # Chuyển đổi 'false' hoặc NaN thành 0, ép về kiểu số
        df['compensation'] = df['compensation'].apply(lambda x: 0 if str(x).lower() == 'false' else x)
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Lỗi Load Data: {e}")
        return pd.DataFrame()

# --- 3. GIAO DIỆN ---
def main():
    st.set_page_config(page_title="4ORANGES OPS 2026", layout="wide", page_icon="🎨")
    tab_dash, tab_admin = st.tabs(["📊 BÁO CÁO VẬN HÀNH", "📥 QUẢN TRỊ"])

    with tab_dash:
        df_db = load_repair_data_final()
        
        if df_db.empty:
            st.info("Chưa có dữ liệu. Vui lòng kiểm tra lại bảng 'repair_cases' trên Supabase.")
        else:
            # SideBar
            with st.sidebar:
                st.header("⚙️ BỘ LỌC")
                if st.button("🔄 LÀM MỚI DỮ LIỆU"):
                    st.cache_data.clear()
                    st.rerun()
                
                # Sắp xếp năm mới nhất lên đầu (Để thấy 2026 ngay lập tức)
                available_years = sorted(df_db['NĂM'].unique(), reverse=True)
                sel_year = st.selectbox("Chọn năm", options=available_years, index=0)
                
                available_months = sorted(df_db[df_db['NĂM'] == sel_year]['THÁNG'].unique().tolist())
                sel_month = st.selectbox("Chọn tháng", options=["Tất cả"] + available_months)

            # Lọc dữ liệu theo lựa chọn
            df_view = df_db[df_db['NĂM'] == sel_year].copy()
            if sel_month != "Tất cả":
                df_view = df_view[df_view['THÁNG'] == sel_month]

            # Hiển thị KPI
            st.title(f"📈 Báo cáo vận hành năm {sel_year}")
            c1, c2, c3 = st.columns(3)
            c1.metric("💰 TỔNG CHI PHÍ", f"{df_view['CHI_PHÍ'].sum():,.0f} đ")
            c2.metric("🛠️ SỐ CA SỬA CHỮA", f"{len(df_view)} ca")
            c3.metric("🏢 CHI NHÁNH", f"{df_view['branch'].nunique()}")

            st.divider()

            # Biểu đồ & Chi tiết
            col1, col2 = st.columns([6, 4])
            with col1:
                st.subheader("📅 Xu hướng theo thứ")
                order = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ Nhật']
                day_stats = df_view['THỨ'].value_counts().reindex(order).fillna(0).reset_index()
                day_stats.columns = ['THỨ', 'SỐ_CA']
                fig = px.line(day_stats, x='THỨ', y='SỐ_CA', markers=True, color_discrete_sequence=['#00CC96'])
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("📋 10 ca mới nhất")
                st.dataframe(df_view[['date_dt', 'branch', 'machine_id', 'CHI_PHÍ']].head(10), hide_index=True)

    with tab_admin:
        st.header("📥 Quản lý dữ liệu")
        st.write("Sếp có thể thực hiện Import dữ liệu tại đây.")
        # ... Giữ nguyên phần tab_admin của sếp ...

if __name__ == "__main__":
    main()
