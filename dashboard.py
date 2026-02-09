import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from datetime import datetime

# --- 1. CẤU HÌNH & KẾT NỐI ---
url = "https://cigbnbaanpebwrufzxfg.supabase.co"
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# ĐỊNH NGHĨA HỢP ĐỒNG DỮ LIỆU (Data Contract)
REQUIRED_COLUMNS = ['id', 'machine_id', 'branch', 'confirmed_date', 'compensation', 'issue_reason']

# --- 2. CÁC HÀM XỬ LÝ LOGIC ---

@st.cache_data(ttl=60)
def load_repair_data_final():
    try:
        res = supabase.table("repair_cases").select("*").execute()
        if not res.data: return pd.DataFrame()
        df = pd.DataFrame(res.data)
        
        # CHUẨN HÓA NGAY KHI LOAD
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

def validate_csv(df_upload):
    """Kiểm tra cấu trúc file theo Giai đoạn 1"""
    missing = set(REQUIRED_COLUMNS) - set(df_upload.columns)
    if missing:
        return False, f"❌ Thiếu cột bắt buộc: {', '.join(missing)}"
    return True, "✅ Cấu trúc file hợp lệ!"

def log_audit(action, detail):
    """Lưu Audit Log (Giai đoạn 2)"""
    try:
        log_data = {
            "action": action,
            "detail": detail,
            "created_at": datetime.now().isoformat()
        }
        # Sếp cần tạo bảng 'audit_logs' trên Supabase để dùng hàm này
        supabase.table("audit_logs").insert(log_data).execute()
    except:
        pass # Tránh làm treo app nếu bảng log chưa tạo

# --- 3. GIAO DIỆN CHÍNH ---

def main():
    st.set_page_config(page_title="4ORANGES PRO OPS", layout="wide")
    
    # TÁCH TAB THEO ROADMAP
    tab_dash, tab_admin = st.tabs(["📊 BÁO CÁO VẬN HÀNH", "⚙️ QUẢN TRỊ DỮ LIỆU"])

    # --- TAB 1: DASHBOARD (Dữ liệu sếp đã code) ---
    # --- TAB 1: DASHBOARD ---
    with tab_dash:
        st.title("🎨 4ORANGES - DASHBOARD")
        df = load_repair_data_final()
        
        if df.empty:
            st.warning("⚠️ Chưa có dữ liệu. Hãy sang tab Quản trị để upload.")
        else:
            with st.sidebar:
                years = sorted(df['NĂM'].unique(), reverse=True)
                sel_year = st.selectbox("Chọn Năm", years, key="year_filter")
                branches = ["Tất cả"] + sorted(df['branch'].unique().tolist())
                sel_branch = st.selectbox("Chọn Chi Nhánh", branches)
            
            df_view = df[df['NĂM'] == sel_year]
            if sel_branch != "Tất cả":
                df_view = df_view[df_view['branch'] == sel_branch]
            
            # KPI Metrics
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💰 TỔNG BỒI THƯỜNG", f"{df_view['CHI_PHÍ'].sum():,.0f} đ")
            c2.metric("📋 TỔNG SỰ VỤ", f"{len(df_view)} ca")
            c3.metric("🚫 KHÔNG THỂ SỬA", f"{int(df_view['is_unrepairable'].sum())}")
            c4.metric("🏢 CHI NHÁNH", f"{df_view['branch'].nunique()}")
            
            # --- FIX LỖI BIỂU ĐỒ TẠI ĐÂY ---
            col1, col2 = st.columns([6, 4])
            with col1:
                st.write("📈 **XU HƯỚNG THEO THỨ**")
                order = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ Nhật']
                # Ép tên cột rõ ràng để tránh lỗi 'index'
                day_stats = df_view['THỨ'].value_counts().reindex(order).reset_index()
                day_stats.columns = ['THỨ_NAME', 'SỐ_CA'] 
                
                fig_line = px.line(day_stats, x='THỨ_NAME', y='SỐ_CA', 
                                  markers=True, color_discrete_sequence=['#FF4500'])
                st.plotly_chart(fig_line, use_container_width=True)
            
            with col2:
                st.write("🧩 **TỶ TRỌNG LÝ DO HỎNG**")
                reason_df = df_view['issue_reason'].value_counts().reset_index().head(10)
                reason_df.columns = ['LÝ_DO', 'SỐ_LƯỢNG']
                st.plotly_chart(px.pie(reason_df, names='LÝ_DO', values='SỐ_LƯỢNG', hole=0.4), use_container_width=True)

            # Data Table
            st.subheader("📋 NHẬT KÝ CHI TIẾT")
            df_display = df_view.copy()
            df_display['NGÀY'] = df_display['date_dt'].dt.strftime('%d/%m/%Y')
            cols_to_show = ['NGÀY', 'THỨ', 'branch', 'customer_name', 'issue_reason', 'CHI_PHÍ']
            st.dataframe(df_display.sort_values('date_dt', ascending=False)[cols_to_show], use_container_width=True, hide_index=True)

    # --- TAB 2: QUẢN TRỊ (Giai đoạn 1 & 2) ---
    with tab_admin:
        st.title("📤 HỆ THỐNG NẠP DỮ LIỆU CHUẨN")
        
        st.info("💡 Hướng dẫn: Tải file CSV có đầy đủ các cột: " + ", ".join(REQUIRED_COLUMNS))
        
        uploaded_file = st.file_uploader("Chọn file CSV từ máy tính", type="csv")
        
        if uploaded_file:
            df_up = pd.read_csv(uploaded_file)
            
            # BƯỚC 1: VALIDATE SCHEMA
            is_valid, msg = validate_csv(df_up)
            
            if not is_valid:
                st.error(msg)
            else:
                st.success(msg)
                
                # BƯỚC 2: PREVIEW & REVIEW
                st.write("🔍 **XEM TRƯỚC DỮ LIỆU (PREVIEW):**")
                st.dataframe(df_up.head(10), use_container_width=True)
                
                # BƯỚC 3: COMMIT (ĐẨY LÊN DB)
                if st.button("🚀 XÁC NHẬN COMMIT LÊN HỆ THỐNG", type="primary"):
                    with st.spinner("Đang đẩy dữ liệu lên Cloud..."):
                        # Chuyển đổi dữ liệu cho khớp DB
                        data_to_insert = df_up.to_dict(orient='records')
                        
                        # Thực hiện Upsert (Thêm mới hoặc cập nhật nếu trùng ID)
                        res = supabase.table("repair_cases").upsert(data_to_insert).execute()
                        
                        if res.data:
                            st.balloons()
                            st.success(f"✅ Thành công! Đã nạp/cập nhật {len(res.data)} dòng.")
                            log_audit("UPLOAD_CSV", f"User uploaded {len(res.data)} records from {uploaded_file.name}")
                            st.cache_data.clear() # Xóa cache để dashboard cập nhật mới ngay
                        else:
                            st.error("❌ Lỗi khi đẩy dữ liệu lên database.")

        # PHẦN AUDIT LOG (Xem lịch sử)
        st.divider()
        st.subheader("🧾 Nhật ký hệ thống (Audit Log)")
        # Lấy dữ liệu từ bảng audit_logs nếu sếp đã tạo
        st.caption("Hiển thị 10 thao tác gần nhất...")
        # res_log = supabase.table("audit_logs").select("*").order("created_at", desc=True).limit(10).execute()
        # st.table(res_log.data)

if __name__ == "__main__":
    main()
