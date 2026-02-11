import streamlit as st
import pandas as pd
from datetime import datetime
from core.database import supabase
from services.repair_service import insert_new_repair

def render_admin_panel(df_db):
    st.title("📥 Quản Trị & Điều Hành Hệ Thống")

    # Khởi tạo các Sub-tabs
    ad_sub1, ad_sub2, ad_sub3 = st.tabs([
        "➕ NHẬP LIỆU", 
        "🏢 CHI NHÁNH", 
        "📜 AUDIT LOG"
    ])

    # ---------------------------------------------------------
    # SUB-TAB 1: NHẬP LIỆU (CSV & MANUAL)
    # ---------------------------------------------------------
    with ad_sub1:
        c_up, c_man = st.columns([1, 1])

        # ---------- PHẦN A: CSV IMPORT ----------
        with c_up:
            st.subheader("📂 Import dữ liệu hàng loạt")
            st.info("Yêu cầu file CSV có các cột: machine_id, branch, customer_name, confirmed_date, issue_reason, compensation")

            up_file = st.file_uploader("Chọn file CSV", type="csv", key="csv_admin_enterprise")

            if up_file:
                try:
                    df_up = pd.read_csv(up_file)
                    expected_cols = {"machine_id", "branch", "customer_name", "confirmed_date", "issue_reason", "compensation"}
                    
                    if not expected_cols.issubset(df_up.columns):
                        st.error(f"❌ File thiếu cột! Cần có đủ: {expected_cols}")
                    else:
                        st.success(f"✅ Đã nhận diện {len(df_up)} dòng dữ liệu")
                        st.dataframe(df_up.head(3), use_container_width=True)

                        if st.button(f"🚀 Xác nhận Import vào Hệ thống", use_container_width=True, type="primary"):
                            with st.spinner("Đang xử lý dữ liệu..."):
                                records = []
                                audits = []
                                
                                for _, r in df_up.iterrows():
                                    # Logic xử lý mã máy: Map hoặc Tạo mới
                                    m_code = str(r["machine_id"]).strip().upper()
                                    res_m = supabase.table("machines").select("id").eq("machine_code", m_code).execute()
                                    
                                    if res_m.data:
                                        m_uuid = res_m.data[0]['id']
                                    else:
                                        new_m = supabase.table("machines").insert({"machine_code": m_code}).execute()
                                        m_uuid = new_m.data[0]['id']

                                    record = {
                                        "machine_id": m_uuid,
                                        "branch": r["branch"],
                                        "customer_name": r["customer_name"],
                                        "confirmed_date": pd.to_datetime(r["confirmed_date"]).isoformat(),
                                        "issue_reason": r["issue_reason"],
                                        "compensation": float(r["compensation"]),
                                        "source": "csv",
                                        "created_by": "admin_user"
                                    }
                                    records.append(record)

                                # Insert theo lô để tối ưu tốc độ
                                supabase.table("repair_cases").insert(records).execute()
                                
                                # Lưu Audit Log chung cho đợt import
                                supabase.table("audit_logs").insert({
                                    "action": "IMPORT_CSV",
                                    "table_name": "repair_cases",
                                    "actor": "admin_user",
                                    "payload": f"Import thành công {len(records)} dòng từ file CSV",
                                    "created_at": datetime.now().isoformat()
                                }).execute()

                                st.success(f"✅ Đã nhập thành công {len(records)} bản ghi!")
                                st.cache_data.clear()
                                st.rerun()
                except Exception as e:
                    st.error(f"❌ Lỗi xử lý CSV: {e}")

        # ---------- PHẦN B: MANUAL ENTRY ----------
        with c_man:
            st.subheader("✍️ Nhập ca đơn lẻ")
            with st.form("f_manual_entry", clear_on_submit=True):
                m1, m2 = st.columns(2)
                with m1:
                    f_machine = st.text_input("Mã máy * (VD: 1641)")
                    f_branch = st.selectbox("Chi nhánh *", ["Miền Bắc", "Miền Trung", "Miền Nam"])
                    f_cost = st.number_input("Chi phí (VNĐ)", min_value=0, step=10000)
                with m2:
                    f_customer = st.text_input("Khách hàng *")
                    f_confirmed = st.date_input("Ngày xác nhận")
                    f_reason = st.text_input("Nguyên nhân *")
                
                f_note = st.text_area("Ghi chú chi tiết")

                if st.form_submit_button("💾 Lưu bản ghi", use_container_width=True):
                    if not f_machine or not f_customer:
                        st.warning("⚠️ Vui lòng điền các trường dấu (*)")
                    else:
                        try:
                            # Tương tự CSV: Xử lý Machine UUID
                            m_code = f_machine.strip().upper()
                            res_m = supabase.table("machines").select("id").eq("machine_code", m_code).execute()
                            m_uuid = res_m.data[0]['id'] if res_m.data else supabase.table("machines").insert({"machine_code": m_code}).execute().data[0]['id']

                            new_record = {
                                "machine_id": m_uuid,
                                "branch": f_branch,
                                "customer_name": f_customer,
                                "confirmed_date": f_confirmed.isoformat(),
                                "issue_reason": f_reason,
                                "compensation": float(f_cost),
                                "note": f_note,
                                "source": "manual",
                                "created_by": "admin_user"
                            }
                            
                            insert_new_repair(new_record)
                            
                            # Lưu Audit Log
                            supabase.table("audit_logs").insert({
                                "action": "INSERT",
                                "table_name": "repair_cases",
                                "actor": "admin_user",
                                "payload": f"Nhập tay máy {m_code}, chi phí {f_cost}",
                                "created_at": datetime.now().isoformat()
                            }).execute()

                            st.success("✅ Đã lưu dữ liệu!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Lỗi DB: {e}")

    # ---------------------------------------------------------
    # SUB-TAB 2: CHI NHÁNH
    # ---------------------------------------------------------
    with ad_sub2:
        st.subheader("🏢 Hiệu suất vận hành theo Chi nhánh")
        if df_db.empty:
            st.info("Chưa có dữ liệu để phân tích chi nhánh.")
        else:
            sel_b = st.selectbox("Chọn chi nhánh để xem chi tiết", sorted(df_db["branch"].unique()))
            df_b = df_db[df_db["branch"] == sel_b]
            
            c1, c2 = st.columns(2)
            with c1:
                # Dùng machine_display (Mã máy thân thiện)
                view = df_b.groupby("machine_display").agg(
                    so_ca=("id", "count"),
                    tong_chi_phi=("CHI_PHÍ", "sum")
                ).sort_values("so_ca", ascending=False).reset_index()
                st.write(f"Danh sách máy hỏng tại {sel_b}")
                st.dataframe(view, use_container_width=True, hide_index=True)
            with c2:
                fig_pie = px.pie(view.head(5), values='so_ca', names='machine_display', title="Top 5 máy hỏng nhiều nhất")
                st.plotly_chart(fig_pie, use_container_width=True)

    # ---------------------------------------------------------
    # SUB-TAB 3: AUDIT LOG
    # ---------------------------------------------------------
    with ad_sub3:
        st.subheader("📜 Nhật ký hệ thống (100 hoạt động gần nhất)")
        if st.button("🔄 Refresh Nhật ký"):
            st.rerun()

        try:
            res_audit = supabase.table("audit_logs").select("*").order("created_at", desc=True).limit(100).execute()
            if res_audit.data:
                df_audit = pd.DataFrame(res_audit.data)
                df_audit['created_at'] = pd.to_datetime(df_audit['created_at']).dt.strftime('%H:%M:%S %d-%m-%Y')
                st.dataframe(
                    df_audit[['created_at', 'actor', 'action', 'payload']], 
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Nhật ký trống.")
        except Exception as e:
            st.warning("⚠️ Không thể tải Audit Log. Hãy đảm bảo bạn đã tạo bảng 'audit_logs' trên Supabase.")
