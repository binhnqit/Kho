import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="Kho Miền Bắc - Fix Trộn Dòng", layout="wide")

@st.cache_data(ttl=2)
def load_data_mien_bac_fix_merge():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv"
    
    try:
        # Đọc toàn bộ dữ liệu dưới dạng text để xử lý
        df = pd.read_csv(url, dtype=str)
        
        # CHUẨN HÓA TIÊU ĐỀ
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        # --- XỬ LÝ LỖI TRỘN DÒNG (MERGE CELLS) ---
        # 1. Thay thế các ô trống thực sự bằng giá trị null của hệ thống
        df = df.replace(r'^\s*$', pd.NA, regex=True)
        
        # 2. Forward Fill cho cột MÃ SỐ MÁY: 
        # Nếu dòng dưới trống mã máy (do bị trộn), nó sẽ lấy mã từ dòng trên
        df['MÃ SỐ MÁY'] = df['MÃ SỐ MÁY'].ffill()
        
        # 3. Làm tương tự cho các cột sếp nghi ngờ bị trộn dòng
        target_cols = ['NGÀY NHẬN', 'LOẠI MÁY', 'SỬA NỘI BỘ', 'SỬA BÊN NGOÀI', 'GIAO LẠI MIỀN BẮC', 'NGÀY TRẢ', 'HƯ KHÔNG SỬA ĐƯỢC']
        for col in target_cols:
            if col in df.columns:
                df[col] = df[col].ffill()

        data_clean = []
        # Group theo Mã Máy để lấy dòng dữ liệu cuối cùng (dòng đã tổng hợp đủ thông tin sau khi ffill)
        for ma_may, group in df.groupby('MÃ SỐ MÁY'):
            if not ma_may or str(ma_may).upper() in ["NAN", "STT", "MÃ SỐ MÁY"]: 
                continue
            
            # Lấy dòng cuối cùng của group vì nó chứa dữ liệu đầy đủ nhất sau khi ffill
            last_row = group.iloc[-1]
            
            # Chuyển đổi ngày
            d_nhan = pd.to_datetime(last_row.get('NGÀY NHẬN', ''), dayfirst=True, errors='coerce')
            d_tra = pd.to_datetime(last_row.get('NGÀY TRẢ', ''), dayfirst=True, errors='coerce')
            
            # LOGIC TRẠNG THÁI
            sua_nb = str(last_row.get('SỬA NỘI BỘ', '')).upper()
            hu_hong = str(last_row.get('HƯ KHÔNG SỬA ĐƯỢC', '')).strip()
            giao_lai = str(last_row.get('GIAO LẠI MIỀN BẮC', '')).upper()
            
            status = "🟡 TRONG KHO"
            if "THANH LÝ" in sua_nb or hu_hong != "" or str(hu_hong).upper() == "X":
                status = "🔴 THANH LÝ"
            elif pd.notnull(d_tra) or any(x in giao_lai for x in ["OK", "XONG"]):
                status = "🟢 ĐÃ XONG"

            data_clean.append({
                "MÃ MÁY": ma_may,
                "LOẠI MÁY": last_row.get('LOẠI MÁY', ''),
                "TRẠNG THÁI": status,
                "NGÀY NHẬN": d_nhan,
                "KIỂM TRA": last_row.get('KIỂM TRA THỰC TẾ', ''),
                "NỘI BỘ": last_row.get('SỬA NỘI BỘ', ''),
                "BÊN NGOÀI": last_row.get('SỬA BÊN NGOÀI', '')
            })
            
        return pd.DataFrame(data_clean)
    except Exception as e:
        st.error(f"Lỗi xử lý trộn dòng: {e}")
        return pd.DataFrame()

# --- 3. GIAO DIỆN ---
st.title("🏭 TRUY VẤN KHO MIỀN BẮC (FIX TRỘN DÒNG)")

df_mb = load_data_mien_bac_fix_merge()

if not df_mb.empty:
    st.success(f"🎯 Đã đọc thành công {len(df_mb)} thiết bị từ Miền Bắc!")
    
    # KPI
    k1, k2, k3 = st.columns(3)
    k1.metric("Tổng thiết bị", len(df_mb))
    k2.metric("Tồn kho", len(df_mb[df_mb['TRẠNG THÁI'] == "🟡 TRONG KHO"]))
    k3.metric("Thanh lý", len(df_mb[df_mb['TRẠNG THÁI'] == "🔴 THANH LÝ"]))

    # BẢNG DỮ LIỆU
    st.dataframe(df_mb.sort_values('NGÀY NHẬN', ascending=False), use_container_width=True)
else:
    st.error("❌ Vẫn chưa đọc được dữ liệu. Sếp kiểm tra giúp tôi tiêu đề cột 'MÃ SỐ MÁY' có đúng là ô B1 không?")
