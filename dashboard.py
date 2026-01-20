import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CAU HINH ---
st.set_page_config(page_title="Quan Ly Kho Chuan Hoa V1.2", layout="wide")

@st.cache_data(ttl=2)
def load_and_fix_logic():
    sources = {
        "MIEN BAC": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv",
        "DA NANG": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"
    }
    final_df = pd.DataFrame()
    for region, url in sources.items():
        try:
            df = pd.read_csv(url, skiprows=1, dtype=str).fillna("")
            df.columns = [str(c).strip().upper() for c in df.columns]
            df = df.replace(r'^\s*$', pd.NA, regex=True)
            
            # Forward Fill de xu ly tron dong
            if 'MÃ SỐ MÁY' in df.columns:
                df['MÃ SỐ MÁY'] = df['MÃ SỐ MÁY'].ffill()
                for c in ['NGÀY NHẬN', 'SỬA NỘI BỘ', 'SỬA BÊN NGOÀI', 'NGÀY TRẢ', 'HƯ KHÔNG SỬA ĐƯỢC']:
                    if c in df.columns: df[c] = df[c].ffill()

            clean_list = []
            for _, row in df.iterrows():
                ma = str(row.get('MÃ SỐ MÁY', '')).strip()
                if not ma or ma.upper() in ["NAN", "STT", "0"]: continue
                
                # Lay cac cot du lieu goc
                sua_nb = str(row.get('SỬA NỘI BỘ', '')).strip()
                sua_ngoai = str(row.get('SỬA BÊN NGOÀI', '')).strip()
                hu_hong = str(row.get('HƯ KHÔNG SỬA ĐƯỢC', '')).strip()
                ngay_tra = str(row.get('NGÀY TRẢ', '')).strip()
                giao_lai = str(row.get('GIAO LẠI MIỀN BẮC', '') if region == "MIEN BAC" else row.get('GIAO LẠI ĐN', '')).upper()

                # --- LOGIC PHAN LOAI MOI ---
                if hu_hong != "": 
                    status = "🔴 THANH LY"
                elif ngay_tra != "" or any(x in giao_lai for x in ["OK", "XONG"]):
                    status = "🟢 DA XONG"
                elif sua_nb != "" or sua_ngoai != "":
                    status = "🟡 DANG SUA"
                else:
                    status = "⚪ CHO KIEM TRA"

                clean_list.append({
                    "CHI NHANH": region,
                    "MA MAY": ma,
                    "TRANG THAI": status,
                    "NGAY NHAN": pd.to_datetime(row.get('NGÀY NHẬN', ''), dayfirst=True, errors='coerce'),
                    "LOAI MAY": row.get('LOẠI MÁY', ''),
                    "KIEM TRA": row.get('KIỂM TRA THỰC TẾ', ''),
                    "GHI CHU": sua_nb if sua_nb else sua_ngoai
                })
            final_df = pd.concat([final_df, pd.DataFrame(clean_list)], ignore_index=True)
        except: continue
    return final_df

# --- 2. HIEN THI ---
df = load_and_fix_logic()
st.title("🏭 HE THONG QUAN TRI KHO - CHUAN HOA TRANG THAI")

if not df.empty:
    # Sidebar Filters
    with st.sidebar:
        st.header("BO LOC")
        sel_region = st.multiselect("Chi nhanh", df['CHI NHANH'].unique(), default=df['CHI NHANH'].unique())
        sel_status = st.multiselect("Trang thai", df['TRANG THAI'].unique(), default=df['TRANG THAI'].unique())
        df_view = df[(df['CHI NHANH'].isin(sel_region)) & (df['TRANG THAI'].isin(sel_status))]

    # KPI Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tong may", len(df_view))
    m2.metric("Dang sua", len(df_view[df_view['TRANG THAI'] == "🟡 DANG SUA"]))
    m3.metric("Da xong", len(df_view[df_view['TRANG THAI'] == "🟢 DA XONG"]))
    m4.metric("Thanh ly", len(df_view[df_view['TRANG THAI'] == "🔴 THANH LY"]))

    # Chart
    st.plotly_chart(px.bar(df_view.groupby(['CHI NHANH', 'TRANG THAI']).size().reset_index(name='SL'), 
                           x='CHI NHANH', y='SL', color='TRANG THAI', barmode='group',
                           color_discrete_map={"🔴 THANH LY":"red","🟢 DA XONG":"green","🟡 DANG SUA":"orange","⚪ CHO KIEM TRA":"gray"}), use_container_width=True)

    # Data Table
    st.subheader("📋 Danh sach thiet bi")
    st.dataframe(df_view.sort_values('NGAY NHAN', ascending=False), use_container_width=True)
else:
    st.info("Dang tai du lieu...")
