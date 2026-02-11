import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def render_kpi_dashboard(df_db):
    st.title("🎯 Performance Management – KPI Dashboard")
    st.caption("Đánh giá hiệu suất – So sánh – Cảnh báo vượt ngưỡng")

    if df_db.empty:
        st.warning("⚠️ Chưa có dữ liệu để tính toán KPI")
        return

    # --- KHỞI TẠO CÁC SUB-TABS TRONG KPI ---
    k_tab1, k_tab2, k_tab3 = st.tabs(["📊 Tổng quan Hệ thống", "🏢 Hiệu suất Chi nhánh", "⚠️ Phân tích Rủi ro"])

    # ---------------------------------------------------------
    # SUB-TAB 1: TỔNG QUAN HỆ THỐNG
    # ---------------------------------------------------------
    with k_tab1:
        k1, k2, k3, k4 = st.columns(4)
        total_cases = len(df_db)
        avg_cost_val = df_db['CHI_PHÍ'].mean()
        
        unique_m = df_db['machine_display'].nunique()
        repeat_m = (df_db.groupby('machine_display').size() > 1).sum()
        repeat_rate = (repeat_m / unique_m) * 100 if unique_m > 0 else 0

        k1.metric("🛠️ Tổng số ca", f"{total_cases} ca")
        k2.metric("💰 Chi phí TB / ca", f"{avg_cost_val:,.0f} đ")
        k3.metric("♻️ Tỷ lệ máy lặp lỗi", f"{repeat_rate:.1f}%")
        k4.metric("🏢 Số chi nhánh", df_db['branch'].nunique())

        st.subheader("📈 Diễn biến vận hành")
        trend = df_db.groupby(['NĂM', 'THÁNG']).agg(
            cases=('id', 'count'),
            cost=('CHI_PHÍ', 'sum')
        ).reset_index()
        trend['period'] = trend['THÁNG'].astype(str) + "/" + trend['NĂM'].astype(str)
        
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(x=trend['period'], y=trend['cost'], name='Chi phí', line=dict(color='firebrick', width=4)))
        fig_trend.add_trace(go.Bar(x=trend['period'], y=trend['cases'], name='Số ca', yaxis='y2', opacity=0.3))
        
        fig_trend.update_layout(
            yaxis=dict(title='Tổng Chi phí (đ)'),
            yaxis2=dict(title='Số ca', overlaying='y', side='right'),
            legend=dict(x=0, y=1.1, orientation='h'),
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    # ---------------------------------------------------------
    # SUB-TAB 2: HIỆU SUẤT CHI NHÁNH
    # ---------------------------------------------------------
    with k_tab2:
        st.subheader("🏢 So sánh chi phí trung bình")
        branch_kpi = df_db.groupby('branch').agg(
            total_cases=('id', 'count'),
            total_cost=('CHI_PHÍ', 'sum'),
            avg_cost=('CHI_PHÍ', 'mean')
        ).reset_index()

        col_b1, col_b2 = st.columns([6, 4])
        with col_b1:
            st.dataframe(
                branch_kpi.style.format({'avg_cost': '{:,.0f} đ', 'total_cost': '{:,.0f} đ'})
                .background_gradient(subset=['avg_cost'], cmap='Reds'), 
                use_container_width=True
            )
        
        with col_b2:
            target_sla = 2000000 # Ngưỡng 2 triệu/ca
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = avg_cost_val,
                title = {'text': "Chi phí TB Hệ thống (SLA)"},
                delta = {'reference': target_sla, 'increasing': {'color': "red"}},
                gauge = {
                    'axis': {'range': [None, target_sla * 2]},
                    'steps': [
                        {'range': [0, target_sla], 'color': "lightgreen"},
                        {'range': [target_sla, target_sla*2], 'color': "pink"}],
                    'threshold': {'line': {'color': "red", 'width': 4}, 'value': target_sla}
                }))
            st.plotly_chart(fig_gauge, use_container_width=True)

    # ---------------------------------------------------------
    # SUB-TAB 3: PHÂN TÍCH RỦI RO
    # ---------------------------------------------------------
    with k_tab3:
        st.subheader("🚨 Top 10 Thiết bị rủi ro cao")
        machine_kpi = df_db.groupby(['machine_display', 'branch']).agg(
            cases=('id', 'count'),
            cost=('CHI_PHÍ', 'sum')
        ).reset_index()

        if not machine_kpi.empty:
            max_c = machine_kpi['cases'].max() if machine_kpi['cases'].max() > 0 else 1
            max_s = machine_kpi['cost'].max() if machine_kpi['cost'].max() > 0 else 1
            
            machine_kpi['risk_score'] = (0.6 * (machine_kpi['cases']/max_c) + 0.4 * (machine_kpi['cost']/max_s)).round(2)
            
            top_risk = machine_kpi.sort_values('risk_score', ascending=False).head(10)
            st.table(top_risk)
