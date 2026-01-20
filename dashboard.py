import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="Hệ Thống Kho Real-time V2.5", layout="wide")

# Hàm xóa cache để ép cập nhật dữ liệu
def refresh_data():
    st.cache_data.clear()
    st.toast("🔄 Đang tải dữ liệu mới nhất từ Google Sheets...", icon="✅")

@st.cache_data(ttl=600) # Lưu cache lâu hơn để chạy nhanh, nhưng sẽ bị xóa khi nhấn nút Refresh
def load_data_pro():
    sources = {
        "MIỀN BẮC": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv",
        "ĐÀ NẴNG": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"
    }
    final_df = pd.DataFrame()
    for region, url in sources.items():
        try:
            df_raw = pd.read_csv(url, skiprows=1, header=None, dtype=str).fillna("")
            data_clean = []
            for i in range(1, len(df_raw)):
                row = df_raw.iloc[i]
                ma = str(row[1]).strip()
                if not ma or ma.upper() in ["NAN", "0", "STT"]: continue
                
                kttt = str(row[6]).upper() 
                snb = (str(row[7]) + str(row[8])).upper() 
                sbn = (str(row[9]) + str(row[11])).upper() 
                gl = str(row[13]).upper().strip()
                
                if gl == "R": stt = "DA_TRA"
                elif any(x in (kttt + sbn) for x in ["THANH LÝ", "KHÔNG SỬA", "HỎNG"]): stt = "THANH_LY"
                elif "OK" in (kttt + snb + sbn): stt = "KHO_NHAN"
                elif sbn != "": stt = "SUA_NGOAI"
                else: stt = "DANG_SUA"

                data_clean.append({
                    "VUNG": region, "MA": ma, "STT": stt,
                    "KTTT": row[6], "SBN": sbn, "GL": gl,
                    "LOAI": row[3], "NGAY": row[5]
                })
            final_df = pd.concat([final_df, pd.DataFrame(data_clean)], ignore_index=True)
        except: continue
    return final_df

# --- 2. GIAO DIỆN ĐIỀU KHIỂN ---
col_title, col_ref = st.columns([4, 1])
with col_title:
    st.title("🚀 QUẢN TRỊ KHO TỔNG HỢP V2.5")
with col_ref:
    # Nút bấm cập nhật dữ liệu tức thì
    if st.button("🔄 CẬP NHẬT DỮ LIỆU", use_container_width=True
