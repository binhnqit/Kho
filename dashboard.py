import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="Kho Miền Bắc V1.0.5", layout="wide")

@st.cache_data(ttl=2)
def load_data_mien_bac():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv"
    try:
        # Đọc từ dòng 2, ép kiểu string
        df = pd.read_csv(url, skiprows=1, dtype=str).fillna("")
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        # Xử lý trộn dòng bằng ffill
        df = df.replace(r'^\s*$', pd.NA, regex=True)
        if 'MÃ SỐ MÁY' in df.columns:
            df['MÃ SỐ MÁY'] = df['MÃ SỐ MÁY'].ffill()
        
        clean_list = []
        for _, row in df.iterrows():
            ma = str(row.get('MÃ SỐ MÁY', '')).strip()
            if not ma or ma.upper() in ["NAN", "STT", "MÃ SỐ MÁY", "0"]:
                continue
            
            # Xử lý ngày và trạng thái
            d_nhan = pd.to_datetime(row.get('NGÀY NHẬN', ''), dayfirst=True, errors='coerce')
            d_tra = pd.to_datetime(row.get('NGÀY TRẢ', ''), dayfirst=True, errors='coerce')
            
            sua_nb = str(row.get('SỬA NỘI BỘ', '')).upper()
            hu_hong = str(row.get('HƯ KHÔNG SỬA ĐƯỢC', '')).strip()
            giao_lai = str(row.get('GIAO LẠI MIỀN BẮC', '')).upper()
            
            # Logic phân loại
            status = "🟡 TRONG KHO"
            if "THANH LÝ" in sua_nb or hu_hong != "":
                status = "🔴 THANH LÝ"
            elif pd.notnull(d_tra) or "OK" in giao_lai or "XONG" in giao_lai:
                status = "🟢 ĐÃ XONG"

            clean_list.append({
                "MÃ MÁY": ma,
                "TRẠNG THÁI": status,
                "NGÀY NHẬN": d_nhan,
                "LOẠI MÁY": row.get('LOẠI MÁY', ''),
                "KIỂM TRA": row.get('KIỂM TRA THỰC TẾ', ''),
                "NỘI BỘ": row.get('SỬA NỘI BỘ', ''),
                "BÊN NGOÀI": row.get('SỬA BÊN NGOÀI', '')
            })
        return pd.DataFrame(clean_list)
    except Exception as e:
        st.error(f"Lỗi: {e}")
        return pd.DataFrame()

# --- 3. HIỂN THỊ DASHBOARD ---
st.title("🏭 KHO MIỀN BẮC - TRUY VẤN DÒNG 2")

df_mb = load_data_mien_bac()

if not df_mb.empty:
    # KPI - Sửa lỗi ngắt dòng ở đây
    k1, k2, k3 = st.columns(3)
    k1.metric("Tổng thiết bị", len(df_mb))
    k2.metric("Đang tồn kho", len(df_mb[df_mb['TRẠNG THÁI'] == "🟡 TRONG KHO"]))
    k3.metric("Đã hoàn tất", len(df_mb[df_mb['TRẠNG THÁI'] == "🟢 ĐÃ XONG"]))

    # Bảng dữ liệu
    st.subheader("📋 Bảng kê chi tiết")
    st.dataframe(df_mb, use_container_width=True)
    
    # Biểu đồ
    st.plotly_chart(px.pie(df_mb, names='TRẠNG THÁI', title="Cơ cấu kho"), use_container_width=True)
else:
    st.info("Chưa
