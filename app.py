import streamlit as st

# 1. PAGE CONFIG (Bắt buộc là dòng lệnh Streamlit đầu tiên)
st.set_page_config(
    page_title="Hệ thống Quản lý Kho & Sửa chữa",
    page_icon="🛠️",
    layout="wide"
)

# 2. IMPORT MODULES
import pandas as pd
import plotly.express as px
from services.auth import render_auth_interface
from services.repair_service import get_repair_data
from tabs.dashboard import render_dashboard
from tabs.admin import render_admin_panel
from tabs.kpi import render_kpi_dashboard
from tabs.alerts import render_alerts
from tabs.ai_intelligence import render_ai_intelligence

# 3. KHỞI TẠO SESSION STATE
if "is_logged_in" not in st.session_state:
    st.session_state["is_logged_in"] = False

def main():
    # KIỂM TRA ĐĂNG NHẬP
    if not st.session_state["is_logged_in"]:
        render_auth_interface()
        return  # Dừng lại tại đây, không chạy code phía dưới nếu chưa login

    # --- NẾU ĐÃ ĐĂNG NHẬP, CHẠY TOÀN BỘ CODE DƯỚI ĐÂY ---
    
    # 4. LẤY DỮ LIỆU (Chỉ lấy khi đã vào app)
    df_db = get_repair_data()
    user_info = st.session_state["user_info"]

    # 5. SIDEBAR (Apple Style)
    with st.sidebar:
        st.title("🔧 OPS CONTROL")
        st.markdown(f"👤 Chào, **{user_info['full_name']}**")
        st.caption(f"Vai trò: {user_info['role']}")
        
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
            
        st.divider()
        if st.button("🚪 Đăng xuất", type="secondary", use_container_width=True):
            st.session_state["is_logged_in"] = False
            st.session_state["user_info"] = None
            st.rerun()

    # 6. HỆ THỐNG TABS CHÍNH
    tab_dash, tab_admin, tab_kpi, tab_ai, tab_alert = st.tabs([
        "📊 BÁO CÁO VẬN HÀNH", 
        "📥 QUẢN TRỊ & NHẬP LIỆU", 
        "🎯 KPI HIỆU SUẤT", 
        "🧠 AI INSIGHTS",
        "🚨 CẢNH BÁO RỦI RO"
    ])

    with tab_dash:
        render_dashboard(df_db)

    with tab_admin:
        # Nếu muốn bảo mật hơn: 
        # if user_info['role'] == 'Admin': render_admin_panel(df_db)
        render_admin_panel(df_db)

    with tab_kpi:
        render_kpi_dashboard(df_db)

    with tab_ai:
        render_ai_intelligence(df_db)

    with tab_alert:
        render_alerts(df_db)

if __name__ == "__main__":
    main()
