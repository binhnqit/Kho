import streamlit as st
import pandas as pd
from datetime import datetime
from core.database import supabase

def render_admin_panel(df_db):
    st.title("📥 Quản Trị & Điều Hành Chi Nhánh")

    ad_sub1, ad_sub2, ad_sub3 = st.tabs([
        "➕ NHẬP LIỆU", 
        "🏢 CHI NHÁNH", 
        "📜 AUDIT LOG"
    ])

    # ---------------------------------------------------------
    # SUB-TAB 1: NHẬP LIỆU
    # ---------------------------------------------------------
    with ad_sub1:
        c_up, c_man = st.columns([5, 5])

        with c_up:
            st.subheader("📂 Import CSV (Enterprise)")
            expected_cols = {"machine_id", "branch", "customer_name", "confirmed_date", "issue_reason", "compensation"}
            up_file = st.file_uploader("Chọn file CSV", type="csv", key="csv_admin_enterprise")

            if up_file:
                try:
                    df_up = pd.read_csv(up_file)
                    missing_cols = expected_cols - set(df_up.columns)
                    if missing_cols:
                        st.error(f"❌ Thiếu cột: {', '.join(missing_cols)}")
                    else:
                        st.success(f"✅ Hợp lệ ({len(df_up)} dòng)")
                        if st.button("🚀 Xác nhận Import", use_container_width=True):
                            # Logic xử lý hàng loạt có thể thêm ở đây
                            st.info("Tính năng import hàng loạt đang tối ưu hóa...")
                except Exception as e:
                    st.error(f"Lỗi: {e}")

        with c_man:
            st.subheader("✍️ Nhập ca sửa chữa đơn lẻ")
            with st.form("f_manual_enterprise", clear_on_submit=True):
                m1, m2 = st.columns(2)
                with m1:
                    f_m_code = st.text_input("Mã máy *").strip().upper()
                    f_branch = st.selectbox("Chi nhánh *", ["Miền Bắc", "Miền Trung", "Miền Nam"])
                    f_cost = st.number_input("Chi phí", min_value=0, step=10000)
                with m2:
                    f_customer = st.text_input("Khách hàng *")
                    f_confirmed = st.date_input("Ngày xác nhận", value=datetime.now())
                    f_reason = st.text_input("Nguyên nhân *")
                
                f_note = st.text_area("Ghi chú")
                submit = st.form_submit_button("💾 Lưu dữ liệu", use_container_width=True)

                if submit:
                    if not f_m_code or not f_customer or not f_reason:
                        st.warning("⚠️ Vui lòng nhập đủ trường (*)")
                    else:
                        try:
                            # 1. Tự động kiểm tra/tạo máy
                            res_m = supabase.table("machines").select("id").eq("machine_code", f_m_code).execute()
                            if res_m.data:
                                m_uuid = res_m.data[0]['id']
                            else:
                                new_m = supabase.table("machines").insert({"machine_code": f_m_code}).execute()
                                m_uuid = new_m.data[0]['id']

                            # 2. Lưu ca sửa chữa
                            record = {
                                "machine_id": m_uuid,
                                "branch": f_branch,
                                "customer_name": f_customer,
                                "confirmed_date": f_confirmed.isoformat(),
                                "received_date": datetime.now().isoformat(),
                                "issue_reason": f_reason,
                                "note": f_note,
                                "compensation": float(f_cost)
                            }
                            supabase.table("repair_cases").insert(record).execute()
                            
                            # 3. Ghi Audit Log
                            supabase.table("audit_logs").insert({
                                "action": "INSERT",
                                "table_name": "repair_cases",
                                "actor": "admin@system",
                                "payload": f"Máy: {f_m_code}, Khách: {f_customer}"
                            }).execute()

                            st.success("✅ Đã lưu thành công!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi DB: {e}")

    # ---------------------------------------------------------
    # SUB-TAB 2: CHI NHÁNH
    # ---------------------------------------------------------
    with ad_sub2:
        st.subheader("🏢 Theo dõi vận hành theo chi nhánh")
        if not df_db.empty:
            sel_b = st.selectbox("Chọn chi nhánh", sorted(df_db["branch"].unique()))
            df_b = df_db[df_db["branch"] == sel_b]
            view = df_b.groupby("machine_display").agg(
                so_ca=("id", "count"), 
                tong_chi_phi=("CHI_PHÍ", "sum")
            ).reset_index().sort_values("so_ca", ascending=False)
            st.dataframe(view, use_container_width=True, hide_index=True)

    # ---------------------------------------------------------
    # SUB-TAB 3: AUDIT LOG
    # ---------------------------------------------------------
    with ad_sub3:
        st.subheader("📜 Nhật ký Audit hệ thống")
        try:
            res_audit = supabase.table("audit_logs").select("*").order("created_at", desc=True).limit(50).execute()
            if res_audit.data:
                st.dataframe(pd.DataFrame(res_audit.data), use_container_width=True)
            else:
                st.info("Chưa có nhật ký.")
        except:
            st.error("Bảng audit_logs chưa sẵn sàng.")
