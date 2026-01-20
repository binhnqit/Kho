import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Kho Logistics V1.4", layout="wide")

@st.cache_data(ttl=2)
def load_and_process_v14():
    sources = {
        "MIEN BAC": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv",
        "DA NANG": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"
    }
    final_df = pd.DataFrame()
    for region, url in sources.items():
        try:
            # Đọc file và lấy đúng thứ tự cột từ A-N (0-13)
            df_raw = pd.read_csv(url, skiprows=1, header=None, dtype=str).fillna("")
            
            # Gán tên cột theo vị trí sếp cung cấp (0-index)
            # A:0, B:1(Mã), C:2, D:3, E:4, F:5, G:6(KTTT), H:7(SNB1), I:8(SNB2), J:9(SBN1), K:10, L:11(SBN2), M:12, N:13(GL)
            data_clean = []
            for i in range(1, len(df_raw)):
                row = df_raw.iloc[i]
                ma = str(row[1]).strip() # Cột B: Mã máy
                if not ma or ma.upper() in ["NAN", "0", "MÃ SỐ MÁY"]: continue
                
                # Forward Fill thủ công cho mã máy bị trộn dòng
                if ma == "": ma = data_clean[-1]["MA MAY"] if data_clean else ""

                kttt = str(row[6]).upper()  # Cột G: Kiểm tra thực tế
                snb = (str(row[7]) + str(row[8])).upper() # Cột H, I: Sửa nội bộ
                sbn = (str(row[9]) + str(row[11])).upper() # Cột J, L: Sửa bên ngoài
                gl = str(row[13]).upper().strip() # Cột N: Giao lại
                
                # --- LOGIC PHÂN LOẠI CHUẨN ---
                # 1. Logic Thanh lý
                keywords_tl = ["THANH LÝ", "KHÔNG SỬA", "HỎNG"]
                if any(x in kttt for x in keywords_tl) or any(x in sbn for x in keywords_tl):
                    stt = "🔴 THANH LÝ"
                # 2. Logic Đã trả về (R)
                elif (("OK" in kttt) or ("OK" in sbn)) and (gl == "R"):
                    stt = "🟢 ĐÃ TRẢ VỀ"
                # 3. Logic Kho Nhận (OK nhưng chưa R)
                elif ("OK" in sbn) and (gl != "R"):
                    stt = "🔵 KHO NHẬN (ĐỐI CHIẾU)"
                # 4. Đang xử lý
                else:
                    stt = "🟡 ĐANG XỬ LÝ"

                data_clean.append({
                    "CHI NHANH": region,
                    "MA MAY": ma,
                    "TRANG THAI": stt,
                    "KTTT": row[6],
                    "SBN": sbn,
                    "GIAO LAI": gl,
                    "LOAI": row[3] # Cột D: Loại máy
                })
            final_df = pd.concat([final_df, pd.DataFrame(data_clean)], ignore_index=True)
        except: continue
    return final_df

df = load_and_process_v14()
st.title("🏭 HỆ THỐNG QUẢN TRỊ KHO V1.4")

if not df.empty:
    # Tính toán con số thực tế
    t_nhan = len(df)
    t_tl = len(df[df['TRANG THAI'] == "🔴 THANH LÝ"])
    t_tra = len(df[df['TRANG THAI'] == "🟢 ĐÃ TRẢ VỀ"])
    t_kho = len(df[df['TRANG THAI'] == "🔵 KHO NHẬN (ĐỐI CHIẾU)"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng Máy Nhận", t_nhan)
    c2.metric("Thanh Lý", t_tl)
    c3.metric("Thực Nhận (Vận hành)", t_nhan - t_tl)
    c4.metric("Đã Trả Miền", t_tra)

    st.info(f"🚩 **Kho Nhận:** {t_kho} máy đã sửa xong nhưng chưa trả về miền (thiếu dấu 'R').")

    # Biểu đồ
    st.plotly_chart(px.pie(df, names='TRANG THAI', color='TRANG THAI', 
                           color_discrete_map={"🔴 THANH LÝ":"red","🟢 ĐÃ TRẢ VỀ":"green","🔵 KHO NHẬN (ĐỐI CHIẾU)":"blue","🟡 ĐANG XỬ LÝ":"orange"}), use_container_width=True)

    st.subheader("📋 Chi tiết danh sách (Cột B, G, J, L, N)")
    st.dataframe(df, use_container_width=True)
else:
    st.warning("Đang kết nối dữ liệu...")
