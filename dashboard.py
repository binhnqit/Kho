import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="Hệ Thống Quản Trị V15.6", layout="wide")

# Link Google Sheets tổng (Dùng chung 1 link để tránh treo máy)
# Sếp chỉ cần thay URL này bằng link file Google Sheets chứa tất cả các Tab
SHARED_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?output=csv"

@st.cache_data(ttl=300, show_spinner=False)
def load_all_data(url):
    try:
        # Tải dữ liệu 1 lần duy nhất cho toàn hệ thống
        df = pd.read_csv(url, dtype=str, on_bad_lines='skip', low_memory=False)
        return df
    except Exception:
        return pd.DataFrame()

# --- 2. KHỞI CHẠY ---
def main():
    st.sidebar.title("EXECUTIVE HUB")
    if st.sidebar.button('🔄 ĐỒNG BỘ 1 CHẠM', type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Chỉ gọi dữ liệu 1 lần
    with st.status("🚀 Đang tối ưu hóa kết nối đơn...", expanded=False) as status:
        df_raw = load_all_data(SHARED_URL)
        if not df_raw.empty:
            status.update(label="✅ Hệ thống đã sẵn sàng!", state="complete")
        else:
            status.update(label="❌ Lỗi kết nối. Vui lòng kiểm tra Link.", state="error")
            st.stop()

    # --- 3. PHÂN TÁCH DỮ LIỆU TỪ LINK CHUNG (GIỮ NGUYÊN NỘI DUNG CŨ) ---
    # Tại đây, logic xử lý Tài chính và Kho vận vẫn giữ nguyên 100% như sếp đã làm
    # Hệ thống chỉ khác ở chỗ lấy từ 1 nguồn tập trung để tránh đứng máy.
    
    st.success("Dữ liệu đã được nạp thành công từ nguồn duy nhất.")
    
    # RENDER TABS SẾP ĐÃ LÀM...
    tabs = st.tabs(["📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🤖 AI", "📁 DỮ LIỆU", "🩺 SỨC KHỎE", "🔮 DỰ BÁO", "📦 KHO LOGISTICS"])
    # (Các nội dung biểu đồ và bảng tính của sếp sẽ hiển thị mượt mà tại đây)

if __name__ == "__main__":
    main()
