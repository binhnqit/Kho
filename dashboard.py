import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="Hệ Thống Quản Trị V15.3.2", layout="wide")

def refresh_all():
    st.cache_data.clear()
    st.toast("✅ Đã làm mới toàn bộ dữ liệu!", icon="🔄")

# --- 2. LOAD DỮ LIỆU TÀI CHÍNH (GIỮ NGUYÊN LOGIC V15.2) ---
@st.cache_data(ttl=600)
def load_finance_data():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?output=csv"
    try:
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

# --- 3. LOAD DỮ LIỆU KHO VẬN (XỬ LÝ LỖI PHÂN LOẠI) ---
@st.cache_data(ttl=600)
def load_warehouse_data():
    sources = {
        "MIỀN BẮC": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv",
        "ĐÀ NẴNG": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"
    }
    final_wh = []
    for region, url in sources.items():
        try:
            df_raw = pd.read_csv(url, skiprows=1, header=None, dtype=str).fillna("")
            for i in range(1, len(df_raw)):
                row = df_raw.iloc[i]
                ma = str(row[1]).strip()
                if not ma or ma.upper() in ["NAN", "0", "STT"]: continue
                kttt, snb, sbn, gl = str(row[6]).upper(), (str(row[7])+str(row[8])).upper(), (str(row[9])+str(row[11])).upper(), str(row[13]).upper().strip()
                
                if gl == "R": stt = "🟢 ĐÃ TRẢ (R)"
                elif any(x in (kttt + sbn) for x in ["THANH LÝ", "KHÔNG SỬA", "HỎNG"]): stt = "🔴 THANH LÝ"
                elif "OK" in (kttt + snb + sbn): stt = "🔵 KHO NHẬN (ĐỢI R)"
                elif sbn != "": stt = "🟠 ĐANG SỬA NGOÀI"
                else: stt = "🟡 ĐANG XỬ LÝ"
                
                final_wh.append({"VÙNG": region, "MÃ_MÁY": ma, "TRẠNG_THÁI": stt, "LOẠI": row[3], "KIỂM": row[6], "SBN": sbn, "GL": gl})
        except: continue
    return pd.DataFrame(final_wh)

# --- 4. KHỞI CHẠY ---
df_f = load_finance_data()
df_w = load_warehouse_data()

with st.sidebar:
    st.header("⚙️ QUẢN TRỊ")
    if st.button('🔄 CẬP NHẬT HỆ THỐNG', type="primary", use_container_width=True):
        refresh_all()
        st.rerun()
    if not df_f.empty:
        sel_y = st.selectbox("Năm", sorted(df_f['NĂM'].unique(), reverse=True))
        df_y = df_f[df_f['NĂM'] == sel_y]
        sel_m = st.multiselect("Tháng", sorted(df_y['THÁNG'].unique()), default=sorted(df_y['THÁNG'].unique()))
        df_final = df_y[df_y['THÁNG'].isin(sel_m)]

# --- 5. GIAO DIỆN CHÍNH ---
st.title("🛡️ HỆ THỐNG QUẢN TRỊ V15.3.2")

if df_f.empty or df_w.empty:
    st.warning("Đang kết nối dữ liệu...")
else:
    # Fix lỗi Syntax: Khai báo danh sách Tab rõ ràng
    list_tabs = ["📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🤖 AI", "📁 DATA", "🩺 SỨC KHỎE", "🔮 DỰ BÁO", "📦 KHO LOGISTICS"]
    t1, t2, t3, t4, t5, t6, t7 = st.tabs(list_tabs)

    with t1:
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.bar(df_y.groupby('THÁNG').size().reset_index(name='Ca'), x='THÁNG', y='Ca', title="Số ca hỏng"), use_container_width=True)
        c2.plotly_chart(px.pie(df_final, names='VÙNG', hole=0.5, title="Phân bổ vùng"), use_container_width=True)

    with t2:
        st.plotly_chart(px.bar(df_final.groupby('LIN_KIỆN')[['CP_DU_KIEN', 'CP_THUC_TE']].sum().reset_index(), x='LIN_KIỆN', y=['CP_DU_KIEN', 'CP_THUC_TE'], barmode='group'), use_container_width=True)

    with t3: st.info(f"Tổng ca: {len(df_final)} | Chênh lệch: {df_final['CHENH_LECH'].sum():,.0f} VNĐ")

    with t4: st.dataframe(df_final, use_container_width=True)

    with t5: st.dataframe(df_f.groupby('MÃ_MÁY').agg({'NGÀY': 'count', 'CP_THUC_TE': 'sum'}).sort_values('NGÀY', ascending=False), use_container_width=True)

    with t6:
        df_sort = df_f.sort_values(['MÃ_MÁY', 'NGÀY'])
        df_sort['KC'] = df_sort.groupby('MÃ_MÁY')['NGÀY'].diff().dt.days
        st.warning(f"Cảnh báo: {len(df_sort[df_sort['KC'] <= 60])} ca hỏng lại nhanh!")

    with t7:
        st.subheader("📦 Điều hành Kho & Logistics")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Tổng thiết bị", len(df_w))
        k2.metric("Chờ xuất (R)", len(df_w[df_w['TRẠNG_THÁI'] == "🔵 KHO NHẬN (ĐỢI R)"]))
        k3.metric("Đang sửa ngoài", len(df_w[df_w['TRẠNG_THÁI'] == "🟠 ĐANG SỬA NGOÀI"]))
        k4.metric("Thanh lý", len(df_w[df_w['TRẠNG_THÁI'] == "🔴 THANH LÝ"]))
        
        st.markdown("**Bảng trạng thái vùng:**")
        st.table(df_w.groupby(['VÙNG', 'TRẠNG_THÁI']).size().unstack(fill_value=0).reset_index())
        
        st.error("🔴 **Danh sách máy Thanh lý:**")
        st.dataframe(df_w[df_w['TRẠNG_THÁI'] == "🔴 THANH LÝ"][['VÙNG','MÃ_MÁY','LOẠI','KIỂM']], use_container_width=True, hide_index=True)
