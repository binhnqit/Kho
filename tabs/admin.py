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
