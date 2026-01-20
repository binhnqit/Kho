import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CAU HINH ---
st.set_page_config(page_title="Kho Mien Bac V1.0.6", layout="wide")

@st.cache_data(ttl=2)
def load_data_mien_bac():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv"
    try:
        # Doc tu dong 2, ep kieu string
        df = pd.read_csv(url, skiprows=1, dtype=str).fillna("")
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        # Xu ly tron dong bang ffill
        df = df.replace(r'^\s*$', pd.NA, regex=True)
        if 'MÃ SỐ MÁY' in df.columns:
            df['MÃ SỐ MÁY'] = df['MÃ SỐ MÁY'].ffill()
        
        clean_list = []
        for _, row in df.iterrows():
            ma = str(row.get('MÃ SỐ MÁY', '')).strip()
            if not ma or ma.upper() in ["NAN", "STT", "MÃ SỐ MÁY", "0"]:
                continue
            
            d_nhan = pd.to_datetime(row.get('NGÀY NHẬN', ''), dayfirst=True, errors='coerce')
            d_tra = pd.to_datetime(row.get('NGÀY TRẢ', ''), dayfirst=True, errors='coerce')
            
            sua_nb = str(row.get('SỬA NỘI BỘ', '')).upper()
            hu_hong = str(row.get('HƯ KHÔNG SỬA ĐƯỢC', '')).strip()
            giao_lai = str(row.get('GIAO LẠI MIỀN BẮC', '')).upper()
            
            # Phan loai trang thai don gian de tranh loi syntax
            status = "TON KHO"
            if "THANH LY" in sua_nb or hu_hong != "":
                status = "THANH LY"
            elif pd.notnull(d_tra) or "OK" in giao_lai or "XONG" in giao_lai:
                status = "DA XONG"

            clean_list.append({
                "MA MAY": ma,
                "TRANG THAI": status,
                "NGAY NHAN": d_nhan,
                "LOAI MAY": row.get('LOẠI MÁY', ''),
                "KIEM TRA": row.get('KIỂM TRA THỰC TẾ', ''),
                "NOI BO": row.get('SỬA NỘI BỘ', ''),
                "NGOAI": row.get('SỬA BÊN NGOÀI', '')
            })
        return pd.DataFrame(clean_list)
    except Exception as e:
        st.error(f"Loi: {e}")
        return pd.DataFrame()

# --- 3. HIEN THI ---
st.title("HE THONG QUAN LY KHO MIEN BAC")

df_mb = load_data_mien_bac()

if not df_mb.empty:
    # KPI
    k1, k2, k3 = st.columns(3)
    k1.metric("Tong thiet bi", len(df_mb))
    k2.metric("Dang ton kho", len(df_mb[df_mb['TRANG THAI'] == "TON KHO"]))
    k3.metric("Da hoan tat", len(df_mb[df_mb['TRANG THAI'] == "DA XONG"]))

    # Bang du lieu
    st.subheader("Danh sach chi tiet")
    st.dataframe(df_mb, use_container_width=True)
    
    # Bieu do
    fig = px.pie(df_mb, names='TRANG THAI', title="Co cau kho")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("He thong dang cho du lieu tu Sheets...")
