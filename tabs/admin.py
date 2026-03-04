import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from core.database import supabase
from services.repair_service import insert_new_repair, update_repair_tracking, STATUS_OPTIONS

def render_status_management(df):
    """
    Giao diện Quản lý luồng máy Nhận - Trả (Đối soát vận hành chuyên nghiệp)
    """
    st.markdown("### 🚚 Điều phối & Đối soát thiết bị")
    
    # 1. Kiểm tra tính toàn vẹn của dữ liệu
    required_cols = ['status', 'machine_display', 'branch', 'id', 'issue_reason', 'note']
    if not all(col in df.columns for col in required_cols):
        st.error("❌ Cấu trúc Database không tương thích. Vui lòng cập nhật Schema.")
        return

    # Chỉ lọc các ca đang trong quá trình xử lý
    active_cases = df[df['status'] != "6. Đã trả chi nhánh"]
    
    if active_cases.empty:
        st.success("✅ Hệ thống sạch sẽ! Tất cả thiết bị đã được hoàn trả chi nhánh.")
        return

    # 2. Giao diện chọn thiết bị thông minh
    col_sel, col_info = st.columns([1, 1.5])
    
    with col_sel:
        selected_code = st.selectbox(
            "🔍 Tìm mã máy / Quét mã:", 
            active_cases['machine_display'].unique(),
            help="Hệ thống tự động lọc các máy đang nằm tại kho tổng hoặc NCC"
        )
        
    case_info = active_cases[active_cases['machine_display'] == selected_code].iloc[0]

    with col_info:
        c1, c2, c3 = st.columns(3)
        origin = case_info.get('origin_branch') or case_info['branch']
        c1.metric("Nguồn gốc", origin)
        c2.metric("Trạng thái", case_info['status'])
        c3.metric("Người giữ", case_info.get('receiver_name') or "---")

    st.markdown("---")
    
    # 3. Form cập nhật tiến độ & Tình trạng hư hỏng thực tế
    with st.expander(f"⚙️ Cập nhật tiến độ & Kỹ thuật cho: {selected_code}", expanded=True):
        # Chia làm 2 khu vực: Trạng thái & Thông tin kỹ thuật thực tế
        col_left, col_right = st.columns([1, 1])
        
        with col_left:
            st.markdown("##### 📍 Trạng thái vận hành")
            try:
                curr_idx = STATUS_OPTIONS.index(case_info['status'])
            except:
                curr_idx = 0
            new_st = st.selectbox("Trạng thái mới:", STATUS_OPTIONS, index=curr_idx)
            staff = st.text_input("Nhân viên thực hiện:", placeholder="Tên thợ / Điều phối...")
            conf_date = st.date_input("Ngày xác nhận sửa", datetime.now())

        with col_right:
            st.markdown("##### 🛠️ Tình trạng hư hỏng thực tế")
            # Cho phép cập nhật lại lý do hỏng nếu kiểm tra thực tế khác với lúc nhập ca
            actual_reason = st.text_input("Lý do hỏng thực tế:", value=case_info['issue_reason'])
            # Cập nhật chi phí thực tế (bồi thường)
            actual_cost = st.number_input("Chi phí thực tế (VNĐ):", 
                                          min_value=0.0, 
                                          value=float(case_info.get('CHI_PHÍ', 0) or case_info.get('compensation', 0)),
                                          step=10000.0)
            
        note = st.text_area("Ghi chú tiến độ:", placeholder="Nhập tình trạng chi tiết hoặc linh kiện đang chờ...")
        
        if st.button("💾 Xác nhận cập nhật hệ thống", type="primary", use_container_width=True):
            if not staff:
                st.warning("⚠️ Vui lòng nhập tên nhân viên để đảm bảo tính Audit Log!")
            else:
                with st.spinner("Đang đồng bộ dữ liệu..."):
                    # Cập nhật thông tin vào Database
                    # Lưu ý: Hàm update_repair_tracking cần bổ sung logic cập nhật issue_reason và compensation/CHI_PHÍ
                    update_data = {
                        "status": new_st,
                        "receiver_name": staff,
                        "note": note,
                        "issue_reason": actual_reason,
                        "compensation": actual_cost,
                        "confirmed_date": conf_date.isoformat()
                    }
                    
                    # Gọi API cập nhật
                    res = supabase.table("repairs").update(update_data).eq("id", case_info['id']).execute()
                    
                    if res:
                        st.toast(f"✅ Đã cập nhật máy {selected_code} thành công!")
                        st.cache_data.clear()
                        st.rerun()

    # 4. Tra cứu chi tiết & Lịch sử kỹ thuật của máy đang chọn
    st.divider()
    st.subheader(f"🔍 Tra cứu lịch sử thiết bị: {selected_code}")
    
    # Lọc tất cả các ca trong quá khứ của máy này
    df_machine = df[df['machine_display'] == selected_code].copy()
    
    m_col1, m_col2 = st.columns(2)
    m_col1.info(f"📍 Chi nhánh quản lý: **{df_machine['branch'].iloc[0]}**")
    
    # Tính tổng chi phí tích lũy (Sử dụng cột CHI_PHÍ hoặc compensation tùy schema)
    cost_col = 'CHI_PHÍ' if 'CHI_PHÍ' in df_machine.columns else 'compensation'
    total_cost = df_machine[cost_col].sum()
    m_col2.error(f"💸 Tổng chi phí tích lũy: **{total_cost:,.0f} đ**")

    # Hiển thị bảng lịch sử
    st.dataframe(
        df_machine.sort_values('confirmed_date', ascending=False)[
            ['confirmed_date', 'customer_name', 'issue_reason', cost_col, 'note']
        ], 
        column_config={
            cost_col: st.column_config.NumberColumn("Chi phí", format="%d đ"),
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
