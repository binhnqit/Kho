import streamlit as st
import pandas as pd
import plotly.express as px

def render_ai_intelligence(df_db):
    st.title("🧠 AI Decision Intelligence")
    st.caption("Hệ thống hỗ trợ ra quyết định dựa trên dữ liệu vận hành thực tế")

    # Kiểm tra điều kiện dữ liệu tối thiểu
    if df_db.empty or len(df_db) < 10:
        st.warning("⚠️ Hệ thống AI cần tối thiểu 10 ca sửa chữa để xây dựng mô hình phân tích chính xác.")
        return

    # Khởi tạo Tabs bên trong
    ai_risk, ai_root, ai_action, ai_forecast = st.tabs([
        "🚨 RỦI RO", "🔍 NGUYÊN NHÂN GỐC", "🧩 KHUYẾN NGHỊ", "📈 DỰ BÁO"
    ])

    # 1. AI Phân tích rủi ro
    with ai_risk:
        st.subheader("🚨 Phân tích mức độ rủi ro Chi nhánh")
        risk_branch = df_db.groupby('branch').agg(
            total_cases=('id', 'count'),
            total_cost=('CHI_PHÍ', 'sum'),
            avg_cost=('CHI_PHÍ', 'mean')
        ).reset_index()

        cost_mean = risk_branch['avg_cost'].mean()
        cost_std = risk_branch['avg_cost'].std()
        
        # Gán nhãn rủi ro bằng logic thống kê
        risk_branch['risk_level'] = risk_branch['avg_cost'].apply(
            lambda x: "CAO" if x > cost_mean + (0.5 * cost_std) else "BÌNH THƯỜNG"
        )
        
        # Trực quan hóa rủi ro
        fig_risk = px.scatter(risk_branch, x='total_cases', y='avg_cost', size='total_cost',
                             color='risk_level', hover_name='branch',
                             title="Ma trận Rủi ro: Tần suất vs Chi phí trung bình",
                             labels={'total_cases': 'Số ca sửa chữa', 'avg_cost': 'Chi phí TB/ca'},
                             color_discrete_map={"CAO": "#EF553B", "BÌNH THƯỜNG": "#00CC96"})
        st.plotly_chart(fig_risk, use_container_width=True)

    # 2. AI Nguyên nhân gốc
    with ai_root:
        st.subheader("🔍 Phân tích nguyên nhân gốc (Root Cause)")
        machine_stats = df_db.groupby(['machine_display', 'branch']).agg(
            total_cases=('id', 'count'),
            total_cost=('CHI_PHÍ', 'sum'),
            avg_cost=('CHI_PHÍ', 'mean')
        ).reset_index()

        # Chuẩn hóa score để tính Risk
        machine_stats['freq_score'] = machine_stats['total_cases'] / machine_stats['total_cases'].max()
        machine_stats['cost_score'] = machine_stats['total_cost'] / machine_stats['total_cost'].max()
        machine_stats['risk_score'] = (0.6 * machine_stats['freq_score'] + 0.4 * machine_stats['cost_score']).round(2)

        def explain_root(row):
            if row['freq_score'] > 0.7 and row['cost_score'] > 0.7: return "⚠️ Thiết bị lỗi lặp lại + chi phí cao"
            if row['freq_score'] > 0.7: return "🔄 Tần suất hỏng bất thường"
            if row['cost_score'] > 0.7: return "💰 Chi phí thay thế phụ tùng đắt đỏ"
            return "✅ Vận hành ổn định"

        machine_stats['Giải thích'] = machine_stats.apply(explain_root, axis=1)
        
        st.dataframe(
            machine_stats.sort_values('risk_score', ascending=False)
            [['machine_display', 'branch', 'risk_score', 'Giải thích']], 
            use_container_width=True, hide_index=True
        )

    # 3. AI Khuyến nghị
    with ai_action:
        st.subheader("🧩 Khuyến nghị hành động dành cho Quản lý")
        recommendations = []
        for _, r in machine_stats.iterrows():
            if r['risk_score'] >= 0.75:
                recommendations.append({
                    "Đối tượng": r['machine_display'], 
                    "Chi nhánh": r['branch'], 
                    "Khuyến nghị": "🚩 THAY THẾ MỚI", 
                    "Lý do": "Vượt ngưỡng rủi ro kinh tế"
                })
            elif r['risk_score'] >= 0.50:
                recommendations.append({
                    "Đối tượng": r['machine_display'], 
                    "Chi nhánh": r['branch'], 
                    "Khuyến nghị": "🔧 BẢO TRÌ CHUYÊN SÂU", 
                    "Lý do": "Dấu hiệu xuống cấp nhanh"
                })
        
        if recommendations:
            st.table(pd.DataFrame(recommendations))
        else:
            st.success("✅ Không có thiết bị nào cần can thiệp khẩn cấp.")

    # 4. AI Dự báo
    with ai_forecast:
        st.subheader("📈 Dự báo chi phí vận hành tháng tới")
        forecast_results = []
        for b in df_db['branch'].unique():
            df_b = df_db[df_db['branch'] == b]
            # Gom nhóm theo tháng/năm
            monthly = df_b.groupby(['NĂM', 'THÁNG'])['CHI_PHÍ'].sum()
            if len(monthly) >= 2:
                # Dự báo đơn giản: (Tháng cuối * 0.7) + (Trung bình * 0.3)
                forecast_value = (monthly.iloc[-1] * 0.7) + (monthly.mean() * 0.3)
                forecast_results.append({"branch": b, "val": forecast_value})
        
        if forecast_results:
            cols = st.columns(len(forecast_results))
            for i, r in enumerate(forecast_results):
                with cols[i]:
                    st.metric(f"Dự báo: {r['branch']}", f"{r['val']:,.0f} đ")
        else:
            st.info("Chưa đủ dữ liệu lịch sử theo tháng để AI thực hiện dự báo.")
