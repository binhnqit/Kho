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

    tab_dash, tab_admin, tab_ai = st.tabs(["📊 BÁO CÁO", "📥 QUẢN TRỊ", "🧠 AI INSIGHTS"])

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

    
    # Thêm tab AI vào danh sách tabs
    tab_dash, tab_admin, tab_ai = st.tabs(["📊 BÁO CÁO", "📥 QUẢN TRỊ", "🧠 AI INSIGHTS"])

    # --- TAB 3: AI PHÂN TÍCH THÔNG MINH ---
    with tab_ai:
        st.title("🤖 Trợ Lý Phân Tích Thông Minh")
        
        if df_db.empty:
            st.info("Cần có dữ liệu để AI thực hiện phân tích.")
        else:
            ai_sub1, ai_sub2, ai_sub3 = st.tabs(["🚨 CẢNH BÁO BẤT THƯỜNG", "🛠️ PHÂN TÍCH RỦI RO", "📈 DỰ BÁO & TÓM TẮT"])

            # --- 1. AI PHÁT HIỆN BẤT THƯỜNG (Anomaly Detection) ---
            with ai_sub1:
                st.subheader("🚩 Cảnh báo chi phí vượt ngưỡng (Statistical Anomaly)")
                
                # Tính toán ngưỡng dựa trên Độ lệch chuẩn (Z-score logic)
                mean_cost = df_db['CHI_PHÍ'].mean()
                std_cost = df_db['CHI_PHÍ'].std()
                threshold = mean_cost + 2 * std_cost # Ngưỡng 2-sigma
                
                anomalies = df_db[df_db['CHI_PHÍ'] > threshold].copy()
                
                if not anomalies.empty:
                    st.error(f"Phát hiện {len(anomalies)} ca có chi phí cao bất thường (> {threshold:,.0f} đ)")
                    st.dataframe(
                        anomalies[['confirmed_dt', 'branch', 'machine_id', 'CHI_PHÍ', 'customer_name']],
                        use_container_width=True
                    )
                    
                    # Giải thích logic AI cho sếp yên tâm
                    st.caption(f"💡 AI định nghĩa 'Bất thường' là các ca có chi phí cao hơn mức trung bình ({mean_cost:,.0f} đ) cộng với 2 lần độ lệch chuẩn.")
                else:
                    st.success("✅ Chưa phát hiện ca nào có dấu hiệu trục lợi hoặc sai số chi phí lớn.")

            # --- 2. AI XẾP HẠNG RỦI RO MÁY MÓC (Risk Scoring) ---
            with ai_sub2:
                st.subheader("🏗️ Xếp hạng rủi ro thiết bị (Machine Risk Score)")
                
                # Tính Risk Score = 60% Tần suất + 40% Chi phí
                machine_stats = df_db.groupby('machine_id').agg(
                    so_lan_hong=('machine_id', 'count'),
                    tong_chi_phi=('CHI_PHÍ', 'sum')
                ).reset_index()
                
                max_cost = machine_stats['tong_chi_phi'].max() if not machine_stats.empty else 1
                machine_stats['risk_score'] = (
                    (machine_stats['so_lan_hong'] * 0.6) + 
                    (machine_stats['tong_chi_phi'] / max_cost * 0.4)
                ).round(2)
                
                top_risk = machine_stats.sort_values('risk_score', ascending=False).head(10)
                
                col_r1, col_r2 = st.columns([6, 4])
                with col_r1:
                    fig_risk = px.bar(top_risk, x='risk_score', y='machine_id', orientation='h',
                                     title="Top 10 Máy Rủi Ro Cao Nhất",
                                     color='risk_score', color_continuous_scale='Reds')
                    st.plotly_chart(fig_risk, use_container_width=True)
                
                with col_r2:
                    st.write("📋 Danh sách máy cần bảo trì ngay:")
                    st.dataframe(top_risk[['machine_id', 'risk_score']], hide_index=True)

            # --- 3. DỰ BÁO & TÓM TẮT TỰ ĐỘNG ---
            with ai_sub3:
                st.subheader("🔮 Dự báo ngân sách & Tóm tắt")
                
                # Tính dự báo Rolling Mean 3 tháng
                monthly_data = df_db.groupby(['NĂM', 'THÁNG'])['CHI_PHÍ'].sum().reset_index()
                if len(monthly_data) >= 2:
                    forecast_value = monthly_data['CHI_PHÍ'].rolling(window=3, min_periods=1).mean().iloc[-1]
                    current_month_cost = monthly_data['CHI_PHÍ'].iloc[-1]
                    diff_pct = ((forecast_value / current_month_cost) - 1) * 100
                    
                    c1, c2 = st.columns(2)
                    c1.metric("Dự báo ngân sách tháng tới", f"{forecast_value:,.0f} đ")
                    c2.metric("Biến động dự kiến", f"{diff_pct:.1f}%", delta=f"{diff_pct:.1f}%", delta_color="inverse")
                
                st.divider()
                
                # AI Report Summary (Logic mẫu)
                if st.button("🧠 AI TÓM TẮT BÁO CÁO THÁNG NÀY"):
                    latest_month = df_db['THÁNG'].iloc[0]
                    month_df = df_db[df_db['THÁNG'] == latest_month]
                    
                    summary_text = f"""
                    **BÁO CÁO NHANH THÁNG {latest_month}/2026:**
                    - **Tổng quan:** Hệ thống ghi nhận {len(month_df)} ca sửa chữa với tổng chi phí {month_df['CHI_PHÍ'].sum():,.0f} đ.
                    - **Điểm nóng:** Chi nhánh **{month_df['branch'].value_counts().idxmax()}** có tần suất sửa chữa cao nhất.
                    - **Rủi ro:** Phát hiện máy **{month_df['machine_id'].value_counts().idxmax()}** lặp lại sự cố nhiều lần.
                    - **Khuyến nghị:** Cần rà soát lại quy trình vận hành tại các chi nhánh có chi phí vượt ngưỡng 2-sigma.
                    """
                    st.info(summary_text)

                # Ô chat hỏi đáp dữ liệu (UI Placeholder - Giai đoạn tiếp theo kết nối LLM)
                st.divider()
                user_q = st.text_input("💬 Hỏi Trợ lý AI về dữ liệu (Ví dụ: Máy nào hỏng nhiều nhất ở Miền Bắc?)")
                if user_q:
                    st.write("🤖 *AI đang phân tích DataFrame...*")
                    # Chỗ này sếp có thể tích hợp LangChain hoặc đơn giản là lọc chuỗi (Regex)
                    if "miền bắc" in user_q.lower():
                        mb_data = df_db[df_db['branch'] == 'Miền Bắc']['machine_id'].value_counts().head(1)
                        st.write(f"Dạ, ở Miền Bắc máy **{mb_data.index[0]}** đang hỏng nhiều nhất ({mb_data.values[0]} lần) sếp nhé!")
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
