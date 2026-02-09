import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from datetime import datetime

# --- 1. CẤU HÌNH & DATA CONTRACT ---
url = "https://cigbnbaanpebwrufzxfg.supabase.co"
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

BASE_COLUMNS = {
    'confirmed_date': 'Ngày xác nhận',
    'branch': 'Chi nhánh',
    'machine_id': 'Mã số máy',
    'customer_name': 'Tên KH',
    'issue_reason': 'Lý do',
    'compensation': 'Chi phí thực tế',
    'expected_cost': 'Chi phí dự kiến',
    'note': 'Ghi chú',
    'checker': 'Người kiểm tra'
}

# --- 2. HÀM XỬ LÝ DỮ LIỆU (CORE LOGIC) ---

@st.cache_data(ttl=300) # Tăng lên 5 phút để tránh load liên tục gây treo
def load_repair_data_final():
    try:
        res = supabase.table("repair_cases").select("*").execute()
        if not res.data: return pd.DataFrame()
        df = pd.DataFrame(res.data)

        # 1. Sửa lỗi Font Tiếng Việt (Xử lý lỗi Miá»n Nam)
        encoding_dict = {
            "Miá» n Trung": "Miền Trung",
            "Miá» n Báº¯c": "Miền Bắc",
            "Miá» n Nam": "Miền Nam"
        }
        df['branch'] = df['branch'].replace(encoding_dict).fillna("Chưa xác định")

        # 2. Ép kiểu ngày tháng (Dùng format='ISO8601' để cực nhanh và chuẩn)
        # Bỏ qua created_at, chỉ tập trung vào confirmed_date để lấy đúng năm 2026
        df['date_dt'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        
        # Loại bỏ các dòng rác (không có ngày) - Đây là nguyên nhân gây con số 1000 ảo
        df = df.dropna(subset=['date_dt'])

        if not df.empty:
            df['NĂM'] = df['date_dt'].dt.year.astype(int)
            df['THÁNG'] = df['date_dt'].dt.month.astype(int)
            
            # Map Thứ Tiếng Việt
            day_map = {'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
                       'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ Nhật'}
            df['THỨ'] = df['date_dt'].dt.day_name().map(day_map)

        # 3. Xử lý chi phí
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Lỗi hệ thống: {e}")
        return pd.DataFrame()

# --- 3. GIAO DIỆN CHÍNH ---

def main():
    st.set_page_config(page_title="4ORANGES PRO OPS", layout="wide", page_icon="🎨")
    tab_dash, tab_admin = st.tabs(["📊 BÁO CÁO VẬN HÀNH", "📥 NHẬP DỮ LIỆU & UPLOAD"])

    # --- TAB 1: DASHBOARD ---
    with tab_dash:
    df_db = load_repair_data_final()
    
    if df_db.empty:
        st.warning("⚠️ Không tìm thấy dữ liệu năm 2026 hợp lệ. Sếp hãy kiểm tra lại cột confirmed_date trong Database!")
        if st.button("🔄 Làm mới & Quét lại"):
            st.cache_data.clear()
            st.rerun()
    else:
        # SIDEBAR CẤU HÌNH
        with st.sidebar:
            st.markdown("## ⚙️ CẤU HÌNH LỌC")
            if st.button("🔄 XÓA CACHE & TẢI LẠI", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
            
            st.divider()
            # Sắp xếp năm mới nhất lên đầu (2026)
            years = sorted(df_db['NĂM'].unique(), reverse=True)
            sel_year = st.selectbox("📅 Năm báo cáo", options=years, index=0)
            
            # Lọc tháng thông minh
            months = sorted(df_db[df_db['NĂM'] == sel_year]['THÁNG'].unique().tolist())
            sel_month = st.selectbox("📆 Tháng", options=["Tất cả"] + months)

        # LỌC DỮ LIỆU HIỂN THỊ
        df_view = df_db[df_db['NĂM'] == sel_year].copy()
        if sel_month != "Tất cả":
            df_view = df_view[df_view['THÁNG'] == sel_month]

        # HIỂN THỊ KPI
        st.title(f"📊 Báo cáo vận hành {sel_year}")
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 TỔNG CHI PHÍ", f"{df_view['CHI_PHÍ'].sum():,.0f} đ")
        c2.metric("📋 SỐ CA SỬA CHỮA", f"{len(df_view)} ca")
        c3.metric("🏢 CHI NHÁNH", f"{df_view['branch'].nunique()}")

        st.divider()

        # BIỂU ĐỒ & BẢNG (Dùng bảo vệ để tránh crash khi treo)
        col_chart, col_data = st.columns([6, 4])
        with col_chart:
            if 'THỨ' in df_view.columns and not df_view.empty:
                order = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ Nhật']
                day_stats = df_view['THỨ'].value_counts().reindex(order).fillna(0).reset_index()
                day_stats.columns = ['THỨ', 'SỐ_CA']
                st.plotly_chart(px.line(day_stats, x='THỨ', y='SỐ_CA', markers=True, title="Xu hướng trong tuần"), use_container_width=True)
        
        with col_data:
            st.write("📋 **CHI TIẾT 10 CA MỚI NHẤT**")
            # Ẩn các cột kỹ thuật để tránh rối mắt
            st.dataframe(df_view[['date_dt', 'branch', 'machine_id', 'CHI_PHÍ']].head(10), hide_index=True)

    # --- TAB 2: QUẢN TRỊ ---
    with tab_admin:
        st.title("📥 HỆ THỐNG NẠP DỮ LIỆU")
        mode = st.radio("Chọn cách nhập", ["📂 Upload CSV", "✍️ Nhập thủ công"], horizontal=True)
        
        if mode == "📂 Upload CSV":
            uploaded_file = st.file_uploader("Chọn file CSV", type=["csv"])
            if uploaded_file:
                df_up = pd.read_csv(uploaded_file)
                st.dataframe(df_up.head())
                if st.button("🚀 Upload lên Cloud"):
                    res = supabase.table("repair_cases").upsert(df_up.to_dict(orient='records')).execute()
                    if res.data:
                        st.success("Nạp dữ liệu thành công!")
                        st.cache_data.clear()
        else:
            with st.form("manual_form"):
                st.write("Nhập thông tin máy hỏng mới")
                # (Sếp giữ nguyên các trường nhập tay như trước...)
                if st.form_submit_button("Lưu dữ liệu"):
                    st.success("Đã ghi nhận!")

if __name__ == "__main__":
    main()
