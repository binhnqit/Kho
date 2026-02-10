import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from datetime import datetime

# --- 1. KẾT NỐI HỆ THỐNG ---
url = "https://cigbnbaanpebwrufzxfg.supabase.co"
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. HÀM XỬ LÝ DỮ LIỆU (HARDENED LOGIC) ---
@st.cache_data(ttl=30)
def load_repair_data_final():
    try:
        # Lấy dữ liệu mới nhất từ Supabase (Sắp xếp theo thời gian tạo hệ thống)
        res = supabase.table("repair_cases") \
            .select("*") \
            .order("created_at", desc=True) \
            .execute()
            
        if not res.data: 
            return pd.DataFrame()
        
        df = pd.DataFrame(res.data)

        # Chuyển đổi datetime và bọc lỗi
        df['confirmed_dt'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        df['created_dt']   = pd.to_datetime(df['created_at'], errors='coerce')
        df = df.dropna(subset=['confirmed_dt'])

        # Trích xuất chiều thời gian (Dùng cho Báo cáo & AI)
        df['NĂM'] = df['confirmed_dt'].dt.year.astype(int)
        df['THÁNG'] = df['confirmed_dt'].dt.month.astype(int)
        
        day_map = {'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
                   'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ Nhật'}
        df['THỨ'] = df['confirmed_dt'].dt.day_name().map(day_map)

        # Làm sạch số liệu chi phí
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)
        
        # Luôn ưu tiên hiển thị record mới nạp lên đầu
        df = df.sort_values(by='created_dt', ascending=False)
        return df
    except Exception as e:
        st.error(f"Lỗi hệ thống tải data: {e}")
        return pd.DataFrame()

# --- 3. GIAO DIỆN CHÍNH ---
def main():
    st.set_page_config(page_title="4ORANGES OPS 2026", layout="wide", page_icon="🎨")
    
    # Load dữ liệu tổng
    df_db = load_repair_data_final()

    # --- TABS CHỨC NĂNG ---
    tab_dash, tab_admin, tab_ai = st.tabs(["📊 BÁO CÁO VẬN HÀNH", "📥 QUẢN TRỊ HỆ THỐNG", "🧠 AI INSIGHTS"])

    # --- TAB 1: BÁO CÁO VẬN HÀNH ---
    with tab_dash:
        if df_db.empty:
            st.info("Chưa có dữ liệu. Vui lòng nạp ở Tab Quản trị.")
        else:
            with st.sidebar:
                st.header("⚙️ BỘ LỌC")
                if st.button("🔄 LÀM MỚI DỮ LIỆU", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()
                
                filter_mode = st.radio("Chế độ lọc:", ["Theo Tháng/Năm", "Theo Khoảng ngày"])

                if filter_mode == "Theo Tháng/Năm":
                    available_years = sorted(df_db['NĂM'].unique(), reverse=True)
                    sel_year = st.selectbox("📅 Chọn năm", options=available_years)
                    available_months = sorted(df_db[df_db['NĂM'] == sel_year]['THÁNG'].unique().tolist())
                    sel_month = st.selectbox("📆 Chọn tháng", options=["Tất cả"] + available_months)
                    
                    df_view = df_db[df_db['NĂM'] == sel_year].copy()
                    if sel_month != "Tất cả":
                        df_view = df_view[df_view['THÁNG'] == sel_month]
                        # Tính Delta so với tháng trước
                        prev_m = sel_month - 1 if sel_month > 1 else 12
                        prev_y = sel_year if sel_month > 1 else sel_year - 1
                        df_prev = df_db[(df_db['NĂM'] == prev_y) & (df_db['THÁNG'] == prev_m)]
                    else:
                        df_prev = pd.DataFrame()
                else:
                    date_range = st.date_input("Chọn khoảng ngày", value=[df_db['confirmed_dt'].min(), df_db['confirmed_dt'].max()])
                    if len(date_range) == 2:
                        df_view = df_db[(df_db['confirmed_dt'].dt.date >= date_range[0]) & (df_db['confirmed_dt'].dt.date <= date_range[1])].copy()
                    df_prev = pd.DataFrame()

            # --- KPI METRICS ---
            st.title("🚀 Chỉ Số Vận Hành")
            c1, c2, c3 = st.columns(3)
            curr_cost = df_view['CHI_PHÍ'].sum()
            if not df_prev.empty:
                delta = curr_cost - df_prev['CHI_PHÍ'].sum()
                c1.metric("💰 TỔNG CHI PHÍ", f"{curr_cost:,.0f} đ", delta=f"{delta:,.0f} đ", delta_color="inverse")
            else:
                c1.metric("💰 TỔNG CHI PHÍ", f"{curr_cost:,.0f} đ")
            
            c2.metric("🛠️ SỐ CA", f"{len(df_view)} ca")
            top_b = df_view['branch'].value_counts().idxmax() if not df_view.empty else "N/A"
            c3.metric("🏢 ĐIỂM NÓNG", top_b)

            # --- CHARTS ---
            st.divider()
            col_left, col_right = st.columns([6, 4])
            with col_left:
                st.subheader("📅 Xu hướng sự vụ theo thứ")
                order = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ Nhật']
                day_counts = df_view['THỨ'].value_counts().reindex(order).fillna(0)
                day_stats = day_counts.reset_index()
                day_stats.columns = ['NGÀY_TRONG_TUẦN', 'SỐ_CA'] # Ép tên cột rõ ràng

                st.plotly_chart(
                px.area(day_stats, x='NGÀY_TRONG_TUẦN', y='SỐ_CA', markers=True), 
                use_container_width=True
                )
            
            with col_right:
                st.subheader("🚨 Ca chi phí cao")
                st.table(df_view.nlargest(5, 'CHI_PHÍ')[['confirmed_dt', 'machine_id', 'CHI_PHÍ']])

    # --- TAB 2: QUẢN TRỊ (Sub-tabs & Rollback) ---
    # --- TAB 2: QUẢN TRỊ HỆ THỐNG (UPGRADED) ---
with tab_admin:
    st.title("📥 Quản Trị & Điều Hành Chi Nhánh")
    
    # Chia tab con theo cấu trúc Enterprise
    admin_sub1, admin_sub2, admin_sub3 = st.tabs([
        "➕ NHẬP LIỆU HỆ THỐNG", 
        "🏢 TÌNH TRẠNG CHI NHÁNH", 
        "📜 TRUY VẾT & AUDIT"
    ])

    # --- 1. NHẬP LIỆU (Manual + CSV) ---
    with admin_sub1:
        c_up, c_man = st.columns([4, 6])
        
        with c_up:
            st.subheader("📂 Import File CSV")
            up_file = st.file_uploader("Chọn file dữ liệu đồng bộ", type="csv", key="csv_admin")
            if up_file:
                df_up = pd.read_csv(up_file)
                batch_id = f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M')}"
                
                # Bổ sung metadata chuẩn Audit
                df_up['batch_id'] = batch_id
                df_up['created_at'] = datetime.now().isoformat()
                
                st.write(f"🔍 Xem trước lô: **{batch_id}** ({len(df_up)} dòng)")
                st.dataframe(df_up.head(5), use_container_width=True)
                
                if st.button(f"🚀 Xác nhận nạp Lô {batch_id}", use_container_width=True, type="primary"):
                    try:
                        # Ép kiểu dữ liệu trước khi đẩy lên Supabase để khớp DB
                        if 'compensation' in df_up.columns:
                            df_up['compensation'] = pd.to_numeric(df_up['compensation']).fillna(0)
                        
                        supabase.table("repair_cases").upsert(df_up.to_dict(orient='records')).execute()
                        st.success(f"✅ Đã nạp thành công {len(df_up)} bản ghi!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi nạp Batch: {e}")

        with c_man:
            # FORM NHẬP TAY CHUẨN ENTERPRISE
            with st.form("f_man_enterprise", clear_on_submit=True):
                st.subheader("✍️ Nhập ca sửa chữa đơn lẻ")
                c1, c2 = st.columns(2)
                with c1:
                    f_machine = st.text_input("Mã máy *")
                    f_branch = st.selectbox("Chi nhánh *", ["Miền Bắc", "Miền Trung", "Miền Nam"])
                    f_cost = st.number_input("Chi phí thực tế (đ)", min_value=0, step=10000)
                with c2:
                    f_confirmer = st.text_input("Người xác nhận *")
                    f_confirmed_date = st.date_input("Ngày xác nhận", value=datetime.now())
                    f_reason = st.selectbox(
                        "Nguyên nhân hư hỏng",
                        ["Hao mòn", "Lỗi vận hành", "Lỗi linh kiện", "Ngoại lực", "Khác"]
                    )
                f_note = st.text_area("Ghi chú thêm (nếu có)")

                if st.form_submit_button("💾 Lưu vào cơ sở dữ liệu", use_container_width=True):
                    if not f_machine or not f_confirmer:
                        st.warning("⚠️ Vui lòng điền đủ Mã máy và Người xác nhận.")
                    else:
                        record = {
                            "machine_id": f_machine.strip().upper(),
                            "branch": f_branch,
                            "compensation": float(f_cost), # Map đúng cột gốc Database
                            "confirmed_by": f_confirmer,
                            "confirmed_date": f_confirmed_date.isoformat(), # Map đúng cột gốc Database
                            "issue_reason": f_reason,
                            "note": f_note,
                            "batch_id": f"MANUAL_{datetime.now().strftime('%Y%m%d')}",
                            "created_at": datetime.now().isoformat()
                        }
                        try:
                            supabase.table("repair_cases").insert(record).execute()
                            st.success("✅ Đã lưu ca sửa chữa và cập nhật hệ thống!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi lưu tay: {e}")

    # --- 2. TÌNH TRẠNG THEO MIỀN ---
    with admin_sub2:
        st.subheader("🏢 Theo dõi vận hành theo chi nhánh")
        sel_branch = st.selectbox("Chọn chi nhánh để xem báo cáo nhanh", ["Miền Bắc", "Miền Trung", "Miền Nam"])
        
        df_branch = df_db[df_db['branch'] == sel_branch]
        
        if not df_branch.empty:
            bc1, bc2, bc3 = st.columns(3)
            bc1.metric("🛠️ Tổng số ca", f"{len(df_branch)} ca")
            bc2.metric("💰 Tổng chi phí", f"{df_branch['CHI_PHÍ'].sum():,.0f} đ")
            
            # Xử lý trường hợp có dữ liệu nhưng chưa có máy nào hỏng
            top_m = df_branch['machine_id'].value_counts()
            if not top_m.empty:
                bc3.metric("⚠️ Máy lỗi nhiều nhất", top_m.idxmax())

            st.divider()
            st.write(f"📋 **Danh sách thiết bị có rủi ro tại {sel_branch}**")
            
            # Bảng tổng hợp tình trạng máy (Aggregated View)
            machine_view = (
                df_branch
                .groupby('machine_id')
                .agg(
                    so_lan=('machine_id', 'count'),
                    tong_chi_phi=('CHI_PHÍ', 'sum'),
                    ca_moi_nhat=('confirmed_dt', 'max')
                )
                .reset_index()
                .sort_values('so_lan', ascending=False)
            )
            
            st.dataframe(
                machine_view.style.format({'tong_chi_phi': '{:,.0f} đ'}), 
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.info(f"Chi nhánh {sel_branch} hiện chưa có dữ liệu ghi nhận.")

    # --- 3. LỊCH SỬ BATCH & AUDIT ---
    with admin_sub3:
        st.subheader("📜 Nhật ký nhập liệu (Audit Trail)")
        if 'batch_id' in df_db.columns:
            # Lấy danh sách lô trừ các ca nhập lẻ
            history = df_db.groupby('batch_id').agg(
                so_dong=('id', 'count'),
                tong_tien=('CHI_PHÍ', 'sum'),
                ngay_nap=('created_dt', 'max')
            ).reset_index().sort_values('ngay_nap', ascending=False)
            
            st.dataframe(history, use_container_width=True, hide_index=True)
            
            st.divider()
            # Tính năng Rollback cực kỳ quan trọng như sếp nói
            st.subheader("🔥 Khu vực xử lý lỗi (Rollback)")
            target_batch = st.selectbox("Chọn lô dữ liệu muốn xóa/thu hồi:", history['batch_id'].unique())
            
            if st.button(f"🗑️ XOÁ VĨNH VIỄN LÔ {target_batch}"):
                if "MANUAL" in target_batch:
                    st.error("Lô nhập tay không được xóa hàng loạt. Vui lòng xóa từng dòng trong Database.")
                else:
                    try:
                        supabase.table("repair_cases").delete().eq("batch_id", target_batch).execute()
                        st.success(f"💥 Đã xóa sạch dữ liệu lô {target_batch}!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi Rollback: {e}")

    # --- TAB 3: AI INSIGHTS (ENTERPRISE HARDENED) ---
    with tab_ai:
        st.title("🧠 Trợ Lý AI Phân Tích")
        
        # 1. Hardening Data
        cost_series = df_db['CHI_PHÍ'].dropna()
        if len(cost_series) < 10:
            st.warning("⚠️ Dữ liệu quá mỏng để AI phân tích. Cần tối thiểu 10 ca.")
            st.stop()

        ai_1, ai_2, ai_3 = st.tabs(["🚩 CẢNH BÁO", "🏗️ RỦI RO THIẾT BỊ", "📊 DỰ BÁO"])

        with ai_1:
            # Anomaly Detection (2-Sigma)
            threshold = cost_series.mean() + 2 * cost_series.std()
            anomalies = df_db[df_db['CHI_PHÍ'] > threshold]
            if not anomalies.empty:
                st.error(f"Phát hiện {len(anomalies)} ca vượt ngưỡng chi phí an toàn!")
                st.dataframe(anomalies[['confirmed_dt', 'machine_id', 'CHI_PHÍ']])
            else:
                st.success("Không phát hiện bất thường về chi phí.")

        with ai_2:
            # Risk Scoring (Normalized)
            m_stats = df_db.groupby('machine_id').agg(count=('machine_id','count'), cost=('CHI_PHÍ','sum')).reset_index()
            # Normalize về thang 0-1
            m_stats['freq_norm'] = m_stats['count'] / m_stats['count'].max()
            m_stats['cost_norm'] = m_stats['cost'] / m_stats['cost'].max()
            m_stats['risk_score'] = (m_stats['freq_norm'] * 0.6 + m_stats['cost_norm'] * 0.4).round(2)
            
            st.plotly_chart(px.bar(m_stats.nlargest(10, 'risk_score'), x='risk_score', y='machine_id', orientation='h', title="Top 10 Máy Rủi Ro Cao (Đã Normalize)"))

        with ai_3:
            # Forecast & Latest Month Fix
            monthly = df_db.groupby(['NĂM', 'THÁNG'])['CHI_PHÍ'].sum().reset_index()
            if len(monthly) >= 2:
                # Dùng MAX để lấy tháng mới nhất
                latest_data = monthly.sort_values(['NĂM', 'THÁNG']).iloc[-1]
                curr_month_val = latest_data['CHI_PHÍ']
                forecast_val = monthly['CHI_PHÍ'].rolling(3, min_periods=1).mean().iloc[-1]
                
                # Bọc chia cho 0
                diff = ((forecast_val / curr_month_val) - 1) * 100 if curr_month_val > 0 else 0
                
                c_f1, c_f2 = st.columns(2)
                c_f1.metric("Dự báo tháng tới", f"{forecast_val:,.0f} đ")
                c_f2.metric("Biến động dự kiến", f"{diff:.1f}%", delta=f"{diff:.1f}%", delta_color="inverse")

            # NLP Parser nhẹ
            st.divider()
            q = st.text_input("💬 Hỏi AI (Ví dụ: 'Máy nào hỏng ở Miền Bắc?')")
            if q:
                branch_key = "Miền Bắc" if "bắc" in q.lower() else "Miền Nam" if "nam" in q.lower() else None
                if branch_key:
                    res_q = df_db[df_db['branch'] == branch_key]['machine_id'].value_counts()
                    st.info(f"🤖 Vùng {branch_key}: Máy {res_q.index[0]} hỏng nhiều nhất ({res_q.values[0]} lần).")

if __name__ == "__main__":
    main()
