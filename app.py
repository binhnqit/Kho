import streamlit as st
import pandas as pd

# 1. PAGE CONFIG (Bắt buộc đặt đầu tiên)
st.set_page_config(
    page_title="Hệ thống Quản lý Kho & Sửa chữa",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. IMPORT MODULES
# Đảm bảo các file này tồn tại trong thư mục services/ và tabs/
from services.auth import render_auth_interface
from services.repair_service import get_repair_data
from tabs.dashboard import render_dashboard
from tabs.admin import render_admin_panel
from tabs.kpi import render_kpi_dashboard
from tabs.alerts import render_alerts
from tabs.ai_intelligence import render_ai_intelligence

# 3. CSS CUSTOMIZATION (Tùy chỉnh giao diện cho Apple Style)
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        border-radius: 8px 8px 0px 0px;
    }
    div[data-testid="stExpander"] { border: none; box-shadow: 0 2px 6px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# 4. KHỞI TẠO SESSION STATE
if "is_logged_in" not in st.session_state:
    st.session_state["is_logged_in"] = False
if "user_info" not in st.session_state:
    st.session_state["user_info"] = None

def main():
    # --- KIỂM TRA TRẠNG THÁI ĐĂNG NHẬP ---
    if not st.session_state["is_logged_in"]:
        render_auth_interface()
        return  

    # --- NẾU ĐÃ ĐĂNG NHẬP, LẤY DỮ LIỆU ---
    # get_repair_data() nên trả về DataFrame đã xử lý cột NĂM, THÁNG
    df_db = get_repair_data()
    user_info = st.session_state["user_info"]

    # 5. SIDEBAR (Thiết kế tối giản)
    with st.sidebar:
        st.title("🔧 OPS CONTROL")
        st.info(f"👤 **{user_info['full_name']}**\n\n🎯 Vai trò: {user_info['role']}")
        
        st.divider()
        
        # Tiện ích nhanh
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
            st.cache_data.clear()
            st.toast("Đang cập nhật dữ liệu mới nhất...", icon="⏳")
            st.rerun()
            
        if st.button("🚪 Đăng xuất", type="secondary", use_container_width=True):
            st.session_state["is_logged_in"] = False
            st.session_state["user_info"] = None
            st.rerun()

        st.divider()
        st.caption("© 2024 Operation Management System")

    # 6. HỆ THỐNG TABS CHÍNH
    # Sử dụng Icon để tăng tính trực quan
    tab_dash, tab_admin, tab_kpi, tab_ai, tab_alert = st.tabs([
        "📊 Dashboard", 
        "📥 Quản trị & Nhập liệu", 
        "🎯 KPI Hiệu suất", 
        "🧠 AI Insights",
        "🚨 Cảnh báo rủi ro"
    ])

    with tab_dash:
        # Truyền df_db vào tab báo cáo
        render_dashboard(df_db)

    with tab_admin:
        # Bảo mật: Chỉ Admin hoặc Manager mới thấy nội dung nhạy cảm nếu cần
        # Ở đây cho phép hiển thị chung, nhưng có thể check trong render_admin_panel
        render_admin_panel(df_db)

    with tab_kpi:
        render_kpi_dashboard(df_db)

    with tab_ai:
        render_ai_intelligence(df_db)

    with tab_alert:
        render_alerts(df_db)

if __name__ == "__main__":
    main()
