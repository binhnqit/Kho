import streamlit as st
import plotly.express as px

def render_dashboard(df):
    st.title("📊 BÁO CÁO VẬN HÀNH – DECISION DASHBOARD")

    if df.empty:
        st.warning("⚠️ Không có dữ liệu để hiển thị báo cáo.")
        return

    # ---------- 1. KPI LAYER ----------
    st.subheader("🚀 Chỉ số tổng quan")
    k1, k2, k3, k4 = st.columns(4)
    
    total_cost = df['CHI_PHÍ'].sum()
    total_cases = len(df)
    hot_branch = df['branch'].value_counts().idxmax() if not df.empty else "N/A"
    risky_machine = df['machine_display'].value_counts().idxmax() if not df.empty else "N/A"

    k1.metric("💰 Tổng chi phí", f"{total_cost:,.0f} đ")
    k2.metric("🛠️ Tổng số ca", f"{total_cases} ca")
    k3.metric("🏢 Chi nhánh HOT", hot_branch)
    k4.metric("⚠️ Máy rủi ro nhất", risky_machine)

    st.divider()

    # ---------- 2. TREND & ANALYSIS ----------
    col_chart1, col_chart2 = st.columns([6, 4])
    
    with col_chart1:
        st.subheader("📈 Xu hướng sự cố")
        trend_df = df.groupby(['NĂM', 'THÁNG']).size().reset_index(name='so_ca')
        fig_trend = px.line(trend_df, x='THÁNG', y='so_ca', color='NĂM', markers=True, title="Số ca theo tháng")
        st.plotly_chart(fig_trend, use_container_width=True)

    with col_chart2:
        st.subheader("📍 Phân bổ theo Chi nhánh")
        fig_pie = px.pie(df, names='branch', values='CHI_PHÍ', hole=0.4, title="Tỷ trọng chi phí")
        st.plotly_chart(fig_pie, use_container_width=True)

    # ---------- 3. RISK SCORING TABLE ----------
    st.divider()
    st.subheader("⚠️ Xếp hạng rủi ro thiết bị")
    
    risk_df = df.groupby('machine_display').agg(
        so_ca=('id', 'count'),
        tong_chi_phi=('CHI_PHÍ', 'sum'),
        branch=('branch', 'first')
    ).reset_index()

    # Tính điểm rủi ro đơn giản (0-1)
    if not risk_df.empty:
        risk_df['risk_score'] = (
            0.6 * (risk_df['so_ca'] / risk_df['so_ca'].max()) + 
            0.4 * (risk_df['tong_chi_phi'] / risk_df['tong_chi_phi'].max())
        ).round(2)

        def get_risk_label(score):
            if score >= 0.75: return "🔴 Cao"
            if score >= 0.5: return "🟠 Trung bình"
            return "🟢 Thấp"

        risk_df['Mức độ'] = risk_df['risk_score'].apply(get_risk_label)
        
        st.dataframe(
            risk_df.sort_values('risk_score', ascending=False),
            column_order=("machine_display", "branch", "so_ca", "tong_chi_phi", "risk_score", "Mức độ"),
            use_container_width=True
        )

    # ---------- 4. DRILL-DOWN CHI TIẾT ----------
    st.divider()
    st.subheader("🔍 Chi tiết lịch sử thiết bị")
    
    selected_m = st.selectbox("Chọn máy cụ thể để xem lịch sử:", sorted(df['machine_display'].unique()))
    detail_df = df[df['machine_display'] == selected_m].sort_values('confirmed_dt', ascending=False)
    
    st.dataframe(
        detail_df[['confirmed_date', 'customer_name', 'issue_reason', 'CHI_PHÍ', 'note']],
        use_container_width=True
    )
