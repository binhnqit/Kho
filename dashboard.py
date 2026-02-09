import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from datetime import datetime

# --- 1. KẾT NỐI ---
url = "https://cigbnbaanpebwrufzxfg.supabase.co"
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. HÀM XỬ LÝ (NÂNG CẤP PHÁ CACHE & ÉP THỨ TỰ) ---
@st.cache_data(ttl=30) # Cache ngắn để nhạy bén với dữ liệu mới
def load_repair_data_final():
    try:
        # FIX: Dùng desc=True thay vì ascending=False
        res = supabase.table("repair_cases") \
            .select("*") \
            .order("created_at", desc=True) \
            .execute()
            
        if not res.data: 
            return pd.DataFrame()
        
        df = pd.DataFrame(res.data)

        # PHÂN TÁCH THỜI GIAN
        df['confirmed_dt'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        df['created_dt']   = pd.to_datetime(df['created_at'], errors='coerce')
        df = df.dropna(subset=['confirmed_dt'])

        # TRÍCH XUẤT THÔNG TIN
        df['NĂM'] = df['confirmed_dt'].dt.year.astype(int)
        df['THÁNG'] = df['confirmed_dt'].dt.month.astype(int)
        
        day_map = {'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
                   'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ Nhật'}
        df['THỨ'] = df['confirmed_dt'].dt.day_name().map(day_map)

        # CHUẨN HÓA SỐ LIỆU
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)
        
        # Sắp xếp trong Pandas (Ở đây thì lại dùng ascending=False sếp nhé, trớ trêu vậy đó!)
        df = df.sort_values(by='created_dt', ascending=False)

        return df
    except Exception as e:
        st.error(f"Lỗi logic tải data: {e}")
        return pd.DataFrame()

# --- 3. GIAO DIỆN CHÍNH ---
def main():
    st.set_page_config(page_title="4ORANGES OPS 2026", layout="wide", page_icon="🎨")
    
    # Load dữ liệu đầu vào
    df_db = load_repair_data_final()

    # --- KHỐI DEBUG (Kiểm tra độ trễ DB) ---
    if not df_db.empty:
        with st.expander("🛠️ DEBUG HỆ THỐNG (Dành cho sếp)"):
            st.write("5 record mới nhất theo thời gian hệ thống (created_at):")
            # Dùng để soi xem record vừa nạp đã lên tới app chưa
            st.write(df_db[['created_dt', 'machine_id', 'confirmed_dt', 'CHI_PHÍ']].head(5))

    tab_dash, tab_admin = st.tabs(["📊 BÁO CÁO VẬN HÀNH", "📥 QUẢN TRỊ"])

    # --- TAB 1: BÁO CÁO VẬN HÀNH ---
    with tab_dash:
        if df_db.empty:
            st.info("Chưa có dữ liệu. Vui lòng nạp ở Tab Quản trị.")
        else:
            # --- 1. SIDEBAR NÂNG CẤP: RANGE FILTER ---
            with st.sidebar:
                st.header("⚙️ BỘ LỌC VẬN HÀNH")
                if st.button("🔄 LÀM MỚI HỆ THỐNG", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()
                st.divider()

                # Lựa chọn chế độ lọc
                filter_mode = st.radio("Chế độ xem:", ["Theo Tháng/Năm", "Theo Khoảng ngày"])

                if filter_mode == "Theo Tháng/Năm":
                    available_years = sorted(df_db['NĂM'].unique(), reverse=True)
                    sel_year = st.selectbox("📅 Chọn năm", options=available_years)
                    available_months = sorted(df_db[df_db['NĂM'] == sel_year]['THÁNG'].unique().tolist())
                    sel_month = st.selectbox("📆 Chọn tháng", options=["Tất cả"] + available_months)
                    
                    # Logic lọc dữ liệu cho chế độ tháng
                    df_view = df_db[df_db['NĂM'] == sel_year].copy()
                    if sel_month != "Tất cả":
                        df_view = df_view[df_view['THÁNG'] == sel_month]
                        # Tính toán Delta cho KPI (Tháng này vs Tháng trước)
                        prev_month = sel_month - 1 if sel_month > 1 else 12
                        prev_year = sel_year if sel_month > 1 else sel_year - 1
                        df_prev = df_db[(df_db['NĂM'] == prev_year) & (df_db['THÁNG'] == prev_month)]
                    else:
                        df_prev = pd.DataFrame() # Không so sánh nếu xem cả năm
                
                else:
                    # Chế độ lọc Range [Chuẩn nghiệp vụ sếp đề xuất]
                    min_date = df_db['confirmed_dt'].min().date()
                    max_date = df_db['confirmed_dt'].max().date()
                    date_range = st.date_input("Chọn khoảng ngày nghiệp vụ", value=[min_date, max_date])
                    
                    if len(date_range) == 2:
                        start_date, end_date = date_range
                        df_view = df_db[(df_db['confirmed_dt'].dt.date >= start_date) & 
                                        (df_db['confirmed_dt'].dt.date <= end_date)].copy()
                        df_prev = pd.DataFrame() # Tạm để trống delta cho range
                    else:
                        df_view = df_db.copy()
                        df_prev = pd.DataFrame()

            # --- 2. HIỂN THỊ KPI CÓ DELTA (SO VỚI KỲ TRƯỚC) ---
            st.title("🚀 Dashboard Chỉ Số Vận Hành")
            
            c1, c2, c3 = st.columns(3)
            
            # KPI Chi phí + Delta
            current_cost = df_view['CHI_PHÍ'].sum()
            if not df_prev.empty:
                prev_cost = df_prev['CHI_PHÍ'].sum()
                delta_cost = current_cost - prev_cost
                c1.metric("💰 TỔNG CHI PHÍ", f"{current_cost:,.0f} đ", delta=f"{delta_cost:,.0f} đ", delta_color="inverse")
            else:
                c1.metric("💰 TỔNG CHI PHÍ", f"{current_cost:,.0f} đ")

            # KPI Số ca + Delta
            current_count = len(df_view)
            if not df_prev.empty:
                prev_count = len(df_prev)
                delta_count = current_count - prev_count
                c2.metric("🛠️ SỐ CA SỬA CHỮA", f"{current_count} ca", delta=f"{delta_count} ca", delta_color="inverse")
            else:
                c2.metric("🛠️ SỐ CA SỬA CHỮA", f"{current_count} ca")

            # Insight Chi nhánh
            top_branch = df_view['branch'].value_counts().idxmax() if not df_view.empty else "N/A"
            c3.metric("🏢 ĐIỂM NÓNG CHI NHÁNH", top_branch)

            st.divider()

            # --- 3. PHÂN TÍCH CHUYÊN SÂU (INSIGHT THẬT) ---
            col_chart, col_insight = st.columns([6, 4])
            
            with col_chart:
                st.subheader("📅 Biến động sự vụ theo thứ")
                order = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ Nhật']
                day_stats = df_view['THỨ'].value_counts().reindex(order).fillna(0).reset_index()
                day_stats.columns = ['THỨ', 'SỐ_CA']
                fig = px.area(day_stats, x='THỨ', y='SỐ_CA', markers=True, color_discrete_sequence=['#00CC96'])
                st.plotly_chart(fig, use_container_width=True)

            with col_insight:
                st.subheader("🚨 Ca chi phí cao bất thường")
                # Highlight 5 ca "đốt tiền" nhất trong kỳ lọc
                top_expensive = df_view.nlargest(5, 'CHI_PHÍ')[['confirmed_dt', 'machine_id', 'CHI_PHÍ', 'branch']]
                st.table(top_expensive.style.format({'CHI_PHÍ': '{:,.0f} đ'}))

            # --- 4. BẢNG DỮ LIỆU ĐA TRỤC THỜI GIAN ---
            st.divider()
            col_list, col_repeat = st.columns([7, 3])
            
            with col_list:
                st.subheader("📋 Danh sách ca mới nhất (Hệ thống)")
                st.dataframe(
                    df_view.sort_values('created_dt', ascending=False).head(10)[['confirmed_dt', 'created_dt', 'branch', 'machine_id', 'CHI_PHÍ']],
                    use_container_width=True, hide_index=True
                )

            with col_repeat:
                st.subheader("🔄 Máy sửa lặp lại")
                # Insight: Máy nào hỏng trên 1 lần trong kỳ lọc
                repeat_machines = df_view['machine_id'].value_counts()
                repeat_machines = repeat_machines[repeat_machines > 1].reset_index()
                repeat_machines.columns = ['Mã máy', 'Số lần hỏng']
                if not repeat_machines.empty:
                    st.warning(f"Phát hiện {len(repeat_machines)} máy sửa nhiều lần!")
                    st.dataframe(repeat_machines, use_container_width=True, hide_index=True)
                else:
                    st.success("Không có máy hỏng lặp lại.")

            with st.expander("🔎 Truy xuất toàn bộ bản ghi"):
                st.dataframe(df_view.sort_values('created_dt', ascending=False), use_container_width=True)

    # --- TAB 2: QUẢN TRỊ ---
    # --- TAB 2: QUẢN TRỊ (Sub-tabs nâng cấp) ---
    with tab_admin:
        st.title("📥 HỆ THỐNG QUẢN TRỊ DỮ LIỆU")
        
        # Chia nhỏ các khu vực quản lý
        sub1, sub2, sub3 = st.tabs(["➕ NHẬP LIỆU", "📜 LỊCH SỬ & ROLLBACK", "⚙️ CẤU HÌNH"])

        # --- SUB-TAB 1: NHẬP LIỆU ---
        with sub1:
            col_import, col_manual = st.columns([1, 1])

            with col_import:
                st.subheader("📂 Import File CSV")
                uploaded_file = st.file_uploader("Chọn file CSV", type=["csv"], key="csv_upload_pro")
                if uploaded_file:
                    df_up = pd.read_csv(uploaded_file)
                    
                    # Tạo batch_id duy nhất cho lần nạp này để dễ dàng Rollback
                    batch_id = f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    
                    if 'confirmed_date' in df_up.columns:
                        df_up['confirmed_date'] = pd.to_datetime(df_up['confirmed_date'], errors='coerce').dt.strftime('%Y-%m-%d')
                    
                    df_up['compensation'] = pd.to_numeric(df_up.get('compensation', 0), errors='coerce').fillna(0)
                    df_up['created_at'] = datetime.now().isoformat()
                    df_up['batch_id'] = batch_id # Gắn nhãn batch
                    
                    st.info(f"Mã lô nạp (Batch ID): **{batch_id}**")
                    st.dataframe(df_up.head(3), use_container_width=True)
                    
                    if st.button("🚀 Xác nhận Upload Lô này", use_container_width=True, type="primary"):
                        try:
                            res = supabase.table("repair_cases").upsert(df_up.to_dict(orient='records')).execute()
                            if res.data:
                                st.success(f"✅ Đã nạp thành công lô {batch_id}")
                                st.cache_data.clear()
                                st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi: {e}")

            with col_manual:
                st.subheader("✍️ Nhập tay ca mới")
                with st.form("manual_entry_form_v4", clear_on_submit=True):
                    f_date = st.date_input("Ngày xác nhận nghiệp vụ", value=datetime.now())
                    
                    # KHÓA CHỈNH SỬA QUÁ KHỨ (> 30 ngày) -
                    is_too_old = (datetime.now().date() - f_date).days > 30
                    
                    m_c1, m_c2 = st.columns(2)
                    with m_c1:
                        f_branch = st.selectbox("Chi nhánh", ["Miền Bắc", "Miền Trung", "Miền Nam"])
                        f_machine = st.text_input("Mã số máy")
                    with m_c2:
                        f_cost = st.number_input("Chi phí thực tế", min_value=0)
                        f_customer = st.text_input("Tên khách hàng")
                    
                    f_reason = st.text_area("Lý do hư hỏng")
                    
                    if st.form_submit_button("💾 Lưu vào hệ thống", use_container_width=True):
                        if is_too_old:
                            st.error("❌ Không được chỉnh ca quá 30 ngày. Vui lòng liên hệ Tổng Admin.")
                        elif not f_machine or not f_customer:
                            st.warning("⚠️ Vui lòng điền đủ Mã máy và Khách hàng.")
                        else:
                            try:
                                new_record = {
                                    "confirmed_date": f_date.isoformat(),
                                    "branch": f_branch,
                                    "machine_id": str(f_machine).strip(),
                                    "compensation": float(f_cost),
                                    "customer_name": f_customer,
                                    "issue_reason": f_reason,
                                    "created_at": datetime.now().isoformat(),
                                    "batch_id": "MANUAL_ENTRY"
                                }
                                res = supabase.table("repair_cases").insert(new_record).execute()
                                if res.data:
                                    st.success("✅ Đã lưu!")
                                    st.cache_data.clear()
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Lỗi: {e}")

        # --- SUB-TAB 2: LỊCH SỬ & ROLLBACK (Phòng ngừa lỗi nạp file sai) ---
        with sub2:
            st.subheader("📜 Quản lý các lô dữ liệu (Batch)")
            if not df_db.empty and 'batch_id' in df_db.columns:
                # Lấy danh sách các batch trừ Manual
                batches = df_db[df_db['batch_id'] != 'MANUAL_ENTRY']['batch_id'].unique().tolist()
                
                if batches:
                    selected_batch = st.selectbox("Chọn Lô dữ liệu cần kiểm tra/xóa:", batches)
                    batch_data = df_db[df_db['batch_id'] == selected_batch]
                    
                    st.write(f"Lô này có: **{len(batch_data)} bản ghi**")
                    st.dataframe(batch_data.head(5), use_container_width=True)
                    
                    # Chức năng Rollback -
                    if st.button(f"🗑️ XOÁ TOÀN BỘ LÔ {selected_batch}", type="secondary"):
                        confirm = st.warning(f"Bạn có chắc muốn xóa vĩnh viễn {len(batch_data)} dòng này?")
                        if st.button("🔥 XÁC NHẬN XOÁ NGAY"):
                            try:
                                supabase.table("repair_cases").delete().eq("batch_id", selected_batch).execute()
                                st.success("💥 Đã xóa thành công lô dữ liệu lỗi!")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Lỗi khi rollback: {e}")
                else:
                    st.info("Chưa có lô dữ liệu CSV nào được nạp.")
            else:
                st.info("Dữ liệu hiện tại không hỗ trợ Batch ID.")

        # --- SUB-TAB 3: CẤU HÌNH (Dọn dẹp/Bảo trì) ---
        with sub3:
            st.subheader("🧹 Bảo trì dữ liệu")
            st.warning("Khu vực dành cho kĩ thuật viên hệ thống")
            if st.button("🧹 Dọn dẹp Cache Streamlit", use_container_width=True):
                st.cache_data.clear()
                st.success("Đã làm mới toàn bộ cache ứng dụng.")

if __name__ == "__main__":
    main()
