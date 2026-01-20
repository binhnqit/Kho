import streamlit as st
import pandas as pd

# --- 1. HÀM LOAD DỮ LIỆU CẢI TIẾN ---
# Thêm tham số show_spinner=False để tránh treo giao diện
@st.cache_data(ttl=300, show_spinner=False)
def load_data_from_url(url):
    try:
        # Tối ưu hóa timeout và cấu hình đọc file
        return pd.read_csv(url, dtype=str, on_bad_lines='skip', engine='python')
    except Exception:
        return pd.DataFrame()

# --- 2. LOGIC ĐIỀU KHIỂN CHÍNH ---
def main():
    st.title("🛡️ HỆ THỐNG QUẢN TRỊ V15.4")
    
    # Định nghĩa link
    url_fin = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?output=csv"
    
    # Dùng st.spinner cục bộ thay vì chặn toàn màn hình
    with st.spinner('Đang lấy dữ liệu từ hệ thống...'):
        df_raw = load_data_from_url(url_fin)

    # KIỂM TRA DỮ LIỆU THÔNG MINH
    if df_raw.empty:
        st.error("⚠️ Không thể tải dữ liệu. Vui lòng kiểm tra lại kết nối Internet hoặc link Google Sheets.")
        if st.button("🔄 Thử kết nối lại"):
            st.cache_data.clear()
            st.rerun()
    else:
        # CHỈ KHI CÓ DỮ LIỆU MỚI CHẠY TIẾP CÁC TAB
        render_dashboard(df_raw)

def render_dashboard(df):
    # (Tại đây dán toàn bộ logic các Tab của sếp vào)
    st.success("✅ Kết nối thành công!")
    tabs = st.tabs(["📊 Tài Chính", "📦 Kho Vận"])
    with tabs[0]:
        st.write("Dữ liệu tài chính đã sẵn sàng.")

if __name__ == "__main__":
    main()
