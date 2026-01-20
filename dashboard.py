import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="Kho Miền Bắc V1.0.1", layout="wide")

# --- 2. MODULE ĐỌC DỮ LIỆU THÔNG MINH (CHỈ MIỀN BẮC) ---
@st.cache_data(ttl=2)
def load_data_mien_bac():
    # Link CSV Miền Bắc của sếp
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv"
    
    try:
        # Đọc thô dữ liệu
        df = pd.read_csv(url)
        
        # Xóa các dòng hoàn toàn trống
        df = df.dropna(how='all')
        
        # CHUẨN HÓA TÊN CỘT: Viết hoa, xóa khoảng trắng thừa đầu cuối
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        # TẠO DANH SÁCH KẾT QUẢ
        data_clean = []
        
        for _, row in df.iterrows():
            # 1. Tìm Mã Máy (Cột nào có chữ "MÃ SỐ MÁY")
            ma = str(row.get('MÃ SỐ MÁY', '')).strip()
            if not ma or ma.upper() == "NAN" or len(ma) < 2: continue
            
            # 2. Tìm Ngày Nhận
            ngay_nhan = pd.to_datetime(row.get('NGÀY NHẬN', ''), dayfirst=True, errors='coerce')
            ngay_tra = pd.to_datetime(row.get('NGÀY TRẢ', ''), dayfirst=True, errors='coerce')
            
            # 3. Phân loại trạng thái
            sua_nb = str(row.get('SỬA NỘI BỘ', '')).upper()
            hu_hong = str(row.get('HƯ KHÔNG SỬA ĐƯỢC', '')).strip()
            giao_lai = str(row.get('GIAO LẠI MIỀN BẮC', '')).upper()
            
            status = "🟡 ĐANG TRONG KHO"
            if "THANH LÝ" in sua_nb or hu_hong != "":
                status = "🔴 THANH LÝ/HỦY"
            elif pd.notnull(ngay_tra) or "OK" in giao_lai or "XONG" in giao_lai:
                status = "🟢 ĐÃ TRẢ VỀ"

            data_clean.append({
                "MÃ MÁY": ma,
                "LOẠI MÁY": row.get('LOẠI MÁY', ''),
                "TRẠNG THÁI": status,
                "NGÀY NHẬN": ngay_nhan,
                "NGÀY TRẢ": ngay_tra,
                "KIỂM TRA": row.get('KIỂM TRA THỰC TẾ', ''),
                "CHI NHÁNH": "MIỀN BẮC"
            })
            
        return pd.DataFrame(data_clean)
    except Exception as e:
        st.error(f"Lỗi đọc File: {e}")
        return pd.DataFrame()

# --- 3. HIỂN THỊ ---
st.title("🏭 QUẢN TRỊ KHO - THỬ NGHIỆM MIỀN BẮC")

df_mb = load_data_mien_bac()

if not df_mb.empty:
    # KPI NHANH
    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng nhận Miền Bắc", len(df_mb))
    c2.metric("Đang tồn kho", len(df_mb[df_mb['TRẠNG THÁI'] == "🟡 ĐANG TRONG KHO"]))
    c3.metric("Thanh lý", len(df_mb[df_mb['TRẠNG THÁI'] == "🔴 THANH LÝ/HỦY"]))
    
    # BẢNG DỮ LIỆU
    st.subheader("📋 Dữ liệu đọc được từ Sheet Miền Bắc")
    st.dataframe(df_mb, use_container_width=True)
    
    # BIỂU ĐỒ KIỂM TRA
    fig = px.pie(df_mb, names='TRẠNG THÁI', title="Tỷ lệ trạng thái (Miền Bắc)")
    st.plotly_chart(fig, use_container_width=True)
    
    st.success("✅ Đã kết nối thành công Sheet Miền Bắc! Sếp kiểm tra xem dữ liệu trong bảng đã đúng chưa?")
else:
    st.warning("⚠️ Vẫn chưa đọc được dữ liệu. Sếp hãy nhấn nút 'R' trên bàn phím để tải lại trang.")
