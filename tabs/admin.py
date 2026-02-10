import streamlit as st
from datetime import datetime
from core.database import supabase
from services.repair_service import insert_new_repair

def render_admin_panel():
    st.title("📥 QUẢN TRỊ & NHẬP LIỆU")
    
    # Kiểm tra kết nối database trước khi render nội dung
    if supabase is None:
        st.error("❌ Kết nối Database thất bại. Vui lòng kiểm tra Secrets.")
        return

    st.subheader("✍️ Nhập ca sửa chữa mới")
    
    with st.form("f_manual_repair", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            f_m_code = st.text_input("Mã máy (VD: 1641) *").strip().upper()
            f_branch = st.selectbox("Chi nhánh *", ["Miền Bắc", "Miền Trung", "Miền Nam"])
            f_cost = st.number_input("Chi phí (VNĐ)", min_value=0.0, step=1000.0)
        with col2:
            f_customer = st.text_input("Khách hàng *")
            f_confirmed = st.date_input("Ngày xác nhận", value=datetime.now())
            f_reason = st.text_input("Lý do hỏng *")
            
        f_note = st.text_area("Ghi chú")
        submit = st.form_submit_button("💾 Lưu dữ liệu", use_container_width=True)
        
        if submit:
            if not f_m_code or not f_customer:
                st.warning("Vui lòng điền đủ thông tin.")
            else:
                try:
                    # Tự động map hoặc tạo máy mới
                    res_m = supabase.table("machines").select("id").eq("machine_code", f_m_code).execute()
                    if res_m.data:
                        m_uuid = res_m.data[0]['id']
                    else:
                        new_m = supabase.table("machines").insert({"machine_code": f_m_code}).execute()
                        m_uuid = new_m.data[0]['id']

                    # Lưu bản ghi
                    repair_record = {
                        "machine_id": m_uuid,
                        "branch": f_branch,
                        "customer_name": f_customer,
                        "confirmed_date": f_confirmed.isoformat(),
                        "issue_reason": f_reason,
                        "compensation": float(f_cost),
                        "note": f_note
                    }
                    insert_new_repair(repair_record)
                    st.success("✅ Đã lưu!")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Lỗi: {e}")

    # Phần hiển thị danh sách máy (Lỗi TypeError thường nằm ở đây nếu res_all_m trả về None)
    st.divider()
    with st.expander("📂 Danh mục thiết bị"):
        try:
            res_all = supabase.table("machines").select("machine_code, created_at").execute()
            if res_all.data:
                st.dataframe(pd.DataFrame(res_all.data), use_container_width=True)
        except:
            st.info("Chưa có danh mục máy.")
