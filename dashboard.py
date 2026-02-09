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

@st.cache_data(ttl=10)
def load_repair_data_final():
    try:
        res = supabase.table("repair_cases").select("*").execute()
        if not res.data: return pd.DataFrame()
        df = pd.DataFrame(res.data)

        # 1. Sửa lỗi Font
        encoding_map = {"Miá» n Trung": "Miền Trung", "Miá» n Báº¯c": "Miền Bắc", "Miá» n Nam": "Miền Nam"}
        df['branch'] = df['branch'].replace(encoding_map)

        # 2. Xử lý ngày tháng (Chỉ lấy confirmed_date, bỏ qua created_at để tránh data ảo)
        df['date_dt'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        df = df.dropna(subset=['date_dt']) # Dòng nào confirmed_date trống sẽ bị loại bỏ khỏi Dashboard
        
        df['NĂM'] = df['date_dt'].dt.year.astype(int)
        df['THÁNG'] = df['date_dt'].dt.month.astype(int)

        # 3. Xử lý chi phí
        df['compensation'] = df['compensation'].apply(lambda x: 0 if str(x).lower() == 'false' else x)
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Lỗi: {e}")
        return pd.DataFrame()

# --- 3. GIAO DIỆN CHÍNH ---

def main():
    st.set_page_config(page_title="4ORANGES PRO OPS", layout="wide", page_icon="🎨")
    tab_dash, tab_admin = st.tabs(["📊 BÁO CÁO VẬN HÀNH", "📥 NHẬP DỮ LIỆU & UPLOAD"])

    # --- TAB 1: DASHBOARD ---
    with tab_dash:
        df_db = load_repair_data_final()
        
        if df_db.empty:
            st.warning("⚠️ Database rỗng hoặc không có dữ liệu hợp lệ.")
            if st.button("🔄 Thử quét lại dữ liệu"):
                st.cache_data.clear()
                st.rerun()
        else:
            # A. SIDEBAR - BỘ LỌC
            with st.sidebar:
                st.markdown("## ⚙️ CẤU HÌNH LỌC")
                
                # 👉 FIX LỖI LOAD LIÊN TỤC: Đưa rerun vào trong khối if
                if st.button("🔄 Làm mới toàn bộ dữ liệu", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()
                
                st.divider()
                
                years = sorted(df_db['NĂM'].unique(), reverse=True)
                with st.form("filter_form"):
                    sel_year = st.selectbox("📅 Năm báo cáo", options=years, index=0)
                    
                    # Lọc danh sách tháng có dữ liệu trong năm đó
                    months_in_year = sorted(df_db[df_db['NĂM'] == sel_year]['THÁNG'].unique().tolist())
                    month_labels = {m: f"Tháng {m:02d}" for m in months_in_year}
                    
                    sel_month_val = st.selectbox(
                        "📆 Tháng", 
                        options=["Tất cả"] + list(month_labels.keys()),
                        format_func=lambda x: "Tất cả" if x == "Tất cả" else month_labels[x]
                    )
                    apply_filter = st.form_submit_button("🔍 Áp dụng bộ lọc", use_container_width=True)

            # B. LOGIC LỌC
            if apply_filter:
                df_view = df_db[df_db['NĂM'] == sel_year].copy()
                if sel_month_val != "Tất cả":
                    df_view = df_view[df_view['THÁNG'] == sel_month_val]
                display_title = f"{month_labels.get(sel_month_val, 'Cả năm')} / {sel_year}"
            else:
                # Mặc định lấy năm mới nhất (2026)
                sel_year = years[0]
                df_view = df_db[df_db['NĂM'] == sel_year].copy()
                display_title = f"Cả năm / {sel_year}"

            # C. HIỂN THỊ
            st.title(f"📊 Báo cáo: {display_title}")
            
            # Kiểm tra xem có dữ liệu sau khi lọc không để tránh KeyError khi vẽ biểu đồ
            if not df_view.empty:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("💰 TỔNG CHI PHÍ", f"{df_view['CHI_PHÍ'].sum():,.0f} đ")
                c2.metric("📋 TỔNG SỰ VỤ", f"{len(df_view)} ca")
                c3.metric("🏢 CHI NHÁNH", f"{df_view['branch'].nunique()}")
                # Kiểm tra cột is_unrepairable nếu có trong DB
                unrepairable_count = int(df_view['is_unrepairable'].sum()) if 'is_unrepairable' in df_view.columns else 0
                c4.metric("🚫 KHÔNG THỂ SỬA", unrepairable_count)
                
                st.divider()
                
                col_chart, col_data = st.columns([6, 4])
                with col_chart:
                    st.write("📈 **XU HƯỚNG THEO THỨ**")
                    order = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ Nhật']
                    # Sử dụng .reindex an toàn hơn
                    day_stats = df_view['THỨ'].value_counts().reindex(order).fillna(0).reset_index()
                    day_stats.columns = ['THỨ', 'SỐ_CA']
                    fig = px.line(day_stats, x='THỨ', y='SỐ_CA', markers=True, color_discrete_sequence=['#FF4500'])
                    st.plotly_chart(fig, use_container_width=True)
                
                with col_data:
                    st.write("📋 **CHI TIẾT 10 CA MỚI NHẤT**")
                    st.dataframe(df_view[['date_dt', 'branch', 'machine_id', 'CHI_PHÍ']].head(10), use_container_width=True, hide_index=True)
            else:
                st.info(f"Không có dữ liệu cho {display_title}. Vui lòng kiểm tra lại ngày tháng trong Database.")

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
