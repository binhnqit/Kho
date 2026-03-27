import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import numpy as np
from core.database import supabase
from services.repair_service import insert_new_repair, STATUS_OPTIONS

# ==========================================
# 1. HÀM PHỤ TRỢ: ĐỐI SOÁT CHI TIẾT
# ==========================================
def render_enterprise_tracking(df_to_track):
    st.markdown("#### 🔍 Đối soát & Tra cứu nhanh")

    # --- CHỨC NĂNG TÌM KIẾM ---
    search_query = st.text_input("🔎 Tìm nhanh theo Mã máy hoặc Tên khách hàng:", 
                                placeholder="Nhập mã máy (vd: 3101) hoặc tên khách...", 
                                key="search_ent")
    
    # Thực hiện lọc dựa trên tìm kiếm
    df_final = df_to_track.copy()
    if search_query:
        df_final = df_final[
            df_final['machine_display'].str.contains(search_query, case=False, na=False) |
            df_final['customer_name'].str.contains(search_query, case=False, na=False)
        ]

    # Khởi tạo 4 Tab đối soát
    tab_ncc, tab_internal, tab_fixed, tab_returned = st.tabs([
        "🏭 Đang gửi NCC", 
        "🛠️ Đang sửa nội bộ",
        "✅ Đã sửa - Chờ trả", 
        "🚚 Đã trả chi nhánh"
    ])

    # --- TAB 1: GỬI NCC ---
    with tab_ncc:
        df_ncc = df_final[df_final['status'].str.contains("4.", na=False)].copy()
        if not df_ncc.empty:
            df_ncc['confirmed_date'] = pd.to_datetime(df_ncc['confirmed_date'], errors='coerce')
            df_ncc = df_ncc.dropna(subset=['confirmed_date'])
            if not df_ncc.empty:
                # Tính số ngày tồn an toàn (Tránh AttributeError .dt)
                delta = pd.to_datetime(datetime.now().date()) - pd.to_datetime(df_ncc['confirmed_date'].dt.date)
                df_ncc['days'] = delta.dt.days
                st.warning(f"⚠️ Có {len(df_ncc)} máy đang nằm tại NCC.")
                st.dataframe(
                    df_ncc[['machine_display', 'days', 'customer_name', 'branch', 'receiver_name']], 
                    column_config={
                        "machine_display": "Mã máy",
                        "days": st.column_config.NumberColumn("Số ngày tồn", format="%d ngày ⏳"),
                        "customer_name": "Khách hàng",
                        "branch": "Chi nhánh",
                        "receiver_name": "Người giữ/NCC"
                    },
                    use_container_width=True, hide_index=True
                )
        else:
            st.info("Không tìm thấy máy nào đang gửi NCC.")

    # --- TAB 2: ĐANG SỬA NỘI BỘ ---
    with tab_internal:
        df_internal = df_final[df_final['status'].str.contains("3.", na=False)].copy()
        if not df_internal.empty:
            st.info(f"🔧 Có {len(df_internal)} máy đang được kỹ thuật nội bộ xử lý.")
            st.dataframe(
                df_internal[['machine_display', 'customer_name', 'branch', 'receiver_name', 'issue_reason']], 
                column_config={"machine_display": "Mã máy", "customer_name": "Khách hàng", "receiver_name": "Kỹ thuật"},
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Hiện không có máy nào đang sửa nội bộ.")

    # --- TAB 3: CHỜ TRẢ ---
    with tab_fixed:
        df_ready = df_final[df_final['status'].str.contains("5.", na=False)].copy()
        if not df_ready.empty:
            st.success(f"📦 Có {len(df_ready)} máy đã xong, chờ đóng gói.")
            st.dataframe(
                df_ready[['machine_display', 'customer_name', 'branch', 'compensation', 'note']], 
                column_config={"compensation": st.column_config.NumberColumn("Chi phí", format="%d đ")},
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Không tìm thấy máy nào đang chờ trả.")

    # --- TAB 4: ĐÃ TRẢ ---
    with tab_returned:
        df_ret = df_final[df_final['status'].str.contains("6.", na=False)].copy()
        if not df_ret.empty:
            st.write("Dữ liệu 15 ca hoàn tất gần nhất:")
            df_ret['updated_at_fmt'] = pd.to_datetime(df_ret['updated_at']).dt.strftime('%d/%m/%Y %H:%M')
            st.dataframe(
                df_ret.sort_values('updated_at', ascending=False).head(15)[
                    ['machine_display', 'customer_name', 'branch', 'receiver_name', 'updated_at_fmt', 'compensation']
                ], 
                column_config={
                    "updated_at_fmt": "Ngày trả",
                    "compensation": st.column_config.NumberColumn("Chi phí", format="%d đ")
                },
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Không tìm thấy dữ liệu máy đã trả.")

# ==========================================
# 2. HÀM PHỤ TRỢ: QUẢN TRỊ NÂNG CAO (SỬA/XÓA)
# ==========================================
def render_advanced_management(df):
    st.markdown("### ⚙️ Điều chỉnh dữ liệu hệ thống")
    if df.empty:
        st.info("Chưa có dữ liệu.")
        return

    all_cases = df.sort_values('updated_at', ascending=False)
    target_id = st.selectbox(
        "🎯 Chọn bản ghi cần xử lý (ID - Mã máy - Khách):",
        options=all_cases['id'].tolist(),
        format_func=lambda x: f"{x[:8]}... | {all_cases[all_cases['id']==x]['machine_display'].values[0]} | {all_cases[all_cases['id']==x]['customer_name'].values[0]}"
    )
    
    case_data = all_cases[all_cases['id'] == target_id].iloc[0]

    st.warning(f"Đang can thiệp máy: **{case_data['machine_display']}** | Chi nhánh: **{case_data['branch']}**")

    a_tab1, a_tab2, a_tab3 = st.tabs(["📝 Sửa thông tin", "🔄 Luân chuyển chi nhánh", "🗑️ Xóa"])

    with a_tab1:
        with st.form("adv_edit_form"):
            new_cust = st.text_input("Tên khách hàng:", value=case_data['customer_name'])
            new_reason = st.text_area("Lý do hỏng:", value=case_data.get('issue_reason', ""))
            if st.form_submit_button("Lưu thay đổi"):
                supabase.table("repair_cases").update({
                    "customer_name": new_cust, "issue_reason": new_reason, "updated_at": datetime.now().isoformat()
                }).eq("id", target_id).execute()
                st.success("Đã cập nhật!"); st.cache_data.clear(); st.rerun()

    with a_tab2:
        branches = ["Miền Bắc", "Miền Trung", "Miền Nam"]
        new_b = st.selectbox("Chuyển sang chi nhánh:", branches, index=branches.index(case_data['branch']) if case_data['branch'] in branches else 0)
        if st.button("Xác nhận chuyển chi nhánh"):
            supabase.table("repair_cases").update({
                "branch": new_b, "origin_branch": new_b, "updated_at": datetime.now().isoformat()
            }).eq("id", target_id).execute()
            st.success("Đã luân chuyển!"); st.cache_data.clear(); st.rerun()

    with a_tab3:
        st.error("Hành động này không thể hoàn tác!")
        if st.button("🔥 XÓA VĨNH VIỄN BẢN GHI NÀY"):
            supabase.table("repair_cases").delete().eq("id", target_id).execute()
            st.success("Đã xóa!"); st.cache_data.clear(); st.rerun()

# ==========================================
# 3. GIAO DIỆN QUẢN LÝ TRẠNG THÁI (DASHBOARD)
# ==========================================
def render_status_management(df):
    st.markdown("### 📊 Tổng quan vận hành")
    list_branches = ["Tất cả"] + sorted(df['branch'].unique().tolist())
    selected_region = st.selectbox("📍 Lọc theo khu vực đối soát:", list_branches, index=0)
    df_filtered = df if selected_region == "Tất cả" else df[df['branch'] == selected_region]

    # Metrics
    status_counts = df_filtered['status'].value_counts().reindex(STATUS_OPTIONS, fill_value=0)
    cols = st.columns(len(STATUS_OPTIONS))
    for i, status in enumerate(STATUS_OPTIONS):
        label = status.split(". ")[1]
        cols[i].metric(label, f"{status_counts[status]} máy")

    st.divider()
    render_enterprise_tracking(df_filtered) # Gọi hàm đối soát
    st.divider()

    # Form cập nhật trạng thái
    st.markdown("### 🚚 Cập nhật trạng thái máy")
    active_cases = df_filtered[df_filtered['status'] != "6. Đã trả chi nhánh"]
    if not active_cases.empty:
        selected_code = st.selectbox("🔍 Chọn máy cập nhật:", active_cases['machine_display'].unique(), key="up_sel")
        case = active_cases[active_cases['machine_display'] == selected_code].iloc[0]
        
        with st.form("update_status_form"):
            c1, c2 = st.columns(2)
            new_st = c1.selectbox("Trạng thái mới:", STATUS_OPTIONS, index=STATUS_OPTIONS.index(case['status']))
            new_staff = c2.text_input("Nhân viên xử lý:", value=case.get('receiver_name', ""))
            new_cost = st.number_input("Chi phí thực tế (đ):", value=int(case.get('compensation', 0)))
            new_note = st.text_area("Ghi chú tiến độ:")
            
            if st.form_submit_button("Cập nhật hệ thống"):
                payload = {
                    "status": new_st, "receiver_name": new_staff, "compensation": float(new_cost),
                    "note": new_note, "updated_at": datetime.now().isoformat(),
                    "confirmed_date": datetime.now().date().isoformat()
                }
                supabase.table("repair_cases").update(payload).eq("id", case['id']).execute()
                st.success("Thành công!"); st.cache_data.clear(); st.rerun()

# ==========================================
# 4. HÀM CHÍNH: RENDER ADMIN PANEL
# ==========================================
def render_admin_panel(df_db):
    st.title("📥 Quản Trị Hệ Thống")

    ad_tabs = st.tabs(["➕ NHẬP LIỆU", "🚚 ĐỐI SOÁT", "🏢 PHÂN TÍCH", "📜 AUDIT", "⚙️ QUẢN TRỊ NÂNG CAO"])

    with ad_tabs[0]: # NHẬP LIỆU
        with st.form("manual_entry"):
            st.subheader("✍️ Nhập ca sửa chữa mới")
            m_code = st.text_input("Mã máy *").strip().upper()
            f_branch = st.selectbox("Chi nhánh *", ["Miền Bắc", "Miền Trung", "Miền Nam"])
            f_cust = st.text_input("Tên khách hàng")
            f_reason = st.text_input("Lý do hỏng *")
            if st.form_submit_button("Lưu ca mới"):
                if m_code and f_reason:
                    # Logic lấy machine_id
                    res_m = supabase.table("machines").select("id").eq("machine_code", m_code).execute()
                    m_id = res_m.data[0]['id'] if res_m.data else supabase.table("machines").insert({"machine_code": m_code}).execute().data[0]['id']
                    
                    new_rec = {
                        "machine_id": m_id, "branch": f_branch, "origin_branch": f_branch,
                        "customer_name": f_cust, "issue_reason": f_reason, "status": "1. Chờ nhận",
                        "confirmed_date": datetime.now().date().isoformat()
                    }
                    supabase.table("repair_cases").insert(new_rec).execute()
                    st.success("Đã thêm!"); st.cache_data.clear(); st.rerun()
                else: st.error("Thiếu thông tin bắt buộc!")

    with ad_tabs[1]: # ĐỐI SOÁT
        render_status_management(df_db)

    with ad_tabs[2]: # PHÂN TÍCH
        if not df_db.empty:
            fig = px.pie(df_db, names='status', title="Tỷ lệ trạng thái thiết bị toàn hệ thống")
            st.plotly_chart(fig, use_container_width=True)

    with ad_tabs[3]: # AUDIT
        st.write("Nhật ký 30 thao tác gần nhất:")
        res = supabase.table("repair_cases").select("machine_display, status, updated_at").order("updated_at", desc=True).limit(30).execute()
        st.table(res.data)

    with ad_tabs[4]: # QUẢN TRỊ NÂNG CAO
        render_advanced_management(df_db)
