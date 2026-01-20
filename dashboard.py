import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Hệ Thống Quản Trị Kho V2.0", layout="wide")

@st.cache_data(ttl=2)
def load_and_process_pro():
    sources = {
        "MIEN BAC": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv",
        "DA NANG": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"
    }
    final_df = pd.DataFrame()
    now = datetime.now()

    for region, url in sources.items():
        try:
            df_raw = pd.read_csv(url, skiprows=1, header=None, dtype=str).fillna("")
            data_clean = []
            for i in range(1, len(df_raw)):
                row = df_raw.iloc[i]
                ma = str(row[1]).strip()
                if not ma or ma.upper() in ["NAN", "0", "STT"]: continue
                
                # 1. Xử lý ngày nhận & Tính ngày tồn kho
                d_nhan = pd.to_datetime(row[5], dayfirst=True, errors='coerce')
                so_ngay_ton = (now - d_nhan).days if pd.notnull(d_nhan) else 0

                # 2. Lấy dữ liệu các cột kỹ thuật
                kttt = str(row[6]).upper()
                snb = (str(row[7]) + str(row[8])).upper()
                sbn = (str(row[9]) + str(row[11])).upper()
                gl = str(row[13]).upper().strip()

                is_ok = any(x in kttt for x in ["OK"]) or any(x in snb for x in ["OK"]) or any(x in sbn for x in ["OK"])
                is_r = (gl == "R")

                # 3. Phân loại trạng thái chuyên sâu
                if is_r:
                    stt = "🟢 ĐÃ TRẢ ĐI (R)"
                elif is_ok and not is_r:
                    stt = "🔵 KHO NHẬN (CHỜ R)"
                elif any(x in kttt for x in ["THANH LÝ", "KHÔNG SỬA"]) or any(x in sbn for x in ["THANH LÝ", "KHÔNG SỬA"]):
                    stt = "🔴 THANH LÝ"
                else:
                    stt = "🟡 ĐANG XỬ LÝ"

                data_clean.append({
                    "MIỀN": region,
                    "MÃ MÁY": ma,
                    "LOẠI MÁY": row[3],
                    "TRẠNG THÁI": stt,
                    "NGÀY NHẬN": d_nhan,
                    "SỐ NGÀY TỒN": so_ngay_ton,
                    "GHI CHÚ": row[6] if row[6] else sbn,
                    "XÁC NHẬN": gl
                })
            final_df = pd.concat([final_df, pd.DataFrame(data_clean)], ignore_index=True)
        except: continue
    return final_df

# --- GIAO DIỆN CHUYÊN GIA ---
st.title("🛡️ QUẢN TRỊ KHO V2.0 - CHỐNG THẤT THOÁT")
df = load_and_process_pro()

if not df.empty:
    # KPI CHUYÊN SÂU
    t_nhan = len(df)
    t_ton_kho = len(df[df['TRẠNG THÁI'] != "🟢 ĐÃ TRẢ ĐI (R)"])
    t_ngam_lau = len(df[(df['TRẠNG THÁI'] == "🔵 KHO NHẬN (CHỜ R)") & (df['SỐ NGÀY TỒN'] > 3)])
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tổng Nhận Toàn Hệ Thống", t_nhan)
    m2.metric("Thực Tồn Tại Kho (Chưa R)", t_ton_kho)
    m3.metric("Cảnh Báo Ngâm Máy (>3 ngày)", t_ngam_lau, delta="Cần xử lý ngay", delta_color="inverse")
    m4.metric("Vòng Quay Kho (Avg Days)", round(df[df['TRẠNG THÁI'] != "🟢 ĐÃ TRẢ ĐI (R)"]['SỐ NGÀY TỒN'].mean(), 1))

    # DANH SÁCH CẢNH BÁO ĐỎ
    if t_ngam_lau > 0:
        st.error(f"🚨 PHÁT HIỆN {t_ngam_lau} THIẾT BỊ ĐÃ XỬ LÝ XONG NHƯNG CHƯA XUẤT KHO TRÊN 3 NGÀY")
        st.dataframe(df[(df['TRẠNG THÁI'] == "🔵 KHO NHẬN (CHỜ R)") & (df['SỐ NGÀY TỒN'] > 3)].sort_values('SỐ NGÀY TỒN', ascending=False), use_container_width=True)

    st.write("---")
    
    # BIỂU ĐỒ PHÂN TÍCH LỨA TUỔI HÀNG TỒN (AGING)
    col1, col2 = st.columns(2)
    with col1:
        fig_pie = px.pie(df, names='TRẠNG THÁI', title="Cơ cấu tồn kho thực tế", hole=0.4,
                         color_discrete_map={"🟢 ĐÃ TRẢ ĐI (R)":"#2ecc71","🔵 KHO NHẬN (CHỜ R)":"#3498db","🔴 THANH LÝ":"#e74c3c","🟡 ĐANG XỬ LÝ":"#f1c40f"})
        st.plotly_chart(fig_pie, use_container_width=True)
    with col2:
        df_aging = df[df['TRẠNG THÁI'] != "🟢 ĐÃ TRẢ ĐI (R)"]
        fig_hist = px.histogram(df_aging, x="SỐ NGÀY TỒN", color="MIỀN", title="Phân bổ thời gian máy nằm tại xưởng",
                               labels={"SỐ NGÀY TỒN": "Số ngày nằm kho"}, barmode="group")
        st.plotly_chart(fig_hist, use_container_width=True)

    # BẢNG TRA CỨU TỔNG HỢP
    st.subheader("🔍 Tra cứu dữ liệu toàn hệ thống")
    st.dataframe(df.sort_values(['SỐ NGÀY TỒN', 'TRẠNG THÁI'], ascending=[False, True]), use_container_width=True)
else:
    st.error("Hệ thống đang kiểm tra lại luồng dữ liệu...")
