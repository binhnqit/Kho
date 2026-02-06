import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from supabase import create_client

# --- 1. CONFIG & AUTH ---
st.set_page_config(page_title="LAPTOP MÁY PHA MÀU 4ORANGES", layout="wide", page_icon="🎨")

# Màu sắc và cấu hình Supabase
ORANGE_COLORS = ["#FF8C00", "#FFA500", "#FF4500", "#E67E22", "#D35400"]
SUPABASE_URL = "https://cigbnbaanpebwrufzxfg.supabase.co"
import streamlit as st
from supabase import create_client

# --- CẤU HÌNH ---
SUPABASE_URL = "https://cigbnbaanpebwrufzxfg.supabase.co"

# Lấy key từ secrets một cách an toàn
try:
    # Bạn có thể dán trực tiếp vào đây để test nhanh, 
    # nhưng tốt nhất vẫn là dùng st.secrets["SUPABASE_KEY"]
    SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_NQzqwJ4YhKC4sQGLxyLAyw_mwRFhkRf")
    
    # Khởi tạo client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Kiểm tra kết nối thực tế bằng cách đếm số dòng trong bảng machines
    supabase.table("machines").select("id", count="exact").limit(1).execute()
    st.sidebar.success("✅ Kết nối Database thành công!")
    
except Exception as e:
    st.error("❌ Lỗi xác thực Database (401)")
    st.info(f"Chi tiết: {e}")
    st.stop()

# URLs dữ liệu cũ (Legacy)
URL_LAPTOP_LOI = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=675485241&single=true&output=csv"
URL_MIEN_BAC = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv"
URL_DA_NANG = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"

# --- 2. ĐỊNH NGHĨA SCHEMA CSV (CONTRACT) ---
FILE_1_COLS = ["MÃ SỐ MÁY", "KHU VỰC", "LOẠI MÁY", "TÌNH TRẠNG", "NGÀY NHẬN", "KIỂM TRA THỰC TẾ", "SỬA NỘI BỘ", "SỬA BÊN NGOÀI", "NGÀY SỬA XONG", "SỬA ĐỀN BÙ", "GIAO LẠI Miền Bắc", "NGÀY TRẢ", "HƯ KHÔNG SỬA ĐƯỢC"]
FILE_2_COLS = ["Mã số máy", "Tên KH", "Lý Do", "Ghi Chú", "Chi Nhánh", "Ngày Xác nhận", "Người Kiểm Tra", "Chi Phí Dự Kiến", "Chi Phí Thực Tế"]

# --- 3. HELPER FUNCTIONS ---
@st.cache_data(ttl=300)
def get_raw_data(url):
    try: return pd.read_csv(url, on_bad_lines='skip', low_memory=False).fillna("")
    except: return pd.DataFrame()

def validate_csv(df, expected_columns):
    missing = set(expected_columns) - set(df.columns)
    if missing: return [f"❌ Thiếu cột: {', '.join(missing)}"]
    if df.empty: return ["❌ File rỗng"]
    return []

def log_audit(action, detail):
    try:
        supabase.table("audit_logs").insert({
            "action": action,
            "detail": detail,
            "created_at": datetime.datetime.now().isoformat()
        }).execute()
    except: pass

@st.cache_data(ttl=300)
def process_finance_data(df_loi_raw):
    f_list = []
    if not df_loi_raw.empty:
        for _, row in df_loi_raw.iloc[1:].iterrows():
            try:
                ma = str(row.iloc[1]).strip()
                if not ma or "MÃ" in ma.upper(): continue
                ngay = pd.to_datetime(row.iloc[6], dayfirst=True, errors='coerce')
                if pd.notnull(ngay):
                    cp = pd.to_numeric(str(row.iloc[8]).replace(',', ''), errors='coerce') or 0
                    f_list.append({
                        "NGÀY": ngay, "NĂM": ngay.year, "THÁNG": ngay.month,
                        "MÃ_MÁY": ma, "LINH_KIỆN": str(row.iloc[3]).strip(),
                        "VÙNG": str(row.iloc[5]).strip(), "CP": cp, "KHÁCH": str(row.iloc[2]).strip()
                    })
            except: continue
    return pd.DataFrame(f_list)

# --- 4. MAIN INTERFACE ---
def main():
    with st.sidebar:
        st.title("🎨 4ORANGES")
        st.subheader("LAPTOP MÁY PHA MÀU")
        if st.button('🔄 LÀM MỚI DỮ LIỆU', type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        df_loi_raw = get_raw_data(URL_LAPTOP_LOI)
        df_bac_raw = get_raw_data(URL_MIEN_BAC)
        df_trung_raw = get_raw_data(URL_DA_NANG)
        df_f = process_finance_data(df_loi_raw)

        if df_f.empty:
            st.warning("⚠️ Đang chờ dữ liệu...")
            return

        now = datetime.datetime.now()
        years = sorted(df_f['NĂM'].unique(), reverse=True)
        sel_year = st.selectbox("Chọn Năm", years, index=years.index(now.year) if now.year in years else 0)
        
        available_months = sorted(df_f[df_f['NĂM'] == sel_year]['THÁNG'].unique().tolist())
        month_options = ["Tất cả"] + available_months
        sel_month = st.selectbox("Chọn Tháng", month_options, index=month_options.index(now.month) if now.month in month_options else 0)

    # FILTERING
    df_display = df_f[df_f['NĂM'] == sel_year]
    if sel_month != "Tất cả":
        df_display = df_display[df_display['THÁNG'] == sel_month]

    st.title("HỆ THỐNG QUẢN LÝ LAPTOP MÁY PHA MÀU 4ORANGES")
    st.divider()

    # KPI CARDS
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TỔNG CHI PHÍ", f"{df_display['CP'].sum():,.0f} đ")
    m2.metric("SỐ CA XỬ LÝ", f"{len(df_display)} ca")
    m3.metric("TRUNG BÌNH/CA", f"{(df_display['CP'].mean() if len(df_display)>0 else 0):,.0f} đ")
    vung_cao = df_display.groupby('VÙNG')['CP'].sum().idxmax() if not df_display.empty else "N/A"
    m4.metric("VÙNG CHI PHÍ CAO", vung_cao)

    # --- TABS DEFINITION (Thêm Tab 6) ---
    tabs = st.tabs(["📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🩺 SỨC KHỎE", "📦 LOGISTICS", "🧠 AI", "📥 DATA INGESTION"])

    with tabs[0]: # XU HƯỚNG
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.pie(df_display, names='VÙNG', title="CƠ CẤU MIỀN", hole=0.4, color_discrete_sequence=ORANGE_COLORS), use_container_width=True)
        with c2:
            df_t = df_display.groupby('THÁNG').size().reset_index(name='Số ca')
            st.plotly_chart(px.line(df_t, x='THÁNG', y='Số ca', title="XU HƯỚNG THÁNG", markers=True, color_discrete_sequence=["#FF8C00"]), use_container_width=True)

    with tabs[1]: # TÀI CHÍNH
        if not df_display.empty:
            st.plotly_chart(px.treemap(df_display, path=['VÙNG', 'LINH_KIỆN'], values='CP', title="CHI TIẾT CHI PHÍ", color_discrete_sequence=ORANGE_COLORS), use_container_width=True)

    with tabs[2]: # SỨC KHỎE
        health = df_f.groupby('MÃ_MÁY').agg({'NGÀY': 'count', 'CP': 'sum', 'KHÁCH': 'first', 'LINH_KIỆN': lambda x: ', '.join(set(x))}).reset_index()
        health.columns = ['Mã Máy', 'Lần hỏng', 'Tổng phí', 'Khách hàng', 'Linh kiện']
        danger_zone = health[health['Lần hỏng'] > 2].sort_values('Lần hỏng', ascending=False)
        st.dataframe(danger_zone.style.format({"Tổng phí": "{:,.0f} đ"}), use_container_width=True)

    with tabs[3]: # LOGISTICS (Dữ liệu từ MB/MT)
        wh_data = []
        for reg, raw in [("MIỀN BẮC", df_bac_raw), ("MIỀN TRUNG", df_trung_raw)]:
            if not raw.empty:
                for _, r in raw.iloc[1:].iterrows():
                    m_id = str(r.iloc[1]).strip()
                    if not m_id or "MÃ" in m_id.upper(): continue
                    st_nb = (str(r.iloc[6]) + str(r.iloc[8])).upper()
                    st_giao = str(r.iloc[13]).upper()
                    tt = "🟢 ĐÃ TRẢ" if "R" in st_giao else ("🔵 KHO NHẬN" if "OK" in st_nb else "⚪ CHỜ")
                    wh_data.append({"VÙNG": reg, "MÃ_MÁY": m_id, "TRẠNG_THÁI": tt})
        df_wh = pd.DataFrame(wh_data)
        if not df_wh.empty:
            st.plotly_chart(px.histogram(df_wh, x="VÙNG", color="TRẠNG_THÁI", barmode="group", title="KHO LOGISTICS", color_discrete_map={"🟢 ĐÃ TRẢ": "#FF8C00", "🔵 KHO NHẬN": "#F39C12", "⚪ CHỜ": "#BDC3C7"}), use_container_width=True)

    with tabs[4]: # AI
        st.subheader("🤖 AI STRATEGIC ADVISOR")
        st.info("AI đang phân tích dựa trên dữ liệu lịch sử và hiệu suất kho...")

    # --- TAB 6: DATA INGESTION (HOÀN THIỆN) ---
    with tabs[5]:
        st.subheader("📥 CỔNG NHẬP DỮ LIỆU TẬP TRUNG (SUPABASE)")
        
        file_type = st.selectbox("Loại dữ liệu import", ["FILE 1 – THEO DÕI SỬA CHỮA", "FILE 2 – CHI PHÍ"])
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

        if uploaded_file:
            df_up = pd.read_csv(uploaded_file).fillna("")
            errors = validate_csv(df_up, FILE_1_COLS if "FILE 1" in file_type else FILE_2_COLS)

            if errors:
                for e in errors: st.error(e)
            else:
                st.success("✅ Cấu trúc file hợp lệ")
                st.dataframe(df_up.head(3), use_container_width=True)

                if st.button("🚀 XÁC NHẬN GHI DATABASE", type="primary"):
                    progress = st.progress(0)
                    success_count = 0
                    
                    try:
                        if "FILE 1" in file_type:
                            for i, r in df_up.iterrows():
                                # Logic Upsert dựa trên Schema ảnh bạn gửi
                                supabase.table("machines").upsert({
                                    "machine_code": str(r["MÃ SỐ MÁY"]).strip(),
                                    "machine_type": str(r["LOẠI MÁY"]),
                                    "region": str(r["KHU VỰC"])
                                }, on_conflict="machine_code").execute()
                                success_count += 1
                                progress.progress((i + 1) / len(df_up))
                        
                        log_audit("IMPORT_SUCCESS", {"file": uploaded_file.name, "rows": success_count})
                        st.balloons()
                        st.success(f"Đã cập nhật {success_count} máy vào hệ thống!")
                    except Exception as e:
                        st.error(f"Lỗi Database: {e}")

if __name__ == "__main__":
    main()
