import streamlit as st
import pandas as pd
import plotly.express as px

            
def render_dashboard(df):
    # 1. KIỂM TRA DỮ LIỆU ĐẦU VÀO
    if df is None or df.empty:
        st.info("💡 Hệ thống hiện chưa có dữ liệu sửa chữa. Vui lòng nạp dữ liệu từ file CSV hoặc nhập thủ công tại Tab 'QUẢN TRỊ HỆ THỐNG'.")
        return

    st.title("📊 BÁO CÁO VẬN HÀNH – DECISION DASHBOARD")

    # 2. ---------- SIDEBAR FILTER ----------
    # 2. ---------- SIDEBAR FILTER ----------
    with st.sidebar:
        st.header("⚙️ BỘ LỌC BÁO CÁO")
        
        # Kiểm tra xem cột NĂM có tồn tại không
        if 'NĂM' not in df.columns:
            st.error("❌ Dữ liệu lỗi: Thiếu cột 'NĂM'. Vui lòng kiểm tra lại hàm xử lý dữ liệu.")
            return # Thoát hàm sớm để không chạy dòng 22 gây lỗi sập app

        # ... (các phần code còn lại giữ nguyên)
        f_mode = st.radio("Chế độ lọc thời gian", ["Tháng / Năm", "Khoảng ngày"])

        if f_mode == "Tháng / Năm":
            # Lấy danh sách Năm và Tháng từ dữ liệu
            y_list = sorted(df['NĂM'].dropna().unique().astype(int), reverse=True)
            sel_y = st.selectbox("Năm", y_list)

            m_list = sorted(df[df['NĂM'] == sel_y]['THÁNG'].dropna().unique().astype(int))
            sel_m = st.selectbox("Tháng", ["Tất cả"] + list(m_list))

            df_view = df[df['NĂM'] == sel_y].copy()
            if sel_m != "Tất cả":
                df_view = df_view[df_view['THÁNG'] == sel_m]
        else:
            # Lọc theo khoảng ngày
            min_date = df['confirmed_dt'].min().date()
            max_date = df['confirmed_dt'].max().date()
            d_range = st.date_input("Chọn khoảng ngày", [min_date, max_date])
            
            if isinstance(d_range, list) and len(d_range) == 2:
                df_view = df[
                    (df['confirmed_dt'].dt.date >= d_range[0]) &
                    (df['confirmed_dt'].dt.date <= d_range[1])
                ].copy()
            else:
                df_view = df.copy()

        st.divider()

        # --- BỘ LỌC CHI NHÁNH (Fixed logic) ---
        if 'branch' in df.columns:
            available_branches = sorted([str(x) for x in df['branch'].dropna().unique()])
        else:
            available_branches = []

        if available_branches:
            sel_branch = st.multiselect(
                "Chi nhánh",
                options=available_branches,
                default=available_branches,
                help="Chọn một hoặc nhiều chi nhánh để xem báo cáo"
            )
            df_view = df_view[df_view['branch'].isin(sel_branch)]
        else:
            st.warning("⚠️ Không tìm thấy cột Chi nhánh.")

    # 3. KIỂM TRA SAU KHI LỌC
    if df_view.empty:
        st.warning("⚠️ Không có dữ liệu phù hợp với bộ lọc bạn chọn. Vui lòng điều chỉnh lại thời gian hoặc chi nhánh.")
        return

    # 4. ---------- KPI LAYER ----------
    # Thiết kế giao diện Dashboard hiện đại
    st.markdown("### 🚀 Chỉ số tổng quan")
    k1, k2, k3, k4 = st.columns(4)
    
    # Tính toán các giá trị KPI
    total_cost = df_view['CHI_PHÍ'].sum()
    total_cases = len(df_view)
    
    # Xử lý trường hợp không có dữ liệu để tránh lỗi idxmax()
    hot_branch = df_view['branch'].value_counts().idxmax() if not df_view['branch'].empty else "N/A"
    risky_machine = df_view['machine_display'].value_counts().idxmax() if not df_view['machine_display'].empty else "N/A"

    k1.metric("💰 Tổng chi phí", f"{total_cost:,.0f} đ")
    k2.metric("🛠️ Tổng số ca", f"{total_cases} ca")
    k3.metric("🏢 Chi nhánh HOT", hot_branch)
    k4.metric("⚠️ Máy rủi ro nhất", risky_machine)

    st.divider()

    # 5. ---------- TREND ANALYSIS ----------
    st.subheader("📈 Xu hướng sự cố theo thời gian")
    trend = (
        df_view.groupby(['NĂM', 'THÁNG'])
        .agg(so_ca=('id', 'count'), chi_phi=('CHI_PHÍ', 'sum'))
        .reset_index()
    )
    # Sắp xếp và tạo label
    trend = trend.sort_values(['NĂM', 'THÁNG'])
    trend['Tháng/Năm'] = trend['THÁNG'].astype(str) + "/" + trend['NĂM'].astype(str)
    
    # Biểu đồ kết hợp (Line + Area)
    fig_trend = px.area(
        trend, x='Tháng/Năm', y='so_ca', 
        markers=True, 
        title="Biểu đồ tần suất sự cố",
        labels={'so_ca': 'Số ca', 'Tháng/Năm': 'Thời gian'},
        color_discrete_sequence=['#FF4B4B']
    )
    fig_trend.update_layout(hovermode="x unified")
    st.plotly_chart(fig_trend, use_container_width=True)

    # 6. ---------- RISK SCORING & ANALYSIS ----------
    st.divider()
    c_left, c_right = st.columns([6, 4])

    with c_left:
        st.subheader("⚠️ Xếp hạng rủi ro thiết bị")
        today = pd.Timestamp.now()
        risk_df = (
            df_view.groupby('machine_display')
            .agg(
                so_ca=('id', 'count'),
                tong_chi_phi=('CHI_PHÍ', 'sum'),
                last_case=('confirmed_dt', 'max'),
                branch=('branch', 'first')
            )
            .reset_index()
        )

        # Tính toán Risk Score
        if not risk_df.empty:
            max_ca = risk_df['so_ca'].max() if risk_df['so_ca'].max() != 0 else 1
            max_cost = risk_df['tong_chi_phi'].max() if risk_df['tong_chi_phi'].max() != 0 else 1
            
            risk_df['freq_score'] = risk_df['so_ca'] / max_ca
            risk_df['cost_score'] = risk_df['tong_chi_phi'] / max_cost
            risk_df['recent_score'] = ((today - risk_df['last_case']).dt.days <= 30).astype(int)
            
            # Trọng số Score
            risk_df['risk_score'] = (0.5 * risk_df['freq_score'] + 0.4 * risk_df['cost_score'] + 0.1 * risk_df['recent_score']).round(2)

            def risk_label(v):
                if v >= 0.75: return "🔴 Cao"
                elif v >= 0.5: return "🟠 Trung bình"
                return "🟢 Thấp"

            risk_df['mức_rủi_ro'] = risk_df['risk_score'].apply(risk_label)
            
            st.dataframe(
                risk_df.sort_values('risk_score', ascending=False).head(10), 
                column_config={
                    "machine_display": "Mã thiết bị",
                    "so_ca": "Số ca",
                    "tong_chi_phi": st.column_config.NumberColumn("Tổng chi phí", format="%d đ"),
                    "risk_score": st.column_config.ProgressColumn("Điểm rủi ro", min_value=0, max_value=1),
                    "mức_rủi_ro": "Trạng thái"
                },
                use_container_width=True,
                hide_index=True
            )

    with c_right:
        st.subheader("🔥 Rủi ro theo Chi nhánh")
        heat = risk_df.groupby('branch')['risk_score'].mean().reset_index()
        fig_heat = px.bar(
            heat, x='risk_score', y='branch', 
            orientation='h',
            color='risk_score', color_continuous_scale='Reds',
            labels={'risk_score': 'Điểm rủi ro TB'}
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    # 7. ---------- DRILL DOWN ----------
    st.divider()
    st.subheader("🔍 Tra cứu chi tiết thiết bị")
    
    # Filter selection
    sel_machine = st.selectbox("Chọn mã máy để tra cứu lịch sử:", sorted(df_view['machine_display'].unique()))
    
    df_machine = df_view[df_view['machine_display'] == sel_machine].copy()
    
    # Hiển thị thông tin máy
    m_col1, m_col2 = st.columns(2)
    m_col1.info(f"📍 Chi nhánh quản lý: **{df_machine['branch'].iloc[0]}**")
    m_col2.error(f"💸 Tổng chi phí tích lũy: **{df_machine['CHI_PHÍ'].sum():,.0f} đ**")

    st.dataframe(
        df_machine.sort_values('confirmed_dt', ascending=False)[
            ['confirmed_date', 'customer_name', 'issue_reason', 'CHI_PHÍ', 'note']
        ], 
        column_config={
            "CHI_PHÍ": st.column_config.NumberColumn("Chi phí bồi thường", format="%d đ"),
            "confirmed_date": "Ngày xác nhận",
            "customer_name": "Tên khách hàng",
            "issue_reason": "Nguyên nhân hư hỏng",
            "note": "Ghi chú kỹ thuật"
        },
        use_container_width=True,
        hide_index=True
    )
