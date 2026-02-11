import streamlit as st

# PHẢI LÀ DÒNG ĐẦU TIÊN (chỉ sau import streamlit)
st.set_page_config(
    page_title="Hệ thống Quản lý Kho & Sửa chữa",
    page_icon="🛠️",
    layout="wide"
)

# Sau đó mới import các module nội bộ
import pandas as pd
import plotly.express as px
from tabs.kpi import render_kpi_dashboard # Thêm dòng này
from tabs.ai_intelligence import render_ai_intelligence
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
    tab_dash, tab_admin, tab_kpi, tab_alert = st.tabs([
        "📊 BÁO CÁO VẬN HÀNH", 
        "📥 QUẢN TRỊ VÀ NHẬP LIỆU", 
        "🎯 KPI HIỆU SUẤT", 
        "🧠 AI",
        "🚨 CẢNH BÁO RỦI RO"
    ])

# ... các with tab khác ...

    with tab_kpi:
        render_kpi_dashboard(df_db) # Gọi hàm từ file kpi.py

    with tab_ai:
        render_ai_intelligence(df_db)
    
    with tab_dash:
        render_dashboard(df_db)

    with tab_admin:
        render_admin_panel(df_db)

    with tab_alert:
        st.header("🚨 Cảnh báo rủi ro")
        st.info("Tính năng đang phát triển.")

if __name__ == "__main__":
    main()
