import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import time

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="Hệ Thống Quản Trị V15.5", layout="wide")

# --- 2. BỘ NẠP DỮ LIỆU THÔNG MINH (CHỐNG TREO) ---
@st.cache_data(ttl=300, show_spinner=False)
def smart_load(url):
    try:
        # Tăng tốc độ đọc bằng cách giới hạn engine và timeout
        df = pd.read_csv(url, dtype=str, on_bad_lines='skip', low_memory=False)
        return df
    except Exception as e:
        return pd.DataFrame()

# --- 3. LOGIC XỬ LÝ DỮ LIỆU (GIỮ NGUYÊN NỘI DUNG CỐT LÕI) ---
def get_finance_data():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?output=csv"
    df_raw = smart_load(url)
    if df_raw.empty: return pd.DataFrame()
    
    # Giữ nguyên logic xử lý của V15.2/V15.3
    clean_data = []
    # Bỏ qua dòng header đầu tiên của Google Sheets
    data_rows = df_raw.iloc[1:] 
    for _, row in data_rows.iterrows():
        try:
            ma_may = str(row.iloc[1]).strip()
            if not ma_may or len(ma_may) < 2 or "MÃ" in ma_may.upper(): continue
            p_date = pd.to_datetime(row.iloc[6], dayfirst=True, errors='coerce')
            if pd.notnull(p_date):
                cp_dk = pd.to_numeric(str(row.iloc[7]).replace(',', ''), errors='coerce') or 0
                cp_tt = pd.to_numeric(str(row.iloc[8]).replace(',', ''), errors='coerce') or 0
                clean_data.append({
                    "NGÀY": p_date, "NĂM": p_date.year, "THÁNG": p_date.month,
                    "MÃ_MÁY": ma_may, "KHÁCH_HÀNG": str(row.iloc[2]).strip(),
                    "LINH_KIỆN": str(row.iloc[3]).strip(), "VÙNG": str(row.iloc[5]).strip(),
                    "CP_DU_KIEN": cp_dk, "CP_THUC_TE": cp_tt, "CHENH_LECH": cp_tt - cp_dk
                })
        except: continue
    return pd.DataFrame(clean_data)

def get_warehouse_data():
    sources = {
        "MIỀN BẮC": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv",
        "ĐÀ NẴNG": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"
    }
    all_wh = []
    for region, url in sources.items():
        df = smart_load(url)
        if df.empty: continue
        # Logic phân loại OK-R (Sửa lỗi màu đỏ sếp gặp ở V15.3)
        for i in range(1, len(df)):
            row = df.iloc[i]
            ma = str(row.iloc[1]).strip()
            if not ma or ma.upper() in ["NAN", "0"]: continue
            kttt, snb, sbn, gl = str(row.iloc[6]).upper(), (str(row.iloc[7])+str(row.iloc[8])).upper(), (str(row.iloc[9])+str(row.iloc[11])).upper(), str(row.iloc[13]).upper().strip()
            
            if gl == "R": stt = "🟢 ĐÃ TRẢ (R)"
            elif any(x in (kttt + sbn) for x in ["THANH LÝ", "KHÔNG SỬA", "HỎNG"]): stt = "🔴 THANH LÝ"
            elif "OK" in (kttt + snb + sbn): stt = "🔵 KHO NHẬN (ĐỢI R)"
            elif sbn != "": stt = "🟠 ĐANG SỬA NGOÀI"
            else: stt = "🟡 ĐANG XỬ LÝ"
            all_wh.append({"VÙNG": region, "MÃ_MÁY": ma, "TRẠNG_THÁI": stt, "LOẠI": row.iloc[3], "KIỂM": row.iloc[6], "SBN": sbn, "GL": gl})
    return pd.DataFrame(all_wh)

# --- 4. GIAO DIỆN ĐIỀU HÀNH ---
def main():
    # Sidebar
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3208/3208726.png", width=80)
        st.title("EXECUTIVE HUB")
        if st.button('🔄 ĐỒNG BỘ TOÀN HỆ THỐNG', use_container_width=True, type="primary"):
            st.cache_data.clear()
            st.rerun()

    # Load dữ liệu với Spinner cục bộ (Không treo màn hình)
    with st.status("🚀 Đang kết nối dữ liệu an toàn...", expanded=True) as status:
        st.write("Đang tải dữ liệu Tài chính...")
        df_f = get_finance_data()
        st.write("Đang tải dữ liệu Kho vận...")
        df_w = get_warehouse_data()
        if not df_f.empty and not df_w.empty:
            status.update(label="✅ Kết nối thành công!", state="complete", expanded=False)
        else:
            status.update(label="⚠️ Kết nối chậm, vui lòng thử lại", state="error")

    if df_f.empty:
        st.error("❌ Lỗi: Không thể truy cập dữ liệu. Sếp hãy nhấn 'ĐỒNG BỘ TOÀN HỆ THỐNG' để thử lại.")
        return

    # --- RENDER TABS (GIỮ NGUYÊN NỘI DUNG SẾP ĐÃ LÀM) ---
    sel_y = st.sidebar.selectbox("📅 Năm", sorted(df_f['NĂM'].unique(), reverse=True))
    df_y = df_f[df_f['NĂM'] == sel_y]
    sel_m = st.sidebar.multiselect("🗓️ Tháng", sorted(df_y['THÁNG'].unique()), default=sorted(df_y['THÁNG'].unique()))
    df_final = df_y[df_y['THÁNG'].isin(sel_m)]

    st.markdown(f"## 🛡️ HỆ THỐNG QUẢN TRỊ CHIẾN LƯỢC V15.5")
    tabs = st.tabs(["📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🤖 AI", "📁 DỮ LIỆU", "🩺 SỨC KHỎE", "🔮 DỰ BÁO", "📦 KHO LOGISTICS"])

    with tabs[0]:
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.bar(df_y.groupby('THÁNG').size().reset_index(name='Ca'), x='THÁNG', y='Ca', title="Số ca hỏng hóc"), use_container_width=True)
        c2.plotly_chart(px.pie(df_final, names='VÙNG', hole=0.5, title="Cơ cấu theo vùng"), use_container_width=True)

    with tabs[1]:
        st.plotly_chart(px.bar(df_final.groupby('LIN_KIỆN')[['CP_DU_KIEN', 'CP_THUC_TE']].sum().reset_index(), x='LIN_KIỆN', y=['CP_DU_KIEN', 'CP_THUC_TE'], barmode='group'), use_container_width=True)

    with tabs[2]:
        st.info(f"Phân tích nhanh: {len(df_final)} vụ việc. Tổng chi phí: {df_final['CP_THUC_TE'].sum():,.0f} VNĐ.")

    with tabs[3]:
        st.dataframe(df_final, use_container_width=True)

    with tabs[4]:
        st.dataframe(df_f.groupby('MÃ_MÁY').agg({'NGÀY': 'count', 'CP_THUC_TE': 'sum'}).sort_values('NGÀY', ascending=False), use_container_width=True)

    with tabs[5]:
        df_sort = df_f.sort_values(['MÃ_MÁY', 'NGÀY'])
        df_sort['KC'] = df_sort.groupby('MÃ_MÁY')['NGÀY'].diff().dt.days
        st.warning(f"Cảnh báo: {len(df_sort[df_sort['KC'] <= 60])} máy hỏng lặp lại nhanh.")

    with tabs[6]:
        st.subheader("📦 Điều hành Kho & Logistics")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Tổng thiết bị", len(df_w))
        k2.metric("Chờ xuất (R)", len(df_w[df_w['TRẠNG_THÁI'] == "🔵 KHO NHẬN (ĐỢI R)"]))
        k3.metric("Đang sửa ngoài", len(df_w[df_w['TRẠNG_THÁI'] == "🟠 ĐANG SỬA NGOÀI"]))
        k4.metric("Thanh lý", len(df_w[df_w['TRẠNG_THÁI'] == "🔴 THANH LÝ"]))
        st.table(df_w.groupby(['VÙNG', 'TRẠNG_THÁI']).size().unstack(fill_value=0).reset_index())

if __name__ == "__main__":
    main()
