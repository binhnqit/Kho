import streamlit as st
import pandas as pd
from datetime import datetime

def render_alerts(df_db):
    st.markdown("""
        <style>
        .apple-card {
            background-color: #ffffff;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border: 1px solid #f0f0f0;
            margin-bottom: 20px;
        }
        .critical-text { color: #FF3B30; font-weight: 600; }
        .warning-text { color: #FF9500; font-weight: 600; }
        .safe-text { color: #34C759; font-weight: 600; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🚨 Trung Tâm Cảnh Báo")
    st.caption("Thiết kế theo ngôn ngữ Human Interface - Apple")

    if df_db.empty:
        st.info("Hiện tại hệ thống chưa phát hiện rủi ro nào.")
        return

    # --- CHỈ SỐ NHANH (Apple Style Metrics) ---
    st.subheader("Trạng thái hiện tại")
    m1, m2, m3 = st.columns(3)
    
    # Logic tính toán
    high_cost_cases = df_db[df_db['CHI_PHÍ'] > 5000000]
    repeat_issues = df_db.groupby('machine_display').filter(lambda x: len(x) > 2)['machine_display'].nunique()

    with m1:
        st.markdown(f"<div class='apple-card'> <p style='color:gray;'>Chi phí cao</p> <h2 class='critical-text'>{len(high_cost_cases)}</h2> <p>Ca vượt ngưỡng</p></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='apple-card'> <p style='color:gray;'>Lặp lỗi</p> <h2 class='warning-text'>{repeat_issues}</h2> <p>Máy hỏng > 2 lần</p></div>", unsafe_allow_html=True)
    with m3:
        st.markdown(f"<div class='apple-card'> <p style='color:gray;'>Hệ thống</p> <h2 class='safe-text'>Ổn định</h2> <p>Trạng thái kết nối</p></div>", unsafe_allow_html=True)

    st.divider()

    # --- DANH SÁCH CẢNH BÁO THÔNG MINH ---
    st.subheader("Danh sách hành động cần xử lý")

    # 1. Cảnh báo chi phí bất thường (Anomaly Detection)
    mean_cost = df_db['CHI_PHÍ'].mean()
    anomalies = df_db[df_db['CHI_PHÍ'] > mean_cost * 2]

    for _, row in anomalies.iterrows():
        with st.expander(f"🔴 Chi phí bất thường: {row['machine_display']} - {row['CHI_PHÍ']:,.0f}đ"):
            st.write(f"**Chi nhánh:** {row['branch']}")
            st.write(f"**Lý do:** {row['issue_reason']}")
            st.write(f"**Ghi chú:** {row['note'] if row['note'] else 'Không có'}")
            st.button("Xác nhận đã xem", key=f"btn_{row['id']}")

    # 2. Cảnh báo máy sửa quá nhiều trong thời gian ngắn
    st.markdown("---")
    st.subheader("🛠️ Theo dõi thiết bị rủi ro")
    
    machine_counts = df_db['machine_display'].value_counts()
    risky_machines = machine_counts[machine_counts >= 2].index.tolist()

    if risky_machines:
        df_risky = df_db[df_db['machine_display'].isin(risky_machines)]
        st.dataframe(
            df_risky[['machine_display', 'branch', 'confirmed_date', 'CHI_PHÍ', 'issue_reason']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("Không có thiết bị nào cần theo dõi đặc biệt.")
