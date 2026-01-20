import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="Hệ Thống Quản Trị V15.3.1", layout="wide")

# Hàm xóa cache đồng bộ
def refresh_all():
    st.cache_data.clear()
    st.toast("✅ Đã làm mới toàn bộ dữ liệu!", icon="🔄")

# --- 2. TÀI CHÍNH (V15.2 - GIỮ NGUYÊN GIÁ TRỊ CỐT LÕI) ---
@st.cache_data(ttl=600)
def load_finance_data():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?output=csv"
    try:
        # Load dữ liệu tài chính không can thiệp logic
        df_raw = pd.read_csv(url, dtype=str, header=None, skiprows=1).fillna("0")
        clean_data = []
        for i, row in df_raw.iterrows():
            ma_may = str(row.iloc[1]).strip()
            if not ma_may or len(ma_may) < 2 or "MÃ" in ma_may.upper(): continue
            ngay_raw = str(row.iloc[6]).strip()
            p_date = pd.to_datetime(ngay_raw, dayfirst=True, errors='coerce')
            if pd.notnull(p_date):
                cp_dk = pd.to_numeric(str(row.iloc[7]).replace(',', ''), errors='coerce') or 0
                cp_tt = pd.to_numeric(str(row.iloc[8]).replace(',', ''), errors='coerce') or 0
                clean_data.append({
                    "NGÀY": p_date, "NĂM": p_date.year, "THÁNG": p_date.month,
                    "MÃ_MÁY": ma_may, "KHÁCH_HÀNG": str(row.iloc[2]).strip(),
                    "LINH_KIỆN": str(row.iloc[3]).strip(), "VÙNG": str(row.iloc[5]).strip(),
                    "CP_DU_KIEN": cp_dk, "CP_THUC_TE": cp_tt, "CHENH_LECH": cp_tt - cp_dk
                })
        return pd.DataFrame(clean_data)
    except: return pd.DataFrame()

# --- 3. KHO VẬN (XỬ LÝ LỖI MÀU ĐỎ TẠI HÌNH 1) ---
@st.cache_data(ttl=600)
def load_warehouse_data():
    sources = {
        "MIỀN BẮC": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv",
        "ĐÀ NẴNG": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"
    }
    final_wh = []
    now = datetime.now()
    for region, url in sources.items():
        try:
            df_raw = pd.read_csv(url, skiprows=1, header=None, dtype=str).fillna("")
            for i in range(1, len(df_raw)):
                row = df_raw.iloc[i]
                ma = str(row[1]).strip()
                if not ma or ma.upper() in ["NAN", "0", "STT"]: continue
                
                # SỬA LOGIC: Kiểm tra kỹ các cột để tránh lỗi 100% Thanh lý
                kttt = str(row[6]).upper() 
                snb = (str(row[7]) + str(row[8])).upper() 
                sbn = (str(row[9]) + str(row[11])).upper() 
                gl = str(row[13]).upper().strip()
                
                if gl == "R": stt = "🟢 ĐÃ TRẢ (R)"
                elif any(x in (kttt + sbn) for x in ["THANH LÝ", "KHÔNG SỬA", "HỎNG"]): stt = "🔴 THANH LÝ"
                elif "OK" in (kttt + snb + sbn): stt = "🔵 KHO NHẬN (ĐỢI R)"
                elif sbn != "": stt = "🟠 ĐANG SỬA NGOÀI"
                else: stt = "🟡 ĐANG XỬ LÝ"

                final_wh.append({
                    "VÙNG": region, "MÃ_MÁY": ma, "TRẠNG_THÁI": stt, 
                    "LOẠI": row[3], "NGÀY_NHẬN": row[5], "GIAO_LAI": gl,
                    "KIỂM_TRA": row[6], "SUA_NGOAI": sbn
                })
        except: continue
    return pd.DataFrame(final_wh)

# --- 4. KHỞI CHẠY DỮ LIỆU ---
df_fin = load_finance_data()
df_wh = load_warehouse_data()

# SIDEBAR điều hướng
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3208/3208726.png", width=80)
    st.title("EXECUTIVE HUB")
    if st.button('🔄 ĐỒNG BỘ TOÀN HỆ THỐNG', type="primary", use_container_width=True):
        refresh_all()
        st.rerun()
    
    if not df_fin.empty:
        sel_y = st.selectbox("📅 Năm báo cáo", sorted(df_fin['NĂM'].unique(), reverse=True))
        df_y = df_fin[df_fin['NĂM'] == sel_y]
        sel_m = st.multiselect("🗓️ Lọc Tháng", sorted(df_y['THÁNG'].unique()), default=sorted(df_y['THÁNG'].unique()))
        df_final = df_y[df_y['THÁNG'].isin(sel_m)]

# --- 5. GIAO DIỆN CHÍNH ---
st.markdown(f"## 🛡️ HỆ THỐNG QUẢN TRỊ CHIẾN LƯỢC V15.3.1")

# Kiểm tra dữ liệu để tránh treo máy (Fix hình 2 & 3)
if df_fin.empty:
    st.error("❌ Không thể kết nối dữ liệu Tài chính. Vui lòng kiểm tra link Sheet tổng.")
elif df_wh.empty:
    st.warning("⚠️ Đang tải dữ liệu Kho vận hoặc link Kho có lỗi...")
else:
    tabs = st.tabs(["📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🤖 AI", "📁 DATA
