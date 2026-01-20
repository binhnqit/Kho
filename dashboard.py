import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="Hệ Thống Quản Trị V16.1", layout="wide")

# ĐỊNH NGHĨA 3 LINK RIÊNG BIỆT (Quay lại cấu trúc gốc sếp yêu cầu)
URL_FINANCE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?output=csv"
URL_KHO_BAC = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv"
URL_KHO_NAM = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"

# Hàm nạp dữ liệu độc lập (Có cơ chế tự ngắt nếu lỗi để tránh treo toàn app)
@st.cache_data(ttl=300)
def fetch_data(url):
    try:
        df = pd.read_csv(url, on_bad_lines='skip', low_memory=False).fillna("0")
        # Làm sạch tên cột ngay tại nguồn
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except:
        return pd.DataFrame()

def main():
    # --- SIDEBAR & REFRESH ---
    with st.sidebar:
        st.title("EXECUTIVE HUB")
        if st.button('🔄 CẬP NHẬT TOÀN HỆ THỐNG', type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # --- NẠP DỮ LIỆU ĐA KÊNH ---
    df_f_raw = fetch_data(URL_FINANCE)
    df_kb_raw = fetch_data(URL_KHO_BAC)
    df_kn_raw = fetch_data(URL_KHO_NAM)

    # --- 2. XỬ LÝ TÀI CHÍNH (GIỮ NGUYÊN GIÁ TRỊ CỐT LÕI) ---
    df_f = pd.DataFrame()
    if not df_f_raw.empty:
        try:
            # Dùng tên cột thực tế trên Sheet của sếp (Hãy đảm bảo tên cột trên Sheet khớp với các chữ này)
            f_data = []
            for _, row in df_f_raw.iloc[1:].iterrows():
                ma = str(row.iloc[1]).strip()
                if not ma or "MÃ" in ma.upper(): continue
                ngay = pd.to_datetime(row.iloc[6], dayfirst=True, errors='coerce')
                if pd.notnull(ngay):
                    f_data.append({
                        "NGÀY": ngay, "NĂM": ngay.year, "THÁNG": ngay.month,
                        "MÃ_MÁY": ma, "LINH_KIỆN": str(row.iloc[3]),
                        "VÙNG": str(row.iloc[5]),
                        "CP_DU_KIEN": pd.to_numeric(str(row.iloc[7]).replace(',', ''), errors='coerce') or 0,
                        "CP_THUC_TE": pd.to_numeric(str(row.iloc[8]).replace(',', ''), errors='coerce') or 0
                    })
            df_f = pd.DataFrame(f_data)
        except: pass

    # --- 3. XỬ LÝ KHO VẬN (KẾT HỢP 2 KHO NHƯNG DỮ LIỆU ĐỘC LẬP) ---
    df_kho = pd.DataFrame()
    warehouse_list = []
    for region, df_raw in [("MIỀN BẮC", df_kb_raw), ("ĐÀ NẴNG", df_kn_raw)]:
        if not df_raw.empty:
            for _, row in df_raw.iloc[1:].iterrows():
                ma = str(row.iloc[1]).strip()
                if not ma or "MÃ" in ma.upper(): continue
                # Logic phân loại màu sắc sếp yêu cầu
                kttt = str(row.iloc[6]).upper()
                snb = str(row.iloc[7]).upper()
                sbn = str(row.iloc[9]).upper()
                gl = str(row.iloc[13]).upper().strip()
                
                if gl == "R": stt = "🟢 ĐÃ TRẢ (R)"
                elif any(x in (kttt + sbn) for x in ["THANH LÝ", "HỎNG"]): stt = "🔴 THANH LÝ"
                elif "OK" in (kttt + snb + sbn): stt = "🔵 KHO NHẬN (ĐỢI R)"
                else: stt = "🟡 ĐANG XỬ LÝ"
                
                warehouse_list.append({"VÙNG": region, "MÃ_MÁY": ma, "TRẠNG_THÁI": stt})
    df_kho = pd.DataFrame(warehouse_list)

    # --- 4. GIAO DIỆN ---
    st.title("🛡️ HỆ THỐNG QUẢN TRỊ CHIẾN LƯỢC V16.1")
    tabs = st.tabs(["📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🤖 AI", "📁 DỮ LIỆU", "📦 KHO LOGISTICS"])

    with tabs[0]: # XU HƯỚNG
        if not df_f.empty:
            c1, c2 = st.columns(2)
            c1.plotly_chart(px.bar(df_f.groupby('THÁNG').size().reset_index(name='CA'), x='THÁNG', y='CA', title="Số ca hỏng hóc"), use_container_width=True)
            c2.plotly_chart(px.pie(df_f, names='VÙNG', title="Cơ cấu vùng miền"), use_container_width=True)

    with tabs[1]: # TÀI CHÍNH
        if not df_f.empty:
            st.plotly_chart(px.bar(df_f.groupby('LINH_KIỆN')[['CP_DU_KIEN', 'CP_THUC_TE']].sum().reset_index(), x='LINH_KIỆN', y=['CP_DU_KIEN', 'CP_THUC_TE'], barmode='group'), use_container_width=True)

    with tabs[2]: # AI
        if not df_f.empty:
            st.info(f"Tổng hợp: {len(df_f)} ca. Tổng chi: {df_f['CP_THUC_TE'].sum():,.0f} VNĐ.")

    with tabs[4]: # KHO LOGISTICS (Tab sếp quan tâm nhất)
        if not df_kho.empty:
            st.subheader("📦 Điều hành Kho & Logistics")
            # Bảng đối soát 2 miền riêng biệt
            summary = df_kho.groupby(['VÙNG', 'TRẠNG_THÁI']).size().unstack(fill_value=0).reset_index()
            st.table(summary)
        else:
            st.warning("Đang tải dữ liệu từ các link Kho...")

if __name__ == "__main__":
    main()
