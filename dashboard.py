import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="Kho Miền Bắc V1.0.2", layout="wide")

# --- 2. MODULE ĐỌC DỮ LIỆU MIỀN BẮC ---
@st.cache_data(ttl=2)
def load_data_mien_bac():
    # Link CSV Miền Bắc sếp đã xuất bản
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv"
    
    try:
        # Đọc dữ liệu thô, ép kiểu string để không mất số 0 đầu mã máy
        df = pd.read_csv(url, dtype=str).fillna("")
        
        # CHUẨN HÓA TIÊU ĐỀ: Xóa khoảng trắng thừa và viết hoa
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        data_clean = []
        for _, row in df.iterrows():
            # Kiểm tra Mã Số Máy (Cột quan trọng nhất)
            ma = str(row.get('MÃ SỐ MÁY', '')).strip()
            if not ma or ma.upper() in ["NAN", "", "STT"]: continue
            
            # Xử lý ngày tháng theo đúng định dạng Việt Nam
            d_nhan = pd.to_datetime(row.get('NGÀY NHẬN', ''), dayfirst=True, errors='coerce')
            d_tra = pd.to_datetime(row.get('NGÀY TRẢ', ''), dayfirst=True, errors='coerce')
            
            # LOGIC TRẠNG THÁI (Dựa trên cấu trúc sếp gửi)
            sua_nb = str(row.get('SỬA NỘI BỘ', '')).upper()
            hu_hong = str(row.get('HƯ KHÔNG SỬA ĐƯỢC', '')).strip()
            giao_lai_mb = str(row.get('GIAO LẠI MIỀN BẮC', '')).upper()
            
            # Ưu tiên 1: Thanh lý
            if "THANH LÝ" in sua_nb or hu_hong != "":
                status = "🔴 THANH LÝ"
            # Ưu tiên 2: Đã trả (Có ngày trả hoặc xác nhận giao lại)
            elif pd.notnull(d_tra) or any(x in giao_lai_mb for x in ["OK", "XONG"]):
                status = "🟢 ĐÃ XONG"
            # Ưu tiên 3: Đang xử lý
            else:
                status = "🟡 TRONG KHO"

            data_clean.append({
                "MÃ MÁY": ma,
                "LOẠI MÁY": row.get('LOẠI MÁY', ''),
                "TRÌNH TRẠNG": row.get('TRÌNH TRẠNG', ''),
                "TRẠNG THÁI": status,
                "NGÀY NHẬN": d_nhan,
                "KIỂM TRA": row.get('KIỂM TRA THỰC TẾ', ''),
                "CHI NHÁNH": "MIỀN BẮC"
            })
            
        return pd.DataFrame(data_clean)
    except Exception as e:
        st.error(f"Lỗi truy vấn: {e}")
        return pd.DataFrame()

# --- 3. GIAO DIỆN ---
st.title("🏭 TRUY VẤN DỮ LIỆU KHO MIỀN BẮC")

df_mb = load_data_mien_bac()

if not df_mb.empty:
    # HIỂN THỊ KPI TỔNG QUAN
    k1, k2, k3 = st.columns(3)
    k1.metric("Tổng thiết bị nhận", len(df_mb))
    k2.metric("Đang sửa/Chờ trả", len(df_mb[df_mb['TRẠNG THÁI'] == "🟡 TRONG KHO"]))
    k3.metric("Đã xử lý xong", len(df_mb[df_mb['TRẠNG THÁI'] == "🟢 ĐÃ XONG"]))

    # BẢNG DỮ LIỆU CHI TIẾT
    st.write("---")
    st.subheader("📋 Danh sách chi tiết Miền Bắc")
    st.dataframe(df_mb.sort_values('NGÀY NHẬN', ascending=False), use_container_width=True)
    
    # BIỂU ĐỒ PHÂN TÍCH NHANH
    st.write("---")
    st.plotly_chart(px.bar(df_mb.groupby('TRẠNG THÁI').size().reset_index(name='SL'), 
                           x='TRẠNG THÁI', y='SL', color='TRẠNG THÁI', title="Thống kê trạng thái"), use_container_width=True)
    
    st.success("🎯 Dữ liệu Miền Bắc đã hiển thị thành công!")
else:
    st.warning("🔄 Đang quét dữ liệu từ Sheet... Sếp hãy kiểm tra xem file Google Sheets đã có dữ liệu ở cột 'MÃ SỐ MÁY' chưa?")
