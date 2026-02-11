import streamlit as st
import pandas as pd
import plotly.express as px

def render_dashboard(df):
    st.title("📊 BÁO CÁO VẬN HÀNH – DECISION DASHBOARD")

    # 1. KIỂM TRA DỮ LIỆU ĐẦU VÀO
    if df is None or df.empty:
        st.info("💡 Chưa có dữ liệu. Vui lòng nạp ở Tab Quản trị.")
        return

    # 2. ---------- SIDEBAR FILTER ----------
    with st.sidebar:
        st.header("⚙️ BỘ LỌC BÁO CÁO")
        
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

        # --- BỘ LỌC CHI NHÁNH (Sửa lỗi KeyError và lọc sạch dữ liệu) ---
        # Sử dụng 'df' thay vì 'df_db'
        # Kiểm tra sự tồn tại của cột 'branch' để tránh KeyError
        if 'branch' in df.columns:
            available_branches = sorted([str(x) for x in df['branch'].dropna().unique()])
        else:
            st.error("❌ Không tìm thấy cột 'branch' trong dữ liệu. Vui lòng kiểm tra bảng 'repair_cases' trên Supabase.")
            available_branches = []

        if not available_branches:
            st.warning("⚠️ Không có dữ liệu chi nhánh để hiển thị.")
            return # Dừng render nếu không có cột quan trọng
            sel_branch = st.multiselect(
            "Chi nhánh",
            options=available_branches,
            default=available_branches
        )
        # Thực hiện lọc theo chi nhánh đã chọn
        df_view = df_view[df_view['branch'].isin(sel_branch)]

    # 3. KIỂM TRA SAU KHI LỌC
    if df_view.empty:
        st.warning("⚠️ Không có dữ liệu phù hợp với bộ lọc.")
        return

    # 4. ---------- KPI LAYER ----------
    st.subheader("🚀 Chỉ số tổng quan")
    k1, k2, k3, k4 = st.columns(4)
    
    # Xác định máy rủi ro và chi nhánh hot dựa trên dữ liệu đã lọc
    risky_machine = df_view['machine_display'].value_counts().idxmax()
    hot_branch = df_view['branch'].value_counts().idxmax()

    k1.metric("💰 Tổng chi phí", f"{df_view['CHI_PHÍ'].sum():,.0f} đ")
    k2.metric("🛠️ Tổng số ca", f"{len(df_view)} ca")
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
    # Sắp xếp theo thời gian và tạo label hiển thị
    trend = trend.sort_values(['NĂM', 'THÁNG'])
    trend['Tháng/Năm'] = trend['THÁNG'].astype(str) + "/" + trend['NĂM'].astype(str)
    
    fig_trend = px.line(
        trend, x='Tháng/Năm', y='so_ca', 
        markers=True, title="Số lượng ca sự cố theo dòng thời gian",
        labels={'so_ca': 'Số ca', 'Tháng/Năm': 'Thời gian'}
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    # 6. ---------- RISK SCORING ----------
    st.divider()
    st.subheader("⚠️ Bảng xếp hạng rủi ro thiết bị (Risk Scoring)")
    
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
        # Chuẩn hóa điểm 0-1 (tránh chia cho 0 nếu chỉ có 1 ca)
        max_ca = risk_df['so_ca'].max() if risk_df['so_ca'].max() != 0 else 1
        max_cost = risk_df['tong_chi_phi'].max() if risk_df['tong_chi_phi'].max() != 0 else 1
        
        risk_df['freq_score'] = risk_df['so_ca'] / max_ca
        risk_df['cost_score'] = risk_df['tong_chi_phi'] / max_cost
        risk_df['recent_score'] = ((today - risk_df['last_case']).dt.days <= 30).astype(int)
        
        # Trọng số: 50% Tần suất - 40% Chi phí - 10% Độ gần đây
        risk_df['risk_score'] = (0.5 * risk_df['freq_score'] + 0.4 * risk_df['cost_score'] + 0.1 * risk_df['recent_score']).round(2)

        def risk_label(v):
            if v >= 0.75: return "🔴 Cao"
            elif v >= 0.5: return "🟠 Trung bình"
            return "🟢 Thấp"

        risk_df['mức_rủi_ro'] = risk_df['risk_score'].apply(risk_label)
        
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

    # 7. ---------- DRILL DOWN ----------
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
