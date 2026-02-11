import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from core.database import supabase
from services.repair_service import insert_new_repair, update_repair_tracking, STATUS_OPTIONS

def render_status_management(df):
    """
    Giao diện Quản lý luồng máy Nhận - Trả (Đối soát vận hành)
    """
    st.subheader("🚚 Điều phối & Đối soát thiết bị")
    
    # Kiểm tra cột để tránh lỗi KeyError
    required_cols = ['status', 'machine_display', 'branch', 'id']
    for col in required_cols:
        if col not in df.columns:
            st.error(f"❌ Database thiếu cột: {col}. Vui lòng kiểm tra lại Schema.")
            return

    # Chỉ hiện các máy chưa hoàn tất quy trình trả về chi nhánh
    active_cases = df[df['status'] != "6. Đã trả chi nhánh"]
    
    if active_cases.empty:
        st.success("✅ Tuyệt vời! Tất cả máy hỏng đã được xử lý và hoàn trả.")
        return

    # Layout chọn máy
    col_sel, col_info = st.columns([1, 2])
    
    with col_sel:
        selected_code = st.selectbox("🔍 Tìm mã máy / Quét mã:", 
                                   active_cases['machine_display'].unique(),
                                   help="Chọn mã máy để cập nhật tiến độ sửa chữa")
        
    case_info = active_cases[active_cases['machine_display'] == selected_code].iloc[0]

    with col_info:
        # Hiển thị thông tin đối soát nhanh dưới dạng thẻ
        c1, c2, c3 = st.columns(3)
        # Kiểm tra origin_branch, nếu rỗng thì dùng branch mặc định
        origin = case_info.get('origin_branch')
        if pd.isna(origin) or origin == "":
            origin = case_info['branch']
            
        c1.metric("Nguồn gốc", origin)
        c2.metric("Trạng thái", case_info['status'])
        c3.metric("Người giữ", case_info.get('receiver_name', 'Chưa xác nhận'))

    st.divider()
    
    # Form cập nhật tiến độ
    with st.expander(f"🔄 Cập nhật trạng thái cho máy: {selected_code}", expanded=True):
        f_st, f_staff = st.columns(2)
        with f_st:
            # Lấy index hiện tại của trạng thái để selectbox nhảy đúng vị trí (optional)
            try:
                curr_idx = STATUS_OPTIONS.index(case_info['status'])
            except:
                curr_idx = 0
            new_st = st.selectbox("Trạng thái mới:", STATUS_OPTIONS, index=curr_idx)
            
        with f_staff:
            staff = st.text_input("Nhân viên xác nhận (Ký tên):", 
                                 placeholder="Nhập tên người thực hiện...")
        
        note = st.text_area("Ghi chú tiến độ (VD: Hư nguồn, đang chờ linh kiện...):")
        
        if st.button("💾 Xác nhận cập nhật hệ thống", type="primary", use_container_width=True):
            if not staff:
                st.warning("⚠️ Vui lòng ký tên nhân viên để đảm bảo tính đối soát!")
            else:
                with st.spinner("Đang cập nhật..."):
                    res = update_repair_tracking(case_info['id'], new_st, staff, note)
                    if res:
                        st.success(f"✅ Đã chuyển máy {selected_code} sang: {new_st}")
                        st.cache_data.clear()
                        st.rerun()

def render_admin_panel(df_db):
    st.title("📥 Quản Trị & Điều Hành Hệ Thống")

    # Hệ thống Sub-tabs chính của Admin
    ad_sub1, ad_sub2, ad_sub3, ad_sub4 = st.tabs([
        "➕ NHẬP LIỆU", 
        "🚚 ĐỐI SOÁT VẬN HÀNH",
        "🏢 CHI NHÁNH", 
        "📜 AUDIT LOG"
    ])

    # --- SUB-TAB 1: NHẬP LIỆU ---
    with ad_sub1:
        c_up, c_man = st.columns([1, 1])
        
        with c_up:
            st.subheader("📂 Import CSV hàng loạt")
            up_file = st.file_uploader("Chọn file CSV", type="csv", key="admin_csv_up")
            if up_file:
                df_up = pd.read_csv(up_file)
                st.dataframe(df_up.head(5), use_container_width=True)
                if st.button("🚀 Xác nhận Import", use_container_width=True):
                    st.info("Hệ thống đang xử lý hàng loạt...")
                    # Code xử lý import tương tự phần thủ công nhưng chạy vòng lặp
                    st.cache_data.clear()

        with c_man:
            st.subheader("✍️ Nhập ca đơn lẻ")
            with st.form("f_manual_admin", clear_on_submit=True):
                f_m = st.text_input("Mã máy * (VD: 3101)")
                f_b = st.selectbox("Chi nhánh gửi *", ["Miền Bắc", "Miền Trung", "Miền Nam"])
                f_c = st.text_input("Khách hàng")
                f_cost = st.number_input("Chi phí dự kiến (VNĐ)", min_value=0, step=1000)
                f_reason = st.text_input("Lý do hỏng/Nội dung sửa *")
                
                if st.form_submit_button("Lưu ca mới", use_container_width=True):
                    if not f_m or not f_reason:
                        st.error("⚠️ Vui lòng nhập Mã máy và Lý do hỏng")
                    else:
                        # 1. Xử lý lấy UUID máy từ mã máy (machine_code)
                        m_code = f_m.strip().upper()
                        res_m = supabase.table("machines").select("id").eq("machine_code", m_code).execute()
                        
                        if res_m.data:
                            m_uuid = res_m.data[0]['id']
                        else:
                            # Nếu máy mới hoàn toàn, tạo luôn trong danh mục
                            new_m = supabase.table("machines").insert({"machine_code": m_code}).execute()
                            m_uuid = new_m.data[0]['id']

                        # 2. Tạo record ca sửa chữa
                        new_record = {
                            "machine_id": m_uuid,
                            "branch": f_b,
                            "origin_branch": f_b, # Đối soát nguồn gốc
                            "customer_name": f_c,
                            "issue_reason": f_reason,
                            "compensation": float(f_cost),
                            "status": "1. Chờ nhận", # Mặc định bước 1
                            "confirmed_date": datetime.now().isoformat()
                        }
                        
                        success = insert_new_repair(new_record)
                        if success:
                            st.success(f"✅ Đã thêm mới ca sửa chữa cho máy {m_code}")
                            st.cache_data.clear()
                            st.rerun()

    # --- SUB-TAB 2: ĐỐI SOÁT VẬN HÀNH ---
    with ad_sub2:
        render_status_management(df_db)

    # --- SUB-TAB 3: CHI NHÁNH ---
    with ad_sub3:
        st.subheader("🏢 Hiệu suất vận hành theo Chi nhánh")
        if df_db.empty:
            st.info("Chưa có dữ liệu để phân tích chi nhánh.")
        else:
            sel_b = st.selectbox("Chọn chi nhánh để xem chi tiết", sorted(df_db["branch"].unique()))
            df_b = df_db[df_db["branch"] == sel_b]
            
            c1, c2 = st.columns(2)
            with c1:
                view = df_b.groupby("machine_display").agg(
                    so_ca=("id", "count"),
                    tong_chi_phi=("CHI_PHÍ", "sum")
                ).sort_values("so_ca", ascending=False).reset_index()
                st.write(f"Danh sách máy hỏng tại {sel_b}")
                st.dataframe(view, use_container_width=True, hide_index=True)
            with c2:
                fig_pie = px.pie(view.head(5), values='so_ca', names='machine_display', 
                                title="Top 5 máy hỏng nhiều nhất",
                                color_discrete_sequence=px.colors.sequential.RdBu)
                st.plotly_chart(fig_pie, use_container_width=True)

    # --- SUB-TAB 4: AUDIT LOG ---
    with ad_sub4:
        st.subheader("📜 Nhật ký hệ thống")
        try:
            res_audit = supabase.table("audit_logs").select("*").order("created_at", desc=True).limit(50).execute()
            if res_audit.data:
                df_audit = pd.DataFrame(res_audit.data)
                st.dataframe(df_audit, use_container_width=True)
            else:
                st.info("Chưa có nhật ký hoạt động.")
        except:
            st.caption("Tính năng Audit Log yêu cầu bảng 'audit_logs' trên Database.")
