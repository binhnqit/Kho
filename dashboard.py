import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 1. CAU HINH ---
st.set_page_config(page_title="Hệ Thống Đối Soát V2.2", layout="wide")

@st.cache_data(ttl=2)
def load_and_audit_v22():
    sources = {
        "MIỀN BẮC": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv",
        "ĐÀ NẴNG": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"
    }
    final_df = pd.DataFrame()
    for region, url in sources.items():
        try:
            # Doc du lieu tu dong 2
            df_raw = pd.read_csv(url, skiprows=1, header=None, dtype=str).fillna("")
            data_clean = []
            for i in range(1, len(df_raw)):
                row = df_raw.iloc[i]
                ma = str(row[1]).strip()
                if not ma or ma.upper() in ["NAN", "0", "STT"]: continue
                
                # Mapping cot theo chi dinh cua sep
                kttt = str(row[6]).upper() # G
                snb = (str(row[7]) + str(row[8])).upper() # H, I
                sbn = (str(row[9]) + str(row[11])).upper() # J, L
                gl = str(row[13]).upper().strip() # N
                
                is_r = (gl == "R")
                is_ok = any(x in (kttt + snb + sbn) for x in ["OK"])
                is_tl = any(x in (kttt + sbn) for x in ["THANH LÝ", "KHÔNG SỬA", "HỎNG"])

                # Logic Phan loai
                if is_r: stt = "🟢 ĐÃ TRẢ (R)"
                elif is_tl: stt = "🔴 THANH LÝ"
                elif is_ok and not is_r: stt = "🔵 KHO NHẬN (CHỜ R)"
                elif sbn != "" and "OK" not in sbn: stt = "🟠 ĐANG SỬA NGOÀI"
                else: stt = "🟡 ĐANG XỬ LÝ"

                data_clean.append({
                    "VÙNG": region, "MÃ MÁY": ma, "TRẠNG THÁI": stt,
                    "KTTT": row[6], "SỬA NGOÀI": sbn, "GIAO LẠI": gl,
                    "LOẠI MÁY": row[3], "NGÀY NHẬN": row[5]
                })
            final_df = pd.concat([final_df, pd.DataFrame(data_clean)], ignore_index=True)
        except: continue
    return final_df

# --- 2. XU LY DU LIEU ---
df = load_and_audit_v22()

# --- 3. GIAO DIEN ---
st.title("🚀 HỆ THỐNG ĐỐI SOÁT & QUẢN TRỊ THANH LÝ V2.2")

if not df.empty:
    # --- TAB CHINH ---
    tab1, tab2 = st.tabs(["📊 ĐỐI SOÁT TỔNG HỢP", "🔴 DANH SÁCH THANH LÝ"])

    with tab1:
        # Thong ke theo Vung
        summary = df.groupby('VÙNG').agg(
            Tong_Nhan=('MÃ MÁY', 'count'),
            Sua_Ngoai=('TRẠNG THÁI', lambda x: (x == '🟠 ĐANG SỬA NGOÀI').sum()),
            Kho_Nhan=('TRẠNG THÁI', lambda x: (x == '🔵 KHO NHẬN (CHỜ R)').sum()),
            Da_Tra=('TRẠNG THÁI', lambda x: (x == '🟢 ĐÃ TRẢ (R)').sum()),
            Thanh_Ly=('TRẠNG THÁI', lambda x: (x == '🔴 THANH LÝ').sum())
        ).reset_index()
        st.subheader("📍 Thống kê trạng thái theo Miền")
        st.table(summary)

        # Doi chieu Logic
        st.write("---")
        c1, c2, c3 = st.columns(3)
        c1.metric("TỔNG NHẬN", len(df))
        c2.metric("TỔNG GIAO (R)", len(df[df['
