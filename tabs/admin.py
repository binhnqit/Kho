import streamlit as st
from datetime import datetime
from services.repair_service import insert_new_repair
from core.database import supabase

def render_admin_panel():
    st.title("📥 QUẢN TRỊ & NHẬP LIỆU")
    
    st.subheader("✍️ Nhập ca sửa chữa đơn lẻ")
    
    # Sử dụng form để tối ưu hóa việc load lại trang
    with st.form("f_manual_repair", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            f_m_code = st.text_input("Mã máy (VD: 1641, M001) *").strip().upper()
            f_branch = st.selectbox("Chi nhánh *", ["Miền Bắc", "Miền Trung", "Miền Nam"])
            f_cost = st.number_input("Chi phí bồi thường (VNĐ)", min_value=0.0, step=1000.0)
            
        with col2:
            f_customer = st.text_input("Tên khách hàng *")
            f_confirmed = st.date_input("Ngày xác nhận", value=datetime.now())
            f_reason = st.text_input("Nguyên nhân hỏng *")
            
        f_note = st.text_area("Ghi chú chi tiết")
        
        submit = st.form_submit_button("💾 Lưu dữ liệu vào hệ thống", use_container_width=True)
        
        if submit:
            if not f_m_code or not f_customer or not f_reason:
                st.warning("⚠️ Vui lòng điền đầy đủ các thông tin có dấu (*)")
            else:
                try:
                    # 1. Logic tự động kiểm tra/tạo máy mới
                    res_machine = supabase.table("machines").select("id").eq("machine_code", f_m_code).execute()
                    
                    if res_machine.data:
                        m_uuid = res_machine.data[0]['id']
                    else:
                        # Tạo máy mới nếu chưa tồn tại
                        new_m = supabase.table("machines").insert({"machine_code": f_m_code}).execute()
                        m_uuid = new_m.data[0]['id']
                        st.info(f"💡 Máy '{f_m_code}' chưa có trong danh mục. Đã tự động tạo mới.")

                    # 2. Chuẩn bị bản ghi ca sửa chữa
                    repair_record = {
                        "machine_id": m_uuid,
                        "branch": f_branch,
                        "customer_name": f_customer,
                        "confirmed_date": f_confirmed.isoformat(),
                        "received_date": datetime.now().date().isoformat(),
                        "issue_reason": f_reason,
                        "note": f_note,
                        "compensation": float(f_cost),
                        "is_unrepairable": False
                    }
                    
                    # 3. Gọi service để lưu
                    insert_new_repair(repair_record)
                    
                    st.success(f"✅ Đã lưu thành công ca sửa chữa cho máy {f_m_code}!")
                    st.balloons()
                    
                    # Clear cache để Dashboard cập nhật số liệu mới
                    st.cache_data.clear()
                    
                except Exception as e:
                    st.error(f"❌ Lỗi khi lưu dữ liệu: {e}")

    # Phần quản lý danh mục máy (Tùy chọn thêm)
    st.divider()
    with st.expander("📂 Xem danh sách máy hiện có"):
        res_all_m = supabase.table("machines").select("machine_code, created_at").execute()
        if res_all_m.data:
            st.table(res_all_m.data)
