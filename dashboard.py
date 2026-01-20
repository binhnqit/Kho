import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CAU HINH ---
st.set_page_config(page_title="Kho Logistics V1.3.1", layout="wide")

@st.cache_data(ttl=2)
def load_and_process_logic():
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
            if 'MÃ SỐ MÁY' in df.columns:
                for c in ['MÃ SỐ MÁY','NGÀY NHẬN','LOẠI MÁY','KIỂM TRA THỰC TẾ','SỬA NỘI BỘ','SỬA BÊN NGOÀI']:
                    if c in df.columns: df[c] = df[c].ffill()
            clean_list = []
            for _, row in df.iterrows():
                ma = str(row.get('MÃ SỐ MÁY', '')).strip()
                if not ma or ma.upper() in ["NAN", "STT", "0"]: continue
                kt_tt = str(row.get('KIỂM TRA THỰC TẾ', '')).upper()
                s_ngoai = str(row.get('SỬA BÊN NGOÀI', '')).upper()
                hu_hong = str(row.get('HƯ KHÔNG SỬA ĐƯỢC', '')).upper()
                col_gl = 'GIAO LẠI MIỀN BẮC' if region == "MIEN BAC" else 'GIAO LẠI ĐN'
                gl = str(row.get(col_gl, '')).upper().strip()
                
                # Logic phan loai
                if any(x in kt_tt for x in ["THANH LÝ","KHÔNG SỬA"]) or any(x in s_ngoai for x in ["THANH LÝ","KHÔNG SỬA"]) or hu_hong != "":
                    stt = "RED_TL" # THANH LY
                elif (("OK" in kt_tt) or ("OK" in s_ngoai)) and (gl == "R"):
                    stt = "GREEN_TRA" # DA TRA VE
                elif ("OK" in s_ngoai) and (gl != "R"):
                    stt = "BLUE_KHO" # KHO NHAN
                else:
                    stt = "YELLOW_SUA" # DANG XU LY
                
                clean_list.append({"CHI NHANH": region, "MA MAY": ma, "STATUS": stt, "NGAY NHAN": pd.to_datetime(row.get('NGÀY NHẬN', ''), dayfirst=True, errors='coerce'), "LOAI": row.get('LOẠI MÁY', ''), "GIAO LAI": gl})
            final_df = pd.concat([final_df, pd.DataFrame(clean_list)], ignore_index=True)
        except: continue
    return final_df

# --- 2. GIAO DIEN ---
st.title("🏭 QUẢN TRỊ KHO V1.3.1 - LOGISTICS FLOW")
df = load_and_process_logic()

if not df.empty:
    # Metric tinh toan
    t_nhan = len(df)
    t_tl = len(df[df['STATUS'] == "RED_TL"])
    t_tra = len(df[df['STATUS'] == "GREEN_TRA"])
    t_kho = len(df[df['STATUS'] == "BLUE_KHO"])
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng Máy Nhận", t_nhan)
    c2.metric("Thanh Lý", t_tl)
    c3.metric("Thực Nhận (Vận hành)", t_nhan - t_tl)
    c4.metric("Đã Trả Miền", t_tra)

    st.info(f"🚩 Kho Nhận (Đối chiếu): {t_kho} máy đã sửa OK nhưng chưa có dấu 'R'")

    # Bieu do - Viet gon de tranh loi Syntax
    m_color = {"RED_TL":"red", "GREEN_TRA":"green", "BLUE_KHO":"blue", "YELLOW_SUA":"orange"}
    fig = px.pie(df, names='STATUS', title="Tỷ lệ Kho", color='STATUS', color_discrete_map=m_color)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Chi tiết danh sách")
    st.dataframe(df.sort_values('NGAY NHAN', ascending=False), use_container_width=True)
else:
    st.warning("Dang ket noi...")
