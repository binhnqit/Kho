import streamlit as st

# PHẢI LÀ DÒNG ĐẦU TIÊN (chỉ sau import streamlit)
st.set_page_config(
    page_title="Hệ thống Quản lý Kho & Sửa chữa",
    page_icon="🛠️",
    layout="wide"
)

# Sau đó mới import các module nội bộ
import pandas as pd
from services.repair_service import get_repair_data
from tabs.dashboard import render_dashboard
from tabs.admin import render_admin_panel

def main():
    # Lấy dữ liệu
    df_db = get_repair_data()

    # Sidebar
    with st.sidebar:
        st.title("🔧 OPS CONTROL")
        if st.button("🔄 Làm mới dữ liệu"):
            st.cache_data.clear()
            st.rerun()

    # Tabs
    tab_dash, tab_admin, tab_alert = st.tabs([
        "📊 Báo cáo vận hành", 
        "📥 Quản trị & Nhập liệu", 
        "🚨 Cảnh báo rủi ro"
    ])

    with tab_dash:
        render_dashboard(df_db)

    with tab_admin:
        render_admin_panel(df_db)

    with tab_alert:
        st.header("🚨 Cảnh báo rủi ro")
        st.info("Tính năng đang phát triển.")

if __name__ == "__main__":
    main()
