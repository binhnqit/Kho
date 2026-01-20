import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Đối Soát Kho Chuyên Sâu V2.1", layout="wide")

@st.cache_data(ttl=2)
def load_and_audit():
    sources = {
        "MIỀN BẮC": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv",
        "ĐÀ NẴNG": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"
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
                
                # 1. Dữ liệu gốc
                kttt = str(row[6]).upper()  # Cột G: Kiểm tra TT
                snb = (str(row[7]) + str(row[8])).upper() # Cột H, I: Nội bộ
                sbn = (str(row[9]) + str(row[11])).upper() # Cột J, L: Bên ngoài
                gl = str(row[13]).upper().strip() # Cột N: Giao lại

                # 2. Phân loại chi tiết để thống kê
                is_r = (gl == "R")
                is_ok_ngoai = "OK" in sbn
                is_ok_tong = "OK" in kttt or "OK" in snb or is_ok_ngoai
                is_thanh_ly = any(x in kttt or x in sbn for x in ["THANH LÝ", "KHÔNG SỬA", "HỎNG"])

                if is_r:
                    stt = "🟢 ĐÃ TRẢ (R)"
                elif is_ok_tong and not is_r:
                    stt = "🔵 KHO NHẬN (ĐỢI R)"
                elif not is_ok_tong and "OK" not in sbn and sbn != "" and not is_thanh_ly:
                    stt = "🟠 ĐANG SỬA NGOÀI"
                elif is_thanh_ly:
                    stt = "🔴 THANH LÝ"
                else:
                    stt = "🟡 ĐANG KIỂM TRA/NB"

                data_clean.append({
                    "VÙNG": region,
                    "MÃ MÁY": ma,
                    "TRẠNG THÁI": stt,
                    "SỬA NGOÀI": sbn,
                    "GIAO LẠI": gl,
                    "NGÀY NHẬN": pd.to_datetime(row[5], dayfirst=True, errors='coerce'),
                    "LOẠI MÁY": row[3]
                })
            final_df = pd.concat([final_df, pd.DataFrame(data_clean)], ignore_index=True)
        except: continue
    return final_df

df = load_audit()

# --- GIAO DIỆN THỐNG KÊ ---
st.title("🚀 TRUNG TÂM ĐIỀU HÀNH & ĐỐI SOÁT TỔNG HỢP")

if not df.empty:
    # 1. THỐNG KÊ THEO VÙNG (Yêu cầu 1)
    st.subheader("📍 1. Thống kê theo vùng Miền")
    summary = df.groupby('VÙNG').agg(
        Tong_Nhan=('MÃ MÁY', 'count'),
        Dang_Sua_Ngoai=('TRẠNG THÁI', lambda x: (x == '🟠 ĐANG SỬA NGOÀI').sum()),
        Kho_Nhan_Doi_R=('TRẠNG THÁI', lambda x: (x == '🔵 KHO NHẬN (ĐỢI R)').sum()),
        Da_Tra_Xong=('TRẠNG THÁI', lambda x: (x == '🟢 ĐÃ TRẢ (R)').sum()),
        Thanh_Ly=('TRẠNG THÁI', lambda x: (x == '🔴 THANH LÝ').sum())
    ).reset_index()
    summary['Thực_Tồn_Tại_Kho'] = summary['Tong_Nhan'] - summary['Da_Tra_Xong']
    st.table(summary)

    # 2. PHÂN TÍCH ĐANG SỬA NGOÀI (Yêu cầu 2)
    st.write("---")
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("🛠️ 2. Máy đang sửa ngoài")
        df_ngoai = df[df['TRẠNG THÁI'] == '🟠 ĐANG SỬA NGOÀI']
        st.metric("Tổng máy đang ở tiệm ngoài", len(df_ngoai))
        if not df_ngoai.empty:
            st.dataframe(df_ngoai[['VÙNG', 'MÃ MÁY', 'SỬA NGOÀI', 'NGÀY NHẬN']], use_container_width=True)

    # 3. MÁY NẰM Ở KHO NHẬN (Yêu cầu 3)
    with col_b:
        st.subheader("📦 3. Đang nằm ở Kho nhận (Chờ R)")
        df_kho = df[df['TRẠNG THÁI'] == '🔵 KHO NHẬN (ĐỢI R)']
        st.metric("Máy sửa xong chưa xuất kho", len(df_kho), delta_color="inverse")
        if not df_kho.empty:
            st.dataframe(df_kho[['VÙNG', 'MÃ MÁY', 'GIAO LẠI', 'LOẠI MÁY']], use_container_width=True)

    # 4. ĐỐI CHIẾU NHẬN VÀO - GIAO RA (Yêu cầu 4)
    st.write("---")
    st.subheader("⚖️ 4. Đối chiếu Nhận vào - Giao ra (Logistics Balance)")
    
    total_in = len(df)
    total_out = len(df[df['TRẠNG THÁI'] == '🟢 ĐÃ TRẢ (R)'])
    total_loss = len(df[df['TRẠNG THÁI'] == '🔴 THANH LÝ'])
    current_stock = total_in - total_out - total_loss

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("TỔNG NHẬN VÀO", total_in)
    c2.metric("TỔNG GIAO RA (R)", total_out, delta="Đã xuất kho")
    c3.metric("KHẤU HAO (THANH LÝ)", total_loss)
    c4.metric("TỒN KHO THỰC TẾ", current_stock, delta="Máy đang tại xưởng", delta_color="off")

    # Biểu đồ dòng chảy thiết bị
    fig_flow = px.funnel_area(
        names=["Nhận vào", "Tồn tại xưởng", "Đã trả (R)", "Thanh lý"],
        values=[total_in, current_stock, total_out, total_loss],
        title="Biểu đồ dòng chảy thiết bị (Input -> Output)"
    )
    st.plotly_chart(fig_flow, use_container_width=True)

else:
    st.warning("Đang kết nối dữ liệu từ Google Sheets...")
