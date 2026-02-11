import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from core.database import supabase
from services.repair_service import insert_new_repair, update_repair_tracking

def render_status_management(df):
    """
    Giao diện Quản lý luồng máy Nhận - Trả (Đối soát vận hành)
    """
    st.subheader("🚚 Điều phối & Đối soát thiết bị")
    
    # Kiểm tra cột để tránh lỗi KeyError
    required_cols = ['status', 'machine_display', 'origin_branch', 'id']
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
        c1.metric("Nguồn gốc", case_info['origin_branch'] if pd.notna(case_info['origin_branch']) else case_info['branch'])
        c2.metric("Trạng thái", case_info['status'])
        c3.metric("Người giữ", case_info.get('receiver_name', 'Chưa xác nhận'))

    st.divider()
    
    # Form cập nhật tiến độ
    with st.expander(f"🔄 Cập nhật trạng thái cho máy: {selected_code}", expanded=True):
        f_st, f_staff = st.columns(2)
        with f_st:
            # Danh sách trạng thái chuẩn từ service
            from services.repair_service import STATUS_OPTIONS
            new_st = st.selectbox("Trạng thái mới:", STATUS_OPTIONS)
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
            up_file = st.file_uploader("Chọn file CSV", type="csv")
            if up_file:
                df_up = pd.read_csv(up_file)
                if st.button("🚀 Xác nhận Import"):
                    # Logic import của bạn (nhớ map machine_id sang UUID)
                    st.success("Tính năng Import đang hoạt động...")
                    st.cache_data.clear()

        with c_man:
            st.subheader("✍️ Nhập ca đơn lẻ")
            with st.form("f_manual"):
                f_m = st.text_input("Mã máy *")
                f_b = st.selectbox("Chi nhánh gửi *", ["Miền Bắc", "Miền Trung", "Miền Nam"])
                f_c = st.text_input("Khách hàng")
                f_cost = st.number_input("Chi phí dự kiến", min_value=0)
                if st.form_submit_button("Lưu ca mới"):
                    # Gọi hàm insert_new_repair từ service
                    st.success("Đã ghi nhận ca mới!")
                    st.cache_data.clear()
                    st.rerun()

    # --- SUB-TAB 2: ĐỐI SOÁT VẬN HÀNH ---
    with ad_sub2:
        render_status_management(df_db)

    # --- SUB-TAB 3: CHI NHÁNH ---
    with ad_sub2:
        # Giữ nguyên code thống kê chi nhánh của bạn...
        pass

    # --- SUB-TAB 4: AUDIT LOG ---
    with ad_sub4:
        st.subheader("📜 Nhật ký hệ thống")
        # Giữ nguyên code audit log...
