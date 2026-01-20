import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="Hệ Thống Kho Real-time V2.5.1", layout="wide")

# Hàm xóa cache để ép cập nhật dữ liệu
def refresh_data():
    st.cache_data.clear()
    st.toast("✅ Đang tải dữ liệu mới nhất từ Google Sheets...", icon="🔄")

@st.cache_data(ttl=600)
def load_data_pro():
    sources = {
        "MIỀN BẮC": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv",
        "ĐÀ NẴNG": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"
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

# --- 2. GIAO DIỆN ĐIỀU KHIỂN ---
col_title, col_ref = st.columns([4, 1.2])
with col_title:
    st.title("🚀 QUẢN TRỊ KHO TỔNG HỢP V2.5.1")
with col_ref:
    # Sửa lỗi Syntax tại đây: Đã đóng đủ ngoặc và thêm logic click
    if st.button("🔄 LÀM MỚI DỮ LIỆU", use_container_width=True, type="primary"):
        refresh_data()
        st.rerun()

# --- 3. XỬ LÝ DỮ LIỆU ---
df = load_data_pro()

if not df.empty:
    # Biến thống kê chuẩn hóa tên để scannable
    t_nhan = len(df)
    t_tra = len(df[df['STT'] == "DA_TRA"])
    t_tl = len(df[df['STT'] == "THANH_LY"])
    t_ton = t_nhan - t_tra
    
    # 4. DASHBOARD METRICS
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("TỔNG NHẬN", t_nhan)
    c2.metric("ĐÃ TRẢ (R)", t_tra)
    c3.metric("THANH LÝ", t_tl)
    c4.metric("TỒN THỰC TẾ", t_ton)

    tab1, tab2, tab3 = st.tabs(["📊 ĐỐI SOÁT VÙNG", "🔴 DANH SÁCH THANH LÝ", "🔍 TRA CỨU NHANH"])

    with tab1:
        st.subheader("📍 Thống kê chi tiết từng Miền")
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
            st.info("**Máy đang sửa ngoài:**")
            st.dataframe(df[df['STT'] == "SUA_NGOAI"][['VUNG','MA','SBN']], use_container_width=True)
        with col_r:
            st.warning("**Máy chờ xuất kho (Chờ R):**")
            st.dataframe(df[df['STT'] == "KHO_NHAN"][['VUNG','MA','GL']], use_container_width=True)

    with tab2:
        st.subheader("🔴 Danh sách máy Thanh lý theo vùng")
        df_tl = df[df['STT'] == "THANH_LY"]
        if not df_tl.empty:
            vung_sel = st.multiselect("Chọn vùng:", df_tl['VUNG'].unique(), default=df_tl['VUNG'].unique())
            st.dataframe(df_tl[df_tl['VUNG'].isin(vung_sel)][['VUNG','MA','LOAI','KTTT','SBN','NGAY']], use_container_width=True)
        else:
            st.info("Chưa có máy thanh lý.")

    with tab3:
        st.subheader("🔍 Tìm kiếm máy theo Mã")
        search_ma = st.text_input("Nhập mã số máy:")
        if search_ma:
            res = df[df['MA'].str.contains(search_ma, case=False)]
            if not res.empty:
                st.write(res)
            else:
                st.error("Không tìm thấy kết quả.")

else:
    st.info("Đang chờ dữ liệu từ Google Sheets...")
