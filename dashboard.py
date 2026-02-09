import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from datetime import datetime

# --- 1. CẤU HÌNH & DATA CONTRACT ---
url = "https://cigbnbaanpebwrufzxfg.supabase.co"
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# Schema chuẩn theo yêu cầu Enterprise của sếp
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

@st.cache_data(ttl=60)
def load_repair_data_final():
    try:
        res = supabase.table("repair_cases").select("*").execute()
        if not res.data: return pd.DataFrame()
        df = pd.DataFrame(res.data)
        
        # Tiền xử lý để lên Dashboard
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)
        df['date_dt'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        df = df.dropna(subset=['date_dt'])
        df['NĂM'] = df['date_dt'].dt.year.astype(int)
        
        day_map = {'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
                   'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ Nhật'}
        df['THỨ'] = df['date_dt'].dt.day_name().map(day_map)
        
        encoding_fix = {"Miá» n Trung": "Miền Trung", "Miá» n Báº¯c": "Miền Bắc", "Miá» n Nam": "Miền Nam"}
        df['branch'] = df['branch'].replace(encoding_fix).fillna("Chưa xác định")
        return df
    except Exception as e:
        st.error(f"Lỗi Load Data: {e}")
        return pd.DataFrame()

def log_import_audit(source, rows, user="Admin"):
    """Ghi lại vết dầu loang khi có thay đổi dữ liệu"""
    try:
        supabase.table("audit_logs").insert({
            "action": f"IMPORT_{source.upper()}",
            "detail": f"Nạp {rows} dòng dữ liệu vào hệ thống",
            "created_at": datetime.now().isoformat()
        }).execute()
    except:
        pass

# --- 3. GIAO DIỆN CHÍNH ---

def main():
    st.set_page_config(page_title="4ORANGES PRO OPS", layout="wide")
    
    tab_dash, tab_admin = st.tabs(["📊 BÁO CÁO VẬN HÀNH", "📥 NHẬP DỮ LIỆU & UPLOAD"])

    # --- TAB 1: DASHBOARD ---
    with tab_dash:
        st.title("🎨 4ORANGES - DASHBOARD")
        df = load_repair_data_final()
        
        if df.empty:
            st.warning("⚠️ Hệ thống chưa có dữ liệu.")
        else:
            # --- PHẦN LỌC DỮ LIỆU ĐÃ TỐI ƯU ---
            with st.sidebar:
                st.header("⚙️ BỘ LỌC HỆ THỐNG")
                
                # 1. Lọc theo Năm (Lấy từ cột date_dt đã chuẩn hóa)
                list_years = sorted(df['NĂM'].unique().tolist(), reverse=True)
                sel_year = st.selectbox("📅 Chọn Năm báo cáo", ["Tất cả"] + list_years)
                
                # 2. Lọc theo Chi nhánh
                list_branches = sorted(df['branch'].unique().tolist())
                sel_branch = st.selectbox("🏢 Chọn Chi nhánh", ["Tất cả"] + list_branches)
                
                # 3. Lọc theo Tình trạng (Mới bổ sung cho chuẩn Enterprise)
                st.divider()
                st.caption("Lọc nhanh tình trạng máy:")
                only_unrepairable = st.checkbox("Chỉ xem máy không thể sửa")

            # --- ÁP DỤNG LOGIC LỌC (FILTERING) ---
            df_view = df.copy()
            
            if sel_year != "Tất cả":
                df_view = df_view[df_view['NĂM'] == sel_year]
                
            if sel_branch != "Tất cả":
                df_view = df_view[df_view['branch'] == sel_branch]
                
            if only_unrepairable:
                df_view = df_view[df_view['is_unrepairable'] == True]

            # --- HIỂN THỊ KPI & BIỂU ĐỒ ---
            if df_view.empty:
                st.info("ℹ️ Không tìm thấy dữ liệu phù hợp với bộ lọc hiện tại.")
            else:
                # (Tiếp tục các phần Metric và Chart như cũ...)
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("💰 TỔNG CHI PHÍ", f"{df_view['CHI_PHÍ'].sum():,.0f} đ")
                c2.metric("📋 TỔNG SỰ VỤ", f"{len(df_view)} ca")
                c3.metric("🚫 KHÔNG THỂ SỬA", f"{int(df_view['is_unrepairable'].sum())}")
                c4.metric("🏢 CHI NHÁNH", f"{df_view['branch'].nunique()}")
                
                # Phần Chart sếp giữ nguyên hoặc dùng bản fix THỨ_NAME ở trên nhé

    # --- TAB 2: QUẢN TRỊ (UNIFIED PIPELINE) ---
    with tab_admin:
        st.subheader("📥 NHẬP DỮ LIỆU HỆ THỐNG")
        
        mode = st.radio("Chọn phương thức nhập", ["📂 Upload CSV", "✍️ Nhập thủ công"], horizontal=True)
        df_input = None

        # NGUỒN 1: CSV
        if mode == "📂 Upload CSV":
            uploaded_file = st.file_uploader("Chọn file CSV", type=["csv"])
            if uploaded_file:
                df_input = pd.read_csv(uploaded_file)
                st.info(f"Đã nhận file {uploaded_file.name} với {len(df_input)} dòng.")

        # NGUỒN 2: NHẬP TAY
        else:
            with st.form("manual_input_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                c_date = col1.date_input("📅 Ngày xác nhận")
                branch = col2.selectbox("🏢 Chi nhánh", ["Miền Bắc", "Miền Trung", "Miền Nam"])
                m_id = col1.text_input("🛠️ Mã số máy")
                cust = col2.text_input("👤 Tên khách hàng")
                reason = st.text_area("❗ Lý do")
                comp = col1.number_input("💰 Chi phí thực tế", min_value=0.0)
                ex_cost = col2.number_input("📊 Chi phí dự kiến", min_value=0.0)
                chk = col1.text_input("🧑‍💼 Người kiểm tra")
                note = st.text_area("📝 Ghi chú")
                
                if st.form_submit_button("➕ Thêm vào Pipeline"):
                    df_input = pd.DataFrame([{
                        'confirmed_date': str(c_date),
                        'branch': branch,
                        'machine_id': m_id,
                        'customer_name': cust,
                        'issue_reason': reason,
                        'compensation': comp,
                        'expected_cost': ex_cost,
                        'checker': chk,
                        'note': note
                    }])

        # --- BƯỚC XỬ LÝ CHUNG (THE PIPELINE) ---
        if df_input is not None:
            st.divider()
            st.subheader("🔍 VALIDATE & PREVIEW")
            
            # 1. Validate Schema
            missing = set(BASE_COLUMNS.keys()) - set(df_input.columns)
            if missing:
                st.error(f"❌ Sai cấu trúc! Thiếu cột: {', '.join(missing)}")
            else:
                # 2. Preview
                st.success("✅ Dữ liệu đúng cấu trúc Schema.")
                st.dataframe(df_input[list(BASE_COLUMNS.keys())], use_container_width=True)
                
                # 3. Commit
                if st.button("🚀 XÁC NHẬN GHI VÀO DATABASE", type="primary"):
                    with st.spinner("Đang lưu trữ..."):
                        # Thực hiện ghi DB (Upsert theo id nếu có, hoặc machine_id)
                        res = supabase.table("repair_cases").upsert(df_input.to_dict(orient='records')).execute()
                        
                        if res.data:
                            st.balloons()
                            st.success(f"Đã lưu thành công {len(res.data)} dòng.")
                            log_import_audit(mode, len(res.data))
                            st.cache_data.clear() # Làm mới dashboard
                        else:
                            st.error("Lỗi ghi Database.")

if __name__ == "__main__":
    main()
