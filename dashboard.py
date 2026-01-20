import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Doi Soat Kho V1.6", layout="wide")

@st.cache_data(ttl=2)
def load_and_process_v16():
    sources = {
        "MIEN BAC": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv",
        "DA NANG": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"
    }
    final_df = pd.DataFrame()
    for region, url in sources.items():
        try:
            # Doc du lieu tu dong 2
            df_raw = pd.read_csv(url, skiprows=1, header=None, dtype=str).fillna("")
            data_clean = []
            for i in range(1, len(df_raw)):
                row = df_raw.iloc[i]
                ma = str(row[1]).strip() # Cot B
                if not ma or ma.upper() in ["NAN", "0", "MÃ SỐ MÁY"]: continue
                
                kttt = str(row[6]).upper()  # Cot G
                sbn = (str(row[9]) + str(row[11])).upper() # Cot J, L
                gl = str(row[13]).upper().strip() # Cot N: "GIAO LAI"
                
                # --- LOGIC CHUẨN THEO SẾP CHỈ ĐẠO ---
                
                # 1. ƯU TIÊN CAO NHẤT: Nếu cột N là "R" -> ĐÃ TRẢ VỀ CHI NHÁNH
                if gl == "R":
                    stt = "GREEN_R" 
                
                # 2. Nếu không phải R, nhưng có từ khóa Thanh lý/Không sửa được -> THANH LÝ
                elif any(x in kttt for x in ["THANH LÝ", "KHÔNG SỬA"]) or \
                     any(x in sbn for x in ["THANH LÝ", "KHÔNG SỬA"]):
                    stt = "RED_TL"
                
                # 3. Nếu không phải R, nhưng Sửa bên ngoài báo OK -> KHO NHẬN (Đợi giao)
                elif "OK" in sbn:
                    stt = "BLUE_KHO"
                
                # 4. Còn lại là đang xử lý
                else:
                    stt = "YELLOW_SUA"

                data_clean.append({
                    "CHI_NHANH": region, 
                    "MA_MAY": ma, 
                    "STT_CODE": stt,
                    "KTTT": row[6],
                    "SBN": sbn,
                    "GIAO_LAI": gl
                })
            final_df = pd.concat([final_df, pd.DataFrame(data_clean)], ignore_index=True)
        except: continue
    return final_df

# --- GIAO DIEN THONG KE ---
st.title("📊 HỆ THỐNG ĐỐI SOÁT V1.6 (ƯU TIÊN CỘT N: 'R')")
df = load_and_process_v16()

if not df.empty:
    # Bang thong ke tom tat
    summary = df.groupby('CHI_NHANH').agg(
        Tong_Nhan=('MA_MAY', 'count'),
        Da_Tra_Ve_R=('STT_CODE', lambda x: (x == 'GREEN_R').sum()),
        Thanh_Ly=('STT_CODE', lambda x: (x == 'RED_TL').sum()),
        Kho_Nhan_Cho_R=('STT_CODE', lambda x: (x == 'BLUE_KHO').sum()),
        Dang_Xu_Ly=('STT_CODE', lambda x: (x == 'YELLOW_SUA').sum())
    ).reset_index()
    
    # Thuc Nhan = Tong - Thanh Ly - Da Tra R (May dang thuc te nam tai kho ky thuat)
    summary['Dang_Tai_Kho_KT'] = summary['Tong_Nhan'] - summary['Da_Tra_Ve_R'] - summary['Thanh_Ly']

    st.subheader("📝 Bảng số liệu đối soát theo Miền")
    st.table(summary)

    # Metrics tong quat
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng Nhận", summary['Tong_Nhan'].sum())
    c2.metric("Đã Trả Miền (R)", summary['Da_Tra_Ve_R'].sum())
    c3.metric("Tổng Thanh Lý", summary['Thanh_Ly'].sum())
    c4.metric("Đang tại Kho KT", summary['Dang_Tai_Kho_KT'].sum())

    # Bieu do
    st.write("---")
    fig = px.bar(summary, x='CHI_NHANH', y=['Da_Tra_Ve_R', 'Thanh_Ly', 'Kho_Nhan_Cho_R', 'Dang_Xu_Ly'],
                 title="Phân tích luồng máy qua cột Giao Lại (N)", barmode='stack')
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Kiểm tra danh sách máy 'Đã Trả Miền (R)'"):
        st.dataframe(df[df['STT_CODE'] == "GREEN_R"], use_container_width=True)
else:
    st.error("Lỗi kết nối dữ liệu.")
