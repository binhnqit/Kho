import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from core.database import supabase
from services.repair_service import insert_new_repair, update_repair_tracking, STATUS_OPTIONS

def render_enterprise_tracking(df_to_track):
    # ... (giữ nguyên phần code phía trên)
    
    with tab_ncc:
        df_ncc = df_to_track[df_to_track['status'].str.contains("4.", na=False)].copy()
        if not df_ncc.empty:
            # Bước 1: Ép kiểu sang datetime, các giá trị lỗi sẽ biến thành NaT (Not a Time)
            df_ncc['confirmed_date'] = pd.to_datetime(df_ncc['confirmed_date'], errors='coerce')
            
            # Bước 2: Chỉ tính toán trên những dòng có dữ liệu ngày tháng hợp lệ
            # Loại bỏ các dòng NaT để tránh lỗi AttributeError khi gọi .dt
            df_ncc = df_ncc.dropna(subset=['confirmed_date'])
            
            if not df_ncc.empty:
                # Bước 3: Tính toán số ngày an toàn
                df_ncc['days'] = (datetime.now().date() - df_ncc['confirmed_date'].dt.date).dt.days
                
                st.warning(f"⚠️ Có {len(df_ncc)} máy đang nằm tại NCC.")
                st.dataframe(
                    df_ncc[['machine_display', 'days', 'issue_reason', 'receiver_name']], 
                    column_config={"days": st.column_config.NumberColumn("Số ngày tồn", format="%d ngày ⏳")},
                    use_container_width=True, hide_index=True
                )
            else:
                st.info("Dữ liệu ngày xác nhận của các máy tại NCC không hợp lệ.")
        else:
            st.info("Hiện tại không có máy nào đang gửi NCC.")
def render_status_management(df):
    """
    Giao diện Quản lý luồng máy Nhận - Trả chuyên nghiệp.
    Tích hợp Dashboard, Enterprise Tracking (Đối soát NCC/Đã trả) và Cập nhật tiến độ.
    """
    
    # ==========================================
    # 1. PHẦN TỔNG HỢP & LỌC THEO VÙNG (DASHBOARD)
    # ==========================================
    st.markdown("### 📊 Tổng quan vận hành")
    
    # Bộ lọc vùng miền cho toàn bộ Tab
    list_branches = ["Tất cả"] + sorted(df['branch'].unique().tolist())
    selected_region = st.selectbox("📍 Lọc theo khu vực đối soát:", list_branches, index=0)
    
    # Lọc dữ liệu theo vùng đã chọn
    df_filtered = df if selected_region == "Tất cả" else df[df['branch'] == selected_region]

    # Tính toán số lượng theo trạng thái
    status_counts = df_filtered['status'].value_counts().reindex(STATUS_OPTIONS, fill_value=0).reset_index()
    status_counts.columns = ['Trạng thái', 'Số lượng']

    # Hiển thị Metrics tóm tắt (6 cột tương ứng 6 trạng thái)
    m_cols = st.columns(len(STATUS_OPTIONS))
    for idx, row in status_counts.iterrows():
        label = row['Trạng thái'].split(". ")[1] if ". " in row['Trạng thái'] else row['Trạng thái']
        m_cols[idx].metric(label, f"{row['Số lượng']} máy")

    # Biểu đồ trực quan hóa
    fig_status = px.bar(
        status_counts, x='Số lượng', y='Trạng thái', orientation='h',
        title=f"Phân bổ thiết bị - {selected_region}",
        color='Trạng thái', color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig_status.update_layout(showlegend=False, height=300, margin=dict(t=30, b=0, l=0, r=0))
    st.plotly_chart(fig_status, use_container_width=True)

    st.divider()

    # ==========================================
    # 2. NÂNG CẤP: GỌI HÀM ĐỐI SOÁT DOANH NGHIỆP
    # (Hiển thị danh sách máy tại NCC, máy chờ trả, máy hoàn tất)
    # ==========================================
    render_enterprise_tracking(df_filtered)

    st.divider()

    # ==========================================
    # 3. PHẦN ĐIỀU PHỐI & CẬP NHẬT CHI TIẾT
    # ==========================================
    st.markdown("### 🚚 Điều phối & Cập nhật trạng thái")
    
    # Kiểm tra tính toàn vẹn Schema
    required_cols = ['status', 'machine_display', 'branch', 'id', 'issue_reason']
    if not all(col in df.columns for col in required_cols):
        st.error("❌ Cấu trúc Database không tương thích. Vui lòng kiểm tra lại Query.")
        return

    # Lọc các ca đang xử lý (SLA Active) trong vùng đã chọn
    active_cases = df_filtered[df_filtered['status'] != "6. Đã trả chi nhánh"]
    
    if active_cases.empty:
        st.success(f"✅ Khu vực {selected_region} hiện không có thiết bị tồn đọng.")
        # Mẹo: Vẫn cho phép tra cứu lịch sử ở dưới dù không có ca active
        selected_code = None 
    else:
        # Giao diện chọn thiết bị để update
        col_sel, col_info = st.columns([1, 1.5])
        with col_sel:
            selected_code = st.selectbox(
                "🔍 Chọn máy cần cập nhật tiến độ:", 
                active_cases['machine_display'].unique(),
                key="status_mgmt_select"
            )
            
        case_info = active_cases[active_cases['machine_display'] == selected_code].iloc[0]

        with col_info:
            c1, c2, c3 = st.columns(3)
            origin = case_info.get('origin_branch') or case_info['branch']
            c1.metric("Nguồn gốc", origin)
            c2.metric("Trạng thái", case_info['status'])
            c3.metric("Người giữ", case_info.get('receiver_name') or "---")

        # Form cập nhật tiến độ
        with st.expander(f"⚙️ Form xử lý kỹ thuật: {selected_code}", expanded=True):
            col_left, col_right = st.columns([1, 1])
            with col_left:
                st.markdown("##### 📍 Vận hành")
                try:
                    curr_idx = STATUS_OPTIONS.index(case_info['status'])
                except:
                    curr_idx = 0
                new_st = st.selectbox("Trạng thái mới:", STATUS_OPTIONS, index=curr_idx)
                staff = st.text_input("Nhân viên thực hiện:", value=case_info.get('receiver_name', ""), placeholder="Tên thợ / Điều phối...")
                conf_date = st.date_input("Ngày xác nhận sửa", datetime.now())

            with col_right:
                st.markdown("##### 🛠️ Chi tiết kỹ thuật")
                actual_reason = st.text_input("Lý do hỏng thực tế:", value=case_info.get('issue_reason', ""))
                current_comp = case_info.get('compensation') if pd.notnull(case_info.get('compensation')) else 0
                actual_cost = st.number_input("Chi phí thực tế (VNĐ):", min_value=0, value=int(current_comp), step=10000)
                
            note_text = st.text_area("Ghi chú tiến độ:", placeholder="Nhập tình trạng chi tiết hoặc linh kiện đang chờ...")
            
            if st.button("💾 Lưu thay đổi vào hệ thống", type="primary", use_container_width=True):
                if not staff:
                    st.warning("⚠️ Vui lòng nhập tên nhân viên để đảm bảo Audit Log!")
                else:
                    with st.spinner("Đang đồng bộ dữ liệu..."):
                        update_payload = {
                            "status": new_st,
                            "receiver_name": staff,
                            "note": note_text,
                            "issue_reason": actual_reason,
                            "compensation": float(actual_cost),
                            "confirmed_date": conf_date.isoformat(),
                            "updated_at": datetime.now().isoformat()
                        }
                        try:
                            supabase.table("repair_cases").update(update_payload).eq("id", case_info['id']).execute()
                            st.toast(f"✅ Đã cập nhật máy {selected_code} thành công!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Lỗi Database: {str(e)}")

    # ==========================================
    # 4. PHẦN TRA CỨU LỊCH SỬ THIẾT BỊ
    # ==========================================
    if selected_code:
        st.divider()
        st.subheader(f"🔍 Tra cứu lịch sử: {selected_code}")
        
        df_machine = df[df['machine_display'] == selected_code].copy()
        
        m_col1, m_col2 = st.columns(2)
        m_col1.info(f"📍 Chi nhánh hiện tại: **{df_machine['branch'].iloc[0]}**")
        total_cost = df_machine['compensation'].sum() if 'compensation' in df_machine.columns else 0
        m_col2.error(f"💸 Tổng chi phí tích lũy: **{total_cost:,.0f} đ**")

        st.dataframe(
            df_machine.sort_values('confirmed_date', ascending=False)[
                ['confirmed_date', 'customer_name', 'issue_reason', 'compensation', 'note']
            ], 
            column_config={
                "compensation": st.column_config.NumberColumn("Chi phí bồi thường", format="%d đ"),
                "confirmed_date": "Ngày xác nhận",
                "customer_name": "Tên khách hàng",
                "issue_reason": "Lý do hư hỏng",
                "note": "Ghi chú kỹ thuật"
            },
            use_container_width=True,
            hide_index=True
        )

def render_admin_panel(df_db):
    st.title("📥 Quản Trị & Điều Hành Hệ Thống")

    ad_sub1, ad_sub2, ad_sub3, ad_sub4 = st.tabs([
        "➕ NHẬP LIỆU MỚI", 
        "🚚 ĐỐI SOÁT VẬN HÀNH",
        "🏢 PHÂN TÍCH CHI NHÁNH", 
        "📜 NHẬT KÝ HỆ THỐNG"
    ])

    # --- SUB-TAB 1: NHẬP LIỆU ---
    with ad_sub1:
        c_up, c_man = st.columns([1, 1.2])
        
        with c_up:
            st.subheader("📂 Import dữ liệu lớn")
            up_file = st.file_uploader("Tải file CSV (Theo mẫu chuẩn)", type="csv")
            if up_file:
                df_up = pd.read_csv(up_file)
                st.dataframe(df_up.head(5), use_container_width=True)
                if st.button("🚀 Thực hiện Batch Import", use_container_width=True):
                    st.warning("Tính năng đang kiểm tra cấu trúc file...")
                    st.cache_data.clear()

        with c_man:
            st.subheader("✍️ Nhập ca đơn lẻ")
            with st.form("f_manual_admin", clear_on_submit=True):
                m_code_raw = st.text_input("Mã máy *", placeholder="Ví dụ: 3101, 892...")
                f_b = st.selectbox("Chi nhánh gửi máy *", ["Miền Bắc", "Miền Trung", "Miền Nam"])
                f_c = st.text_input("Tên khách hàng")
                
                # Cặp trường bổ sung theo yêu cầu
                f_date = st.date_input("Ngày xác nhận lỗi", datetime.now())
                f_note = st.text_area("Ghi chú ban đầu", placeholder="Mô tả sơ bộ lỗi khi nhận máy...")

                f_cost = st.number_input("Chi phí dự kiến (VNĐ)", min_value=0, step=10000)
                f_reason = st.text_input("Lý do hỏng / Nội dung sửa *")
                
                if st.form_submit_button("🚀 Lưu ca sửa chữa mới", use_container_width=True):
                    if not m_code_raw or not f_reason:
                        st.error("⚠️ Mã máy và Lý do hỏng là bắt buộc!")
                    else:
                        with st.spinner("Đang khởi tạo ca sửa chữa..."):
                            m_code = m_code_raw.strip().upper()
                            # 1. Xử lý logic Máy (Machines)
                            res_m = supabase.table("machines").select("id").eq("machine_code", m_code).execute()
                            m_uuid = res_m.data[0]['id'] if res_m.data else supabase.table("machines").insert({"machine_code": m_code}).execute().data[0]['id']

                            # 2. Tạo record hoàn chỉnh
                            new_record = {
                                "machine_id": m_uuid,
                                "branch": f_b,
                                "origin_branch": f_b,
                                "customer_name": f_c,
                                "issue_reason": f_reason,
                                "compensation": float(f_cost),
                                "confirmed_date": f_date.isoformat(),
                                "note": f_note,
                                "status": "1. Chờ nhận"
                            }
                            
                            if insert_new_repair(new_record):
                                st.success(f"✅ Đã khởi tạo thành công ca sửa chữa cho máy {m_code}!")
                                st.cache_data.clear()
                                st.rerun()

    # --- SUB-TAB 2: ĐỐI SOÁT ---
    with ad_sub2:
        render_status_management(df_db)

    # --- SUB-TAB 3: CHI NHÁNH ---
    with ad_sub3:
        st.subheader("🏢 Phân tích Hiệu suất theo Vùng")
        if df_db.empty:
            st.info("Chưa có dữ liệu vùng miền.")
        else:
            sel_b = st.selectbox("Chọn chi nhánh:", sorted(df_db["branch"].unique()))
            df_b = df_db[df_db["branch"] == sel_b]
            
            v1, v2 = st.columns([1, 1])
            with v1:
                summary = df_b.groupby("machine_display").agg(
                    ca=("id", "count"),
                    phi=("CHI_PHÍ", "sum")
                ).sort_values("ca", ascending=False).reset_index()
                st.write(f"Báo cáo chi tiết: {sel_b}")
                st.dataframe(summary, use_container_width=True, hide_index=True)
            with v2:
                fig = px.pie(summary.head(8), values='ca', names='machine_display', 
                           hole=0.4, title="Cơ cấu hỏng hóc (Top 8)")
                st.plotly_chart(fig, use_container_width=True)

    # --- SUB-TAB 4: AUDIT LOG ---
    with ad_sub4:
        st.subheader("📜 Nhật ký hệ thống (Audit Logs)")
        try:
            res_audit = supabase.table("audit_logs").select("*").order("created_at", desc=True).limit(30).execute()
            if res_audit.data:
                st.dataframe(pd.DataFrame(res_audit.data), use_container_width=True)
            else:
                st.info("Nhật ký đang trống.")
        except:
            st.caption("Yêu cầu bảng 'audit_logs' để kích hoạt tính năng này.")
