import streamlit as st
import pandas as pd
import plotly.express as px

def render_dashboard(df):
    st.title("📊 BÁO CÁO VẬN HÀNH – DECISION DASHBOARD")

    if df.empty:
        st.info("💡 Chưa có dữ liệu. Vui lòng nạp ở Tab Quản trị.")
        return

    # ---------- SIDEBAR FILTER (Chỉ hiển thị khi có dữ liệu) ----------
    with st.sidebar:
        st.header("⚙️ BỘ LỌC BÁO CÁO")
        
        # Nút làm mới nhanh
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        f_mode = st.radio("Chế độ lọc thời gian", ["Tháng / Năm", "Khoảng ngày"])

        if f_mode == "Tháng / Năm":
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

        # Bộ lọc chi nhánh
        all_branches = sorted(df['branch'].unique())
        sel_branch = st.multiselect("Chi nhánh", options=all_branches, default=all_branches)
        df_view = df_view[df_view['branch'].isin(sel_branch)]

    # Kiểm tra sau khi lọc
    if df_view.empty:
        st.warning("⚠️ Không có dữ liệu phù hợp với bộ lọc.")
        return

    # ---------- KPI LAYER ----------
    st.subheader("🚀 Chỉ số tổng quan")
    k1, k2, k3, k4 = st.columns(4)
    
    # Sử dụng machine_display đã được xử lý từ Service
    risky_machine = df_view['machine_display'].value_counts().idxmax()

    k1.metric("💰 Tổng chi phí", f"{df_view['CHI_PHÍ'].sum():,.0f} đ")
    k2.metric("🛠️ Tổng số ca", f"{len(df_view)} ca")
    k3.metric("🏢 Chi nhánh HOT", df_view['branch'].value_counts().idxmax())
    k4.metric("⚠️ Máy rủi ro nhất", risky_machine)

    st.divider()

    # ---------- TREND ANALYSIS ----------
    st.subheader("📈 Xu hướng sự cố theo thời gian")
    trend = (
        df_view.groupby(['NĂM', 'THÁNG'])
        .agg(so_ca=('id', 'count'), chi_phi=('CHI_PHÍ', 'sum'))
        .reset_index()
    )
    # Convert Tháng sang chuỗi để biểu đồ hiển thị đẹp hơn
    trend['Tháng/Năm'] = trend['THÁNG'].astype(str) + "/" + trend['NĂM'].astype(str)
    
    fig_trend = px.line(
        trend, x='Tháng/Năm', y='so_ca', 
        markers=True, title="Số lượng ca sự cố theo dòng thời gian",
        labels={'so_ca': 'Số ca', 'Tháng/Năm': 'Thời gian'}
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    # ---------- RISK SCORING ----------
    st.divider()
    st.subheader("⚠️ Bảng xếp hạng rủi ro thiết bị (Risk Scoring)")
    
    # Tính toán Risk Score dựa trên machine_display (Mã máy)
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

    if not risk_df.empty:
        # Chuẩn hóa điểm 0-1
        risk_df['freq_score'] = risk_df['so_ca'] / risk_df['so_ca'].max()
        risk_df['cost_score'] = risk_df['tong_chi_phi'] / risk_df['tong_chi_phi'].max()
        # Điểm gần đây: Nếu có ca trong vòng 30 ngày thì cộng thêm điểm rủi ro
        risk_df['recent_score'] = ((today - risk_df['last_case']).dt.days <= 30).astype(int)
        
        # Trọng số: 50% Tần suất - 40% Chi phí - 10% Độ gần đây
        risk_df['risk_score'] = (0.5 * risk_df['freq_score'] + 0.4 * risk_df['cost_score'] + 0.1 * risk_df['recent_score']).round(2)

        def risk_label(v):
            if v >= 0.75: return "🔴 Cao"
            elif v >= 0.5: return "🟠 Trung bình"
            return "🟢 Thấp"

        risk_df['mức_rủi_ro'] = risk_df['risk_score'].apply(risk_label)
        
        # Hiển thị bảng Risk
        st.dataframe(
            risk_df.sort_values('risk_score', ascending=False)[
                ['machine_display', 'branch', 'so_ca', 'tong_chi_phi', 'risk_score', 'mức_rủi_ro']
            ], 
            column_config={
                "machine_display": "Mã thiết bị",
                "so_ca": "Số ca",
                "tong_chi_phi": st.column_config.NumberColumn("Tổng chi phí", format="%d đ"),
                "risk_score": "Điểm rủi ro"
            },
            use_container_width=True,
            hide_index=True
        )

        # Biểu đồ Heatmap rủi ro theo chi nhánh
        heat = risk_df.groupby('branch')['risk_score'].mean().reset_index()
        fig_heat = px.bar(
            heat, x='branch', y='risk_score', 
            color='risk_score', color_continuous_scale='Reds',
            title="🔥 Mức rủi ro trung bình theo Chi nhánh"
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    # ---------- DRILL DOWN ----------
    st.divider()
    st.subheader("🔍 Drill-down chi tiết theo thiết bị")
    
    # Chọn theo Mã máy (machine_display)
    sel_machine = st.selectbox("Chọn mã máy để tra cứu lịch sử:", sorted(df_view['machine_display'].unique()))
    
    df_machine = df_view[df_view['machine_display'] == sel_machine].copy()
    
    st.write(f"Đang hiển thị lịch sử sửa chữa của máy: **{sel_machine}**")
    st.dataframe(
        df_machine.sort_values('confirmed_dt', ascending=False)[
            ['confirmed_date', 'customer_name', 'issue_reason', 'CHI_PHÍ', 'note', 'branch']
        ], 
        column_config={
            "CHI_PHÍ": st.column_config.NumberColumn("Chi phí", format="%d đ"),
            "confirmed_date": "Ngày xác nhận"
        },
        use_container_width=True,
        hide_index=True
    )
