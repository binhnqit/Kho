import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Quan Ly Kho OK-R V1.7", layout="wide")

@st.cache_data(ttl=2)
def load_and_process_v17():
    sources = {
        "MIEN BAC": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv",
        "DA NANG": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"
    }
    final_df = pd.DataFrame()
    for region, url in sources.items():
        try:
            # Đọc dữ liệu từ dòng 2
            df_raw = pd.read_csv(url, skiprows=1, header=None, dtype=str).fillna("")
            data_clean = []
            for i in range(1, len(df_raw)):
                row = df_raw.iloc[i]
                ma = str(row[1]).strip() # Cột B
                if not ma or ma.upper() in ["NAN", "0", "MÃ SỐ MÁY"]: continue
                
                kttt = str(row[6]).upper()  # Cột G
                snb = (str(row[7]) + str(row[8])).upper() # Cột H, I
                sbn = (str(row[9]) + str(row[11])).upper() # Cột J, L
                gl = str(row[13]).upper().strip() # Cột N: Giao lại

                # Kiểm tra trạng thái sửa xong (OK) ở bất kỳ cột kỹ thuật nào
                is_ok = any(x in kttt for x in ["OK"]) or any(x in snb for x in ["OK"]) or any(x in sbn for x in ["OK"])
                # Kiểm tra trạng thái đã trả đi (R)
                is_returned = (gl == "R")

                # --- LOGIC PHÂN LOẠI THEO QUY TRÌNH SẾP DUYỆT ---
                if is_returned:
                    stt = "🟢 ĐÃ TRẢ ĐI (R)"
                elif is_ok and not is_returned:
                    stt = "🔵 CÒN TRONG KHO (CHỜ R)"
                elif any(x in kttt for x in ["THANH LÝ", "KHÔNG SỬA"]) or any(x in sbn for x in ["THANH LÝ", "KHÔNG SỬA"]):
                    stt = "🔴 THANH LÝ"
                else:
                    stt = "🟡 ĐANG XỬ LÝ"

                data_clean.append({
                    "CHI NHÁNH": region, 
                    "MÃ MÁY": ma, 
                    "TRẠNG THÁI": stt,
                    "KIỂM TRA": row[6],
                    "SỬA NGOÀI": sbn,
                    "GIAO LẠI": gl,
                    "LOẠI MÁY": row[3]
                })
            final_df = pd.concat([final_df, pd.DataFrame(data_clean)], ignore_index=True)
        except: continue
    return final_df

# --- GIAO DIỆN ---
st.title("🏭 HỆ THỐNG QUẢN TRỊ KHO: QUY TRÌNH OK - R")
df = load_and_process_v17()

if not df.empty:
    # 1. Bảng số liệu tổng hợp
    summary = df.groupby('CHI NHÁNH').agg(
        Tong_Nhan=('MÃ MÁY', 'count'),
        Da_Tra_R=('TRẠNG THÁI', lambda x: (x == '🟢 ĐÃ TRẢ ĐI (R)').sum()),
        Con_Trong_Kho=('TRẠNG THÁI', lambda x: (x == '🔵 CÒN TRONG KHO (CHỜ R)').sum()),
        Thanh_Ly=('TRẠNG THÁI', lambda x: (x == '🔴 THANH LÝ').sum()),
        Dang_Sua=('TRẠNG THÁI', lambda x: (x == '🟡 ĐANG XỬ LÝ').sum())
    ).reset_index()

    st.subheader("📝 Báo cáo tổng hợp theo Miền")
    st.table(summary)

    # 2. Metrics tổng hợp nhanh
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng Máy Nhận", summary['Tong_Nhan'].sum())
    c2.metric("Đã Trả Đi (R)", summary['Da_Tra_R'].sum())
    c3.metric("Tồn Kho Chờ R", summary['Con_Trong_Kho'].sum(), delta_color="inverse")
    c4.metric("Đang Sửa/Kiểm", summary['Dang_Sua'].sum())

    # 3. Biểu đồ trực quan
    st.write("---")
    fig = px.bar(summary, x='CHI NHÁNH', y=['Da_Tra_R', 'Con_Trong_Kho', 'Dang_Sua', 'Thanh_Ly'],
                 title="Phân tích tình trạng tồn kho thực tế",
                 color_discrete_map={
                     "Da_Tra_R": "green",
                     "Con_Trong_Kho": "blue",
                     "Dang_Sua": "orange",
                     "Thanh_Ly": "red"
                 })
    st.plotly_chart(fig, use_container_width=True)

    # 4. Danh sách máy đang "Ngâm" trong kho (OK nhưng chưa R)
    st.subheader("🚩 Danh sách máy đã sửa xong nhưng chưa xuất kho (CHỜ R)")
    df_pending = df[df['TRẠNG THÁI'] == '🔵 CÒN TRONG KHO (CHỜ R)']
    if not df_pending.empty:
        st.dataframe(df_pending, use_container_width=True)
    else:
        st.success("Tuyệt vời! Không có máy nào đã OK mà chưa xuất kho.")
else:
    st.error("Lỗi dữ liệu. Sếp hãy kiểm tra trạng thái Publish của file.")
