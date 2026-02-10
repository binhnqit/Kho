import streamlit as st
import pandas as pd
from services.repair_service import get_repair_data
from tabs.dashboard import render_dashboard
from tabs.admin import render_admin_panel

# 1. Cấu hình trang (Luôn ở đầu tiên)
st.set_page_config(
    page_title="Hệ thống Quản lý Kho & Sửa chữa",
    page_icon="🛠️",
    layout="wide"
)

def main():
    # 2. Lấy dữ liệu từ Service
    df_db = get_repair_data()

    # 3. Sidebar chung
    with st.sidebar:
        st.title("🔧 OPS CONTROL")
        st.divider()
        if st.button("🔄 Làm mới dữ liệu"):
            st.cache_data.clear()
            st.rerun()

    # 4. Khởi tạo các Tabs
    tab_dash, tab_admin, tab_alert = st.tabs([
        "📊 Báo cáo vận hành", 
        "📥 Quản trị & Nhập liệu", 
        "🚨 Cảnh báo rủi ro"
    ])

    # 5. Điều hướng nội dung vào từng Tab (Chú ý thụt lề ở đây)
    with tab_dash:
        # Dòng render phải lùi vào 4 dấu cách so với 'with'
        render_dashboard(df_db)

    with tab_admin:
        # Dòng render phải lùi vào 4 dấu cách so với 'with'
        render_admin_panel()

    with tab_alert:
        st.header("🚨 Cảnh báo rủi ro")
        st.info("Tính năng cảnh báo đang được phát triển.")

if __name__ == "__main__":
    main()
