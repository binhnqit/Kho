import streamlit as st
import pandas as pd

def render_alerts(df_db):
    st.markdown("""
        <style>
        .apple-card {
            background-color: #ffffff; border-radius: 15px; padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #f0f0f0; margin-bottom: 20px;
        }
        .critical-text { color: #FF3B30; font-weight: 600; }
        .warning-text { color: #FF9500; font-weight: 600; }
        .safe-text { color: #34C759; font-weight: 600; }
        .days-badge {
            background-color: #FF3B30; color: white; padding: 2px 8px;
            border-radius: 10px; font-size: 0.8rem; margin-left: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🚨 Trung Tâm Cảnh Báo")
    
    if df_db.empty:
        st.info("Hiện tại hệ thống chưa phát hiện rủi ro nào.")
        return

    # --- TÍNH TOÁN LOGIC (BACKEND) ---
    # 1. Tính số ngày tồn (SLA)
    now = pd.Timestamp.now(tz='UTC')
    df_db['created_at_dt'] = pd.to_datetime(df_db['created_at'])
    df_db['ngay_ton'] = (now - df_db['created_at_dt']).dt.days
    
    # 2. Lọc các ca chậm tiến độ (Ví dụ > 7 ngày và chưa trả máy)
    sla_violation = df_db[(df_db['status'] != "6. Đã trả chi nhánh") & (df_db['ngay_ton'] > 7)]
    
    # 3. Lọc chi phí cao và máy lỗi lặp lại
    high_cost_cases = df_db[df_db['CHI_PHÍ'] > 5000000]
    repeat_issues = df_db.groupby('machine_display').filter(lambda x: len(x) > 2)['machine_display'].nunique()

    # --- CHỈ SỐ NHANH ---
    st.subheader("Chỉ số rủi ro vận hành")
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"<div class='apple-card'><p style='color:gray;'>Chậm tiến độ</p><h2 class='critical-text'>{len(sla_violation)}</h2><p>Ca quá 7 ngày</p></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='apple-card'><p style='color:gray;'>Chi phí cao</p><h2 class='warning-text'>{len(high_cost_cases)}</h2><p>Ca > 5 Triệu</p></div>", unsafe_allow_html=True)
    with m3:
        st.markdown(f"<div class='apple-card'><p style='color:gray;'>Lặp lỗi</p><h2 class='warning-text'>{repeat_issues}</h2><p>Máy hỏng > 2 lần</p></div>", unsafe_allow_html=True)

    # --- PHẦN 1: CẢNH BÁO SLA (MỚI BỔ SUNG) ---
    st.divider()
    st.subheader("⚠️ Cảnh báo tồn kho quá hạn (SLA)")
    if not sla_violation.empty:
        for _, row in sla_violation.iterrows():
            with st.expander(f"🕒 {row['machine_display']} - Đã ngâm {row['ngay_ton']} ngày"):
                c1, c2 = st.columns(2)
                c1.write(f"**Trạng thái hiện tại:** {row['status']}")
                c1.write(f"**Chi nhánh gốc:** {row['origin_branch']}")
                c2.write(f"**Khách hàng:** {row['customer_name']}")
                c2.write(f"**Lý do:** {row['issue_reason']}")
                if st.button("Hối thúc xử lý", key=f"sla_{row['id']}"):
                    st.toast(f"Đã gửi yêu cầu ưu tiên cho máy {row['machine_display']}")
    else:
        st.success("Không có ca nào bị chậm tiến độ.")

    # --- PHẦN 2: CHI PHÍ BẤT THƯỜNG (CỦA BẠN) ---
    st.divider()
    st.subheader("💰 Chi phí bất thường (Anomaly Detection)")
    mean_cost = df_db['CHI_PHÍ'].mean()
    anomalies = df_db[df_db['CHI_PHÍ'] > mean_cost * 2]
    
    if not anomalies.empty:
        for _, row in anomalies.iterrows():
            with st.expander(f"🔴 {row['machine_display']} - {row['CHI_PHÍ']:,.0f}đ (Gấp {row['CHI_PHÍ']/mean_cost:.1f} lần TB)"):
                st.write(f"**Lý do hỏng:** {row['issue_reason']}")
                st.write(f"**Ghi chú:** {row['note'] if row['note'] else 'Không có'}")
    else:
        st.info("Chưa ghi nhận chi phí bất thường.")

    # --- PHẦN 3: THEO DÕI THIẾT BỊ RỦI RO (CỦA BẠN) ---
    st.divider()
    st.subheader("🛠️ Theo dõi thiết bị hỏng lặp lại")
    machine_counts = df_db['machine_display'].value_counts()
    risky_machines = machine_counts[machine_counts >= 2].index.tolist()

    if risky_machines:
        df_risky = df_db[df_db['machine_display'].isin(risky_machines)]
        st.dataframe(
            df_risky[['machine_display', 'branch', 'confirmed_date', 'CHI_PHÍ', 'issue_reason']],
            use_container_width=True, hide_index=True
        )
