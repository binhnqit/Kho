import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CAU HINH ---
st.set_page_config(page_title="He Thong Kho V2.3", layout="wide")

@st.cache_data(ttl=2)
def load_data_final():
    sources = {
        "MIEN BAC": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv",
        "DA NANG": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"
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
                
                # Logic phan loai ngan gon
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

# --- 2. XU LY ---
df = load_data_final()

# --- 3. GIAO DIEN ---
st.title("📊 QUẢN TRỊ KHO & THANH LÝ V2.3")

if not df.empty:
    # Tinh toan bien truoc de tranh loi ngat dong trong metric
    t_nhan = len(df)
    t_tra = len(df[df['STT'] == "DA_TRA"])
    t_tl = len(df[df['STT'] == "THANH_LY"])
    t_ton = t_nhan - t_tra
    
    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("TỔNG NHẬN", t_nhan)
    c2.metric("ĐÃ TRẢ (R)", t_tra)
    c3.metric("THANH LÝ", t_tl)
    c4.metric("TỒN KHO THỰC", t_ton)

    tab1, tab2 = st.tabs(["ĐỐI SOÁT VÙNG", "DANH SÁCH THANH LÝ"])

    with tab1:
        st.subheader("📍 Thống kê theo vùng")
        summary = df.groupby('VUNG').agg(
            Nhan=('MA', 'count'),
            Tra_R=('STT', lambda x: (x == 'DA_TRA').sum()),
            Kho_Nhan=('STT', lambda x: (x == 'KHO_NHAN').sum()),
            Sua_Ngoai=('STT', lambda x: (x == 'SUA_NGOAI').sum()),
            Thanh_Ly=('STT', lambda x: (x == 'THANH_LY').sum())
        ).reset_index()
        st.table(summary)
        
        col_l, col_r = st.columns(2)
        with col_l:
            st.write("**Máy đang sửa ngoài:**")
            st.dataframe(df[df['STT'] == "SUA_NGOAI"][['VUNG','MA','SBN']], use_container_width=True)
        with col_r:
            st.write("**Máy chờ xuất kho (Chờ R):**")
            st.dataframe(df[df['STT'] == "KHO_NHAN"][['VUNG','MA','GL']], use_container_width=True)

    with tab2:
        st.subheader("🔴 Danh sách máy Thanh lý theo vùng")
        df_tl = df[df['STT'] == "THANH_LY"]
        if not df_tl.empty:
            vung_sel = st.multiselect("Chọn vùng:", df_tl['VUNG'].unique(), default=df_tl['VUNG'].unique())
            st.dataframe(df_tl[df_tl['VUNG'].isin(vung_sel)][['VUNG','MA','LOAI','KTTT','SBN','NGAY']], use_container_width=True)
            st.plotly_chart(px.bar(df_tl.groupby('VUNG').size().reset_index(name='SL'), x='VUNG', y='SL', color='VUNG'))
        else:
            st.info("Chưa có máy thanh lý.")
else:
    st.error("Lỗi kết nối dữ liệu.")
