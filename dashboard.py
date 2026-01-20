import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="Kho Miền Bắc V1.0.4", layout="wide")

@st.cache_data(ttl=2)
def load_data_mien_bac_final_v2():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv"
    
    try:
        # BẮT ĐẦU ĐỌC TỪ DÒNG 2 (skiprows=1)
        df = pd.read_csv(url, skiprows=1, dtype=str)
        
        # CHUẨN HÓA TIÊU ĐỀ (Xóa khoảng trắng, viết hoa)
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        # --- XỬ LÝ LỖI TRỘN DÒNG (Forward Fill) ---
        # Thay thế ô rỗng bằng NA để ffill hoạt động
        df = df.replace(r'^\s*$', pd.NA, regex=True)
        
        # Điền đầy dữ liệu cho các cột quan trọng nếu bị trống do trộn dòng
        fill_cols = ['MÃ SỐ MÁY', 'NGÀY NHẬN', 'LOẠI MÁY', 'TRÌNH TRẠNG']
        for col in fill_cols:
            if col in df.columns:
                df[col] = df[col].ffill()

        data_clean = []
        # Duyệt qua từng dòng dữ liệu
        for _, row in df.iterrows():
            ma = str(row.get('MÃ SỐ MÁY', '')).strip()
            
            # Loại bỏ dòng tiêu đề lặp lại hoặc dòng trống
            if not ma or ma.upper() in ["NAN", "STT", "MÃ SỐ MÁY", "0"]: 
                continue
            
            # Chuyển đổi ngày tháng
            d_nhan = pd.to_datetime(row.get('NGÀY NHẬN', ''), dayfirst=True, errors='coerce')
            d_tra = pd.to_datetime(row.get('NGÀY TRẢ', ''), dayfirst=True, errors='coerce')
            
            # LOGIC TRẠNG THÁI THEO CỘT THỰC TẾ
            sua_nb = str(row.get('SỬA NỘI BỘ', '')).upper()
            hu_hong = str(row.get('HƯ KHÔNG SỬA ĐƯỢC', '')).strip()
            giao_lai = str(row.get('GIAO LẠI MIỀN BẮC', '')).upper()
            
            status = "🟡 TRONG KHO"
            if "THANH LÝ" in sua_nb or hu_hong != "":
                status = "🔴 THANH LÝ"
            elif pd.notnull(d_tra) or any(x in giao_lai for x in ["OK", "XONG"]):
                status = "🟢 ĐÃ XONG"

            data_clean.append({
                "MÃ MÁY": ma,
                "LOẠI MÁY": row.get('LOẠI MÁY', ''),
                "TÌNH TRẠNG GỐC": row.get('TRÌNH TRẠNG', ''),
                "TRẠNG THÁI": status,
                "NGÀY NHẬN": d_nhan,
                "KIỂM TRA": row.get('KIỂM TRA THỰC TẾ', ''),
                "SỬA NỘI BỘ": row.get('SỬA NỘI BỘ', ''),
                "SỬA BÊN NGOÀI": row.get('SỬA BÊN NGOÀI', '')
            })
            
        return pd.DataFrame(data_clean)
    except Exception as e:
        st.error(f"Lỗi đọc dữ liệu dòng 2: {e}")
        return pd.DataFrame()

# --- 3. HIỂN THỊ ---
st.title("🏭 TRUY VẤN KHO MIỀN BẮC (DÒNG TIÊU ĐỀ 2)")

df_mb = load_data_mien_bac_final_v2()

if not df_mb.empty:
    st.success(f"✅ Đã kết nối thành công! Tìm thấy {len(df_mb)} dòng dữ liệu.")
    
    # Dashboard nhanh
    k1, k2, k3 = st.columns(3)
    k1.metric("Tổng thiết bị", len(df_mb))
    k2.metric("Đang sửa/Chờ", len(df_mb[df_mb['TRẠNG THÁI'] == "🟡 TRONG KHO"]))
    k3.metric("Đã hoàn tất", len(df_mb[df_mb['TRẠNG THÁI'] == "🟢 ĐÃ
