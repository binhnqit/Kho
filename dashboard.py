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
@st.cache_data(ttl=60)
def load_repair_data_final():
    try:
        res = supabase.table("repair_cases").select("*").execute()
        if not res.data: 
            return pd.DataFrame()
        
        df = pd.DataFrame(res.data)

        # 1. PHÂN TÁCH HAI LOẠI THỜI GIAN
        # confirmed_dt dùng cho KPI, Xu hướng, Bộ lọc
        df['confirmed_dt'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        # created_dt dùng để sắp xếp thứ tự nhập liệu
        df['created_dt']   = pd.to_datetime(df['created_at'], errors='coerce')
        
        # Loại bỏ rác nếu không có ngày nghiệp vụ
        df = df.dropna(subset=['confirmed_dt'])

        # 2. TRÍCH XUẤT THÔNG TIN NGHIỆP VỤ (KPI + FILTER)
        df['NĂM'] = df['confirmed_dt'].dt.year.astype(int)
        df['THÁNG'] = df['confirmed_dt'].dt.month.astype(int)
        
        day_map = {'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
                   'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ Nhật'}
        df['THỨ'] = df['confirmed_dt'].dt.day_name().map(day_map)

        # 3. CHUẨN HÓA DỮ LIỆU SỐ & CHI NHÁNH
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)
        encoding_dict = {"Miá» n Trung": "Miền Trung", "Miá» n Báº¯c": "Miền Bắc", "Miá» n Nam": "Miền Nam"}
        df['branch'] = df['branch'].replace(encoding_dict)

        # 4. SẮP XẾP THEO HỆ THỐNG (Mới nhập hiện lên đầu)
        df = df.sort_values(by='created_dt', ascending=False)

        return df
    except Exception as e:
        st.error(f"Lỗi logic: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Lỗi: {e}")
        return pd.DataFrame()

# --- 3. GIAO DIỆN ---
def main():
    st.set_page_config(page_title="4ORANGES OPS 2026", layout="wide", page_icon="🎨")
    
    # 1. LOAD DỮ LIỆU CHUNG (Dùng chung cho cả 2 Tab)
    df_db = load_repair_data_final()
    
    # 2. KHỞI TẠO TABS
    tab_dash, tab_admin = st.tabs(["📊 BÁO CÁO VẬN HÀNH", "📥 QUẢN TRỊ"])

    # --- TAB 1: BÁO CÁO VẬN HÀNH ---
    with tab_dash:
        if df_db.empty:
            st.info("Chưa có dữ liệu hợp lệ. Vui lòng kiểm tra lại Database hoặc nạp dữ liệu ở Tab Quản trị.")
        else:
            # --- A. SIDEBAR (Chỉ hiện khi ở Tab Báo cáo) ---
            with st.sidebar:
                st.header("⚙️ BỘ LỌC")
                if st.button("🔄 LÀM MỚI DỮ LIỆU", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()
                st.divider()
                
                # Logic chọn Năm/Tháng
                available_years = sorted(df_db['NĂM'].unique(), reverse=True)
                sel_year = st.selectbox("📅 Chọn năm", options=available_years, key="year_filter")
                
                available_months = sorted(df_db[df_db['NĂM'] == sel_year]['THÁNG'].unique().tolist())
                sel_month = st.selectbox("📆 Chọn tháng", options=["Tất cả"] + available_months, key="month_filter")

            # --- B. LỌC DỮ LIỆU VIEW ---
            df_view = df_db[df_db['NĂM'] == sel_year].copy()
            if sel_month != "Tất cả":
                df_view = df_view[df_view['THÁNG'] == sel_month]

            # --- C. HIỂN THỊ KPI ---
            month_label = f"Tháng {sel_month}" if sel_month != "Tất cả" else "Cả năm"
            st.title(f"📈 Báo cáo vận hành {month_label} / {sel_year}")
            
            c1, c2, c3 = st.columns(3)
            # Dữ liệu CHI_PHÍ đã được ép kiểu numeric trong SQL nên sum() sẽ ra kết quả chuẩn
            c1.metric("💰 TỔNG CHI PHÍ", f"{df_view['CHI_PHÍ'].sum():,.0f} đ")
            c2.metric("🛠️ SỐ CA SỬA CHỮA", f"{len(df_view)} ca")
            top_branch = df_view['branch'].value_counts().idxmax() if not df_view.empty else "N/A"
            c3.metric("🏢 CHI NHÁNH NHIỀU CA NHẤT", top_branch)

            st.divider()

            # --- D. BIỂU ĐỒ & BẢNG ---
            col_chart, col_table = st.columns([6, 4])
            with col_chart:
                st.subheader("📅 Xu hướng sự vụ theo thứ")
                order = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ Nhật']
                day_stats = df_view['THỨ'].value_counts().reindex(order).fillna(0).reset_index()
                day_stats.columns = ['THỨ', 'SỐ_CA']
                fig = px.line(day_stats, x='THỨ', y='SỐ_CA', markers=True, color_discrete_sequence=['#00CC96'])
                fig.update_layout(height=350, margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)

            with col_table:
                st.subheader("📋 10 ca mới cập nhật")
                # Hiển thị mã máy vừa nạp (ví dụ 1366) ở ngay đây
                st.dataframe(
                    df_view.sort_values('date_dt', ascending=False).head(10)[['date_dt', 'branch', 'machine_id', 'CHI_PHÍ']],
                    use_container_width=True, hide_index=True
                )

            with st.expander("🔎 Xem toàn bộ dữ liệu chi tiết đã lọc"):
                st.dataframe(df_view.sort_values('date_dt', ascending=False), use_container_width=True)

    # --- TAB 2: QUẢN TRỊ (Phần sếp vừa yêu cầu) ---
    
    with tab_admin:
        st.title("📥 HỆ THỐNG QUẢN TRỊ DỮ LIỆU")
        
        # Chia 2 cột: Một bên nạp file, một bên nhập tay
        col_import, col_manual = st.columns([1, 1])

        # --- PHẦN 1: IMPORT FILE CSV (Dành cho nạp data lớn) ---
        with col_import:
            st.subheader("📂 Import từ File CSV")
            st.info("💡 Mẹo: File nên có cột `machine_id`, `branch`, `compensation`, `confirmed_date`...")
            uploaded_file = st.file_uploader("Chọn file CSV", type=["csv"], key="csv_upload")
            
            if uploaded_file:
                df_up = pd.read_csv(uploaded_file)
                
                # 1. Xử lý Ngày Nghiệp vụ: Ép kiểu và xóa rác
                if 'confirmed_date' in df_up.columns:
                    df_up['confirmed_date'] = pd.to_datetime(df_up['confirmed_date'], errors='coerce').dt.strftime('%Y-%m-%d')
                
                # 2. Xử lý Chi phí: Ép về Numeric (Fix lỗi Boolean 'false')
                if 'compensation' in df_up.columns:
                    df_up['compensation'] = pd.to_numeric(df_up['compensation'], errors='coerce').fillna(0).astype(float)
                
                # 3. Gắn nhãn Ngày Hệ thống: Để Dashboard biết đây là dữ liệu mới nạp
                df_up['created_at'] = datetime.now().isoformat()
                
                # 4. Đảm bảo machine_id là dạng chữ (tránh lỗi định dạng UUID)
                if 'machine_id' in df_up.columns:
                    df_up['machine_id'] = df_up['machine_id'].astype(str)
                
                st.write("👀 Xem trước dữ liệu chuẩn bị nạp:")
                st.dataframe(df_up.head(3), use_container_width=True)
                
                if st.button("🚀 Xác nhận Upload lên Cloud", use_container_width=True, type="primary"):
                    try:
                        data_to_upsert = df_up.to_dict(orient='records')
                        res = supabase.table("repair_cases").upsert(data_to_upsert).execute()
                        if res.data:
                            st.success(f"✅ Đã nạp {len(res.data)} dòng thành công!")
                            st.cache_data.clear() # Xóa cache để dashboard thấy data mới ngay
                            st.balloons()
                    except Exception as e:
                        st.error(f"❌ Lỗi nạp dữ liệu: {e}")

        # --- PHẦN 2: NHẬP TAY (Dành cho ca phát sinh hàng ngày) ---
        with col_manual:
            st.subheader("✍️ Thêm ca sửa chữa mới")
            # Dùng key duy nhất để tránh lỗi Duplicate Form
            with st.form("manual_entry_form_v3", clear_on_submit=True):
                m_c1, m_c2 = st.columns(2)
                with m_c1:
                    # Ngày xác nhận = Ngày Nghiệp vụ (Dùng để lọc Dashboard)
                    f_date = st.date_input("Ngày xác nhận", value=datetime.now())
                    f_branch = st.selectbox("Chi nhánh", ["Miền Bắc", "Miền Trung", "Miền Nam"])
                with m_c2:
                    f_machine = st.text_input("Mã số máy (Machine ID)") 
                    f_cost = st.number_input("Chi phí thực tế (đ)", min_value=0, step=10000)

                f_customer = st.text_input("Tên khách hàng")
                f_reason = st.text_area("Lý do hư hỏng", height=68)
                
                submit_manual = st.form_submit_button("💾 Lưu vào hệ thống", use_container_width=True)

                if submit_manual:
                    if not f_machine or not f_customer:
                        st.warning("⚠️ Sếp điền thiếu Mã máy hoặc Tên khách rồi!")
                    else:
                        try:
                            new_record = {
                                "confirmed_date": f_date.isoformat(),   # Nghiệp vụ
                                "branch": f_branch,
                                "machine_id": str(f_machine).strip(),
                                "compensation": float(f_cost),
                                "customer_name": f_customer,
                                "issue_reason": f_reason,
                                "created_at": datetime.now().isoformat() # Hệ thống (Dùng để sắp xếp)
                            }
                            res = supabase.table("repair_cases").insert(new_record).execute()
                            if res.data:
                                st.success(f"✅ Đã lưu thành công ca máy: {f_machine}")
                                st.cache_data.clear()
                        except Exception as e:
                            st.error(f"❌ Lỗi: {e}")

if __name__ == "__main__":
    main()
