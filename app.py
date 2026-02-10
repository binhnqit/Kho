import streamlit as st
from services.repair_service import get_repair_data
from tabs.dashboard import render_dashboard  # <--- THÊM DÒNG NÀY
from tabs.admin import render_admin_panel

# 1. Cấu hình trang (Luôn để ở dòng đầu tiên)
st.set_page_config(
    page_title="Hệ thống Quản lý Kho & Sửa chữa",
    page_icon="🛠️",
    layout="wide"
)

# 2. CSS tùy chỉnh để giao diện chuyên nghiệp hơn
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

def main():
    # 3. Lấy dữ liệu sạch từ Service (Đã được map tên máy và chuẩn hóa cột)
    df_db = get_repair_data()

    # 4. Tạo thanh Sidebar chung cho toàn bộ App
    with st.sidebar:
        st.image("https://www.gstatic.com/images/branding/product/2x/drive_2020q4_48dp.png", width=50) # Ví dụ logo
        st.title("🔧 OPS CONTROL")
        st.divider()
        if st.button("🔄 Làm mới toàn bộ dữ liệu"):
            st.cache_data.clear()
            st.rerun()

    # 5. Khởi tạo các Tabs chính
    with tab_dash:
        render_dashboard(df_db) # <--- GỌI HÀM CỰC KỲ GỌN

    # 6. Điều hướng nội dung (Sau này sẽ gọi từ thư mục tabs/)
    with tab_dash:
        st.info("💡 Đang kết nối dữ liệu...")
        # Chúng ta sẽ viết hàm render_dashboard(df_db) vào file tabs/dashboard.py sau
        # Hiện tại để tạm dòng này để kiểm tra dữ liệu:
        if not df_db.empty:
            st.success(f"Đã tải {len(df_db)} ca sửa chữa thành công!")
            st.dataframe(df_db.head(5))
        else:
            st.warning("Chưa có dữ liệu hoặc lỗi kết nối.")

    with tab_admin:
    render_admin_panel()

    with tab_alert:
        st.write("Nội dung Tab Cảnh báo sẽ được triển khai tiếp theo.")

if __name__ == "__main__":
    main()
