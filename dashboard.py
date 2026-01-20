import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Thong Ke Doi Soat Kho", layout="wide")

@st.cache_data(ttl=2)
def load_and_process_v15():
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
                ma = str(row[1]).strip() # Cot B
                if not ma or ma.upper() in ["NAN", "0", "MÃ SỐ MÁY"]: continue
                
                kttt = str(row[6]).upper()  # Cot G
                snb = (str(row[7]) + str(row[8])).upper() # Cot H, I
                sbn = (str(row[9]) + str(row[11])).upper() # Cot J, L
                gl = str(row[13]).upper().strip() # Cot N
                
                keywords_tl = ["THANH LÝ", "KHÔNG SỬA", "HỎNG"]
                if any(x in kttt for x in keywords_tl) or any(x in sbn for x in keywords_tl):
                    stt = "THANH_LY"
                elif (("OK" in kttt) or ("OK" in sbn)) and (gl == "R"):
                    stt = "DA_TRA_VE"
                elif ("OK" in sbn) and (gl != "R"):
                    stt = "KHO_NHAN"
                else:
                    stt = "DANG_XU_LY"

                data_clean.append({"CHI_NHANH": region, "MA_MAY": ma, "STT": stt})
            final_df = pd.concat([final_df, pd.DataFrame(data_clean)], ignore_index=True)
        except: continue
    return final_df

# --- HIEN THI ---
st.title("📊 BÁO CÁO ĐỐI SOÁT KHO TỔNG HỢP")
df = load_and_process_v15()

if not df.empty:
    # 1. BANG THONG KE TONG HOP
    st.subheader("📝 1. Bảng số liệu tổng hợp theo Miền")
    
    # Tao bang thong ke
    summary = df.groupby('CHI_NHANH').agg(
        Tong_Nhan=('MA_MAY', 'count'),
        Thanh_Ly=('STT', lambda x: (x == 'THANH_LY').sum()),
        Da_Tra_R=('STT', lambda x: (x == 'DA_TRA_VE').sum()),
        Kho_Nhan_Doi_Chieu=('STT', lambda x: (x == 'KHO_NHAN').sum()),
        Dang_Sua_Kiem_Tra=('STT', lambda x: (x == 'DANG_XU_LY').sum())
    ).reset_index()
    
    # Tinh toan Thuc Nhan = Tong - Thanh Ly
    summary['Thuc_Nhan_Van_Hanh'] = summary['Tong_Nhan'] - summary['Thanh_Ly']
    
    # Sap xep lai cot cho de nhìn
    summary = summary[['CHI_NHANH', 'Tong_Nhan', 'Thanh_Ly', 'Thuc_Nhan_Van_Hanh', 'Da_Tra_R', 'Kho_Nhan_Doi_Chieu', 'Dang_Sua_Kiem_Tra']]
    
    # Hien thi bang summary
    st.table(summary)

    # 2. TONG CONG TOAN HE THONG
    st.subheader("🌎 2. Tổng cộng toàn hệ thống")
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Tổng Nhận 2 Miền", summary['Tong_Nhan'].sum())
    t2.metric("Tổng Thanh Lý", summary['Thanh_Ly'].sum())
    t3.metric("Thực Nhận Toàn Hệ Thống", summary['Thuc_Nhan_Van_Hanh'].sum())
    t4.metric("Tổng Đã Trả (R)", summary['Da_Tra_R'].sum())

    # 3. BIỂU ĐỒ SO SÁNH
    st.write("---")
    fig_compare = px.bar(summary, x='CHI_NHANH', 
                         y=['Da_Tra_R', 'Kho_Nhan_Doi_Chieu', 'Dang_Sua_Kiem_Tra', 'Thanh_Ly'],
                         title="So sánh trạng thái giữa 2 Miền",
                         barmode='group')
    st.plotly_chart(fig_compare, use_container_width=True)

    # 4. DANH SACH CHI TIET
    with st.expander("Xem danh sách chi tiết để đối soát từng mã máy"):
        st.dataframe(df, use_container_width=True)
else:
    st.error("Chưa có dữ liệu. Sếp hãy kiểm tra lại kết nối Sheets.")
