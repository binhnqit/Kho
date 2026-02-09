import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from datetime import datetime

# --- 1. CẤU HÌNH & DATA CONTRACT ---
url = "https://cigbnbaanpebwrufzxfg.supabase.co"
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# Schema chuẩn - Mọi cột dữ liệu phải tuân thủ danh sách này
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

@st.cache_data(ttl=10) # Giảm TTL xuống 10 giây để thấy dữ liệu 2026 ngay lập tức
def load_repair_data_final():
    try:
        # Truy vấn lấy toàn bộ, sắp xếp theo ngày mới nhất
        res = supabase.table("repair_cases").select("*").order("confirmed_date", desc=True).execute()
        
        if not res.data: 
            return pd.DataFrame()
            
        df = pd.DataFrame(res.data)

        # 🛠️ XỬ LÝ NGHẼN ĐỊNH DẠNG:
        # Chuyển đổi compensation: Nếu là 'false' (string) hoặc False (bool) -> 0
        df['compensation'] = df['compensation'].apply(lambda x: 0 if str(x).lower() == 'false' else x)
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)

        # Chuyển đổi Ngày tháng: Ép kiểu datetime chuẩn ISO
        df['date_dt'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        
        # Nếu dòng nào không có confirmed_date, lấy created_at làm fallback (dự phòng)
        df['date_dt'] = df['date_dt'].fillna(pd.to_datetime(df['created_at'], errors='coerce'))
        
        # Loại bỏ dòng không thể xác định ngày (tránh lỗi bộ lọc)
        df = df.dropna(subset=['date_dt'])

        # Tạo cột thời gian
        df['NĂM'] = df['date_dt'].dt.year.astype(int)
        df['THÁNG'] = df['date_dt'].dt.month.astype(int)
        
        # Fix Encoding cho Chi nhánh (Dựa trên dữ liệu thực tế của sếp)
        branch_map = {
            "Miá» n Trung": "Miền Trung",
            "Miá» n Báº¯c": "Miền Bắc",
            "Miá» n Nam": "Miền Nam"
        }
        df['branch'] = df['branch'].replace(branch_map)

        return df
    except Exception as e:
        st.error(f"🚨 Lỗi truy vấn Database: {e}")
        return pd.DataFrame()

def log_import_audit(source, rows):
    """Ghi lại lịch sử thao tác dữ liệu"""
    try:
        supabase.table("audit_logs").insert({
            "action": f"IMPORT_{source.upper()}",
            "detail": f"Nạp {rows} dòng dữ liệu",
            "created_at": datetime.now().isoformat()
        }).execute()
    except:
        pass # Tránh làm gián đoạn UX nếu bảng log gặp lỗi

# --- 3. GIAO DIỆN CHÍNH ---

def main():
    st.set_page_config(page_title="4ORANGES PRO OPS", layout="wide", page_icon="🎨")
    
    # Khởi tạo Tabs
    tab_dash, tab_admin = st.tabs(["📊 BÁO CÁO VẬN HÀNH", "📥 NHẬP DỮ LIỆU & UPLOAD"])

    # --- TAB 1: DASHBOARD ---
    with tab_dash:
        df_db = load_repair_data_final()
        
        if df_db.empty:
            st.warning("⚠️ Database chưa có dữ liệu. Vui lòng sang tab Quản trị để nạp dữ liệu.")
        else:
            # A. SIDEBAR - BỘ LỌC THÔNG MINH
            with st.sidebar:
                st.markdown("## ⚙️ CẤU HÌNH LỌC")
                if st.sidebar.button("🔄 Làm mới toàn bộ dữ liệu"):
                    st.cache_data.clear()
                st.rerun()
                years = sorted(df_db['NĂM'].unique(), reverse=True)
                
                with st.form("filter_form"):
                    sel_year = st.selectbox("📅 Năm báo cáo", options=years, index=0)
                    
                    # Lọc tháng dựa trên năm đã chọn
                    months_in_year = sorted(df_db[df_db['NĂM'] == sel_year]['THÁNG'].unique().tolist())
                    month_map = {m: f"Tháng {m:02d}" for m in months_in_year}
                    sel_month_val = st.selectbox("📆 Tháng", options=["Tất cả"] + list(month_map.keys()), 
                                                 format_func=lambda x: "Tất cả" if x == "Tất cả" else month_map[x])
                    
                    apply_filter = st.form_submit_button("🔍 Áp dụng bộ lọc", use_container_width=True)

            # B. LOGIC LỌC DỮ LIỆU
            if apply_filter:
                df_view = df_db[df_db['NĂM'] == sel_year].copy()
                if sel_month_val != "Tất cả":
                    df_view = df_view[df_view['THÁNG'] == sel_month_val]
                current_month_display = month_map.get(sel_month_val, "Cả năm") if sel_month_val != "Tất cả" else "Cả năm"
            else:
                sel_year = years[0]
                current_month_display = "Cả năm"
                df_view = df_db[df_db['NĂM'] == sel_year].copy()

            # C. HIỂN THỊ KẾT QUẢ
            st.title(f"📊 Báo cáo {current_month_display} / {sel_year}")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💰 TỔNG CHI PHÍ", f"{df_view['CHI_PHÍ'].sum():,.0f} đ")
            c2.metric("📋 TỔNG SỰ VỤ", f"{len(df_view)} ca")
            c3.metric("🚫 KHÔNG THỂ SỬA", f"{int(df_view['is_unrepairable'].sum() if 'is_unrepairable' in df_view else 0)}")
            c4.metric("🏢 CHI NHÁNH", f"{df_view['branch'].nunique()}")
            
            st.divider()
            
            # Biểu đồ xu hướng đơn giản
            if not df_view.empty:
                col_chart, col_data = st.columns([6, 4])
                with col_chart:
                    st.write("📈 **XU HƯỚNG THEO THỨ**")
                    order = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ Nhật']
                    day_stats = df_view['THỨ'].value_counts().reindex(order).reset_index()
                    day_stats.columns = ['THỨ', 'SỐ_CA']
                    fig = px.line(day_stats, x='THỨ', y='SỐ_CA', markers=True, color_discrete_sequence=['#FF4500'])
                    st.plotly_chart(fig, use_container_width=True)
                
                with col_data:
                    st.write("📋 **TOP DỮ LIỆU CHI TIẾT**")
                    st.dataframe(df_view[['date_dt', 'branch', 'customer_name', 'CHI_PHÍ']].head(10), use_container_width=True)

    # --- TAB 2: QUẢN TRỊ (UNIFIED PIPELINE) ---
    with tab_admin:
        st.title("📥 HỆ THỐNG NẠP DỮ LIỆU")
        mode = st.radio("Phương thức nhập", ["📂 Upload CSV", "✍️ Nhập thủ công"], horizontal=True)
        df_input = None

        if mode == "📂 Upload CSV":
            uploaded_file = st.file_uploader("Chọn file CSV chuẩn", type=["csv"])
            if uploaded_file:
                df_input = pd.read_csv(uploaded_file)
        else:
            with st.form("manual_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                f_date = c1.date_input("Ngày xác nhận")
                f_branch = c2.selectbox("Chi nhánh", ["Miền Bắc", "Miền Trung", "Miền Nam"])
                f_mid = c1.text_input("Mã số máy")
                f_cust = c2.text_input("Tên khách hàng")
                f_reason = st.text_area("Lý do hỏng")
                f_comp = c1.number_input("Chi phí thực tế", min_value=0)
                f_exp = c2.number_input("Chi phí dự kiến", min_value=0)
                
                if st.form_submit_button("➕ Kiểm tra & Thêm"):
                    df_input = pd.DataFrame([{
                        'confirmed_date': str(f_date), 'branch': f_branch,
                        'machine_id': f_mid, 'customer_name': f_cust,
                        'issue_reason': f_reason, 'compensation': f_comp,
                        'expected_cost': f_exp
                    }])

        # PIPELINE CHUNG
        if df_input is not None:
            st.divider()
            # Kiểm tra schema
            missing = set(BASE_COLUMNS.keys()) - set(df_input.columns)
            if missing and mode == "📂 Upload CSV":
                st.error(f"❌ File thiếu cột: {', '.join(missing)}")
            else:
                st.subheader("🔍 Xem trước dữ liệu")
                st.dataframe(df_input, use_container_width=True)
                if st.button("🚀 XÁC NHẬN LƯU VÀO HỆ THỐNG", type="primary"):
                    res = supabase.table("repair_cases").upsert(df_input.to_dict(orient='records')).execute()
                    if res.data:
                        st.success(f"✅ Đã nạp thành công {len(res.data)} dòng!")
                        log_import_audit(mode, len(res.data))
                        st.cache_data.clear()

if __name__ == "__main__":
    main()
