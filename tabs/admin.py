import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from core.database import supabase
from services.repair_service import insert_new_repair, update_repair_tracking, STATUS_OPTIONS

def render_enterprise_tracking(df_to_track):
    """
    Tính năng đối soát chuyên sâu: Phân loại máy theo các 'điểm nóng' vận hành.
    """
    st.markdown("#### 🔍 Danh sách đối soát nhanh (SLA Control)")
    tab_ncc, tab_fixed, tab_returned = st.tabs([
        "🏭 Đang tại NCC", 
        "✅ Chờ trả chi nhánh", 
        "🚚 Hoàn tất gần đây"
    ])

    with tab_ncc:
        # Lọc trạng thái '4. Gửi nhà cung cấp'
        df_ncc = df_to_track[df_to_track['status'].str.contains("4.", na=False)].copy()
        if not df_ncc.empty:
            df_ncc['days'] = (datetime.now().date() - pd.to_datetime(df_ncc['confirmed_date']).dt.date).dt.days
            st.warning(f"⚠️ Có {len(df_ncc)} máy đang sửa ngoài. Chú ý các ca > 7 ngày.")
            st.dataframe(
                df_ncc[['machine_display', 'days', 'issue_reason', 'receiver_name']], 
                column_config={"days": st.column_config.NumberColumn("Số ngày tồn", format="%d ngày ⏳")},
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Không có máy nào tại NCC.")

    with tab_fixed:
        # Lọc trạng thái '5. Đã sửa xong'
        df_ready = df_to_track[df_to_track['status'].str.contains("5.", na=False)].copy()
        if not df_ready.empty:
            st.success(f"📦 {len(df_ready)} máy đã sẵn sàng để điều phối trả vùng.")
            st.dataframe(
                df_ready[['machine_display', 'branch', 'compensation', 'note']], 
                column_config={"compensation": st.column_config.NumberColumn("Chi phí", format="%d đ")},
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Hiện không có máy chờ trả.")

    with tab_returned:
        df_ret = df_to_track[df_to_track['status'].str.contains("6.", na=False)].head(15)
        st.write("15 ca trả máy gần nhất:")
        st.dataframe(df_ret[['machine_display', 'updated_at', 'receiver_name']], use_container_width=True, hide_index=True)

def render_status_management(df):
    """
    Giao diện Quản lý vận hành tích hợp Enterprise Tracking.
    """
    # 1. BỘ LỌC VÙNG MIỀN (Master Filter cho Tab)
    st.markdown("### 📊 Tổng quan & Đối soát")
    list_branches = ["Tất cả"] + sorted(df['branch'].unique().tolist())
    selected_region = st.selectbox("📍 Chọn vùng đối soát:", list_branches, index=0, key="master_reg_filter")
    
    df_filtered = df if selected_region == "Tất cả" else df[df['branch'] == selected_region]

    # 2. KPI METRICS
    status_counts = df_filtered['status'].value_counts().reindex(STATUS_OPTIONS, fill_value=0).reset_index()
    m_cols = st.columns(len(STATUS_OPTIONS))
    for idx, row in status_counts.iterrows():
        label = row['status'].split(". ")[1] if ". " in row['status'] else row['status']
        m_cols[idx].metric(label, f"{row['count']} máy")

    st.divider()

    # 3. TÍCH HỢP ENTERPRISE TRACKING (Gọi hàm mới ở đây)
    render_enterprise_tracking(df_filtered)

    st.divider()

    # 4. FORM CẬP NHẬT CHI TIẾT
    st.markdown("### ⚙️ Cập nhật tiến độ kỹ thuật")
    active_cases = df_filtered[~df_filtered['status'].str.contains("6.", na=False)]
    
    if active_cases.empty:
        st.success(f"✅ Vùng {selected_region} sạch lưới! Không có máy tồn.")
    else:
        col_sel, col_info = st.columns([1, 1.5])
        with col_sel:
            selected_code = st.selectbox("🔍 Mã máy xử lý:", active_cases['machine_display'].unique())
        
        case_info = active_cases[active_cases['machine_display'] == selected_code].iloc[0]
        
        with col_info:
            c1, c2 = st.columns(2)
            c1.info(f"Nguồn: {case_info.get('origin_branch', 'N/A')}")
            c2.error(f"Hiện tại: {case_info['status']}")

        with st.expander(f"📝 Form cập nhật: {selected_code}", expanded=True):
            f_l, f_r = st.columns(2)
            with f_l:
                new_st = st.selectbox("Trạng thái mới:", STATUS_OPTIONS, index=STATUS_OPTIONS.index(case_info['status']))
                staff = st.text_input("Kỹ thuật viên:", value=case_info.get('receiver_name', ""))
            with f_r:
                reason = st.text_input("Lý do thực tế:", value=case_info.get('issue_reason', ""))
                cost = st.number_input("Chi phí (VNĐ):", value=int(case_info.get('compensation', 0)))
            
            note = st.text_area("Ghi chú tiến độ (Linh kiện, vận chuyển...)")
            
            if st.button("💾 Xác nhận cập nhật hệ thống", type="primary", use_container_width=True):
                if not staff: st.warning("Vui lòng nhập tên người xử lý!")
                else:
                    payload = {
                        "status": new_st, "receiver_name": staff, "issue_reason": reason,
                        "compensation": float(cost), "note": note, "updated_at": datetime.now().isoformat()
                    }
                    supabase.table("repair_cases").update(payload).eq("id", case_info['id']).execute()
                    st.toast(f"✅ Đã cập nhật {selected_code}")
                    st.cache_data.clear()
                    st.rerun()

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
