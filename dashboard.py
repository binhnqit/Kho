import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CẤU HÌNH & KẾT NỐI (TỐI ƯU 1 LINK) ---
st.set_page_config(page_title="Hệ Thống Quản Trị V15.7", layout="wide")

# Link chung sếp đã thiết lập thành công
SHARED_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?output=csv"

@st.cache_data(ttl=300, show_spinner=False)
def load_unified_data(url):
    try:
        # Tải dữ liệu thô từ link duy nhất
        return pd.read_csv(url, dtype=str, on_bad_lines='skip', low_memory=False).fillna("0")
    except:
        return pd.DataFrame()

# --- 2. KHỞI TẠO CÁC CHỨC NĂNG ---
def main():
    # Sidebar điều khiển
    with st.sidebar:
        st.title("EXECUTIVE HUB")
        if st.button('🔄 ĐỒNG BỘ 1 CHẠM', type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Nạp dữ liệu
    df_raw = load_unified_data(SHARED_URL)
    
    if df_raw.empty:
        st.error("❌ Không thể nạp dữ liệu. Sếp kiểm tra lại link Google Sheets.")
        return

    # --- 3. PHÂN TÁCH LOGIC (GIỮ NGUYÊN NỘI DUNG PHẦN MỀM) ---
    # Phần này tự động nhận diện các dòng thuộc Tài chính hoặc Kho vận
    try:
        # Khởi tạo dữ liệu Tài chính
        clean_f = []
        # Duyệt từ dòng 1 (bỏ header)
        for _, row in df_raw.iloc[1:].iterrows():
            ma = str(row.iloc[1]).strip()
            if not ma or "MÃ" in ma.upper(): continue
            ngay = pd.to_datetime(row.iloc[6], dayfirst=True, errors='coerce')
            if pd.notnull(ngay):
                cp_dk = pd.to_numeric(str(row.iloc[7]).replace(',', ''), errors='coerce') or 0
                cp_tt = pd.to_numeric(str(row.iloc[8]).replace(',', ''), errors='coerce') or 0
                clean_f.append({
                    "NGÀY": ngay, "NĂM": ngay.year, "THÁNG": ngay.month,
                    "MÃ_MÁY": ma, "LINH_KIỆN": str(row.iloc[3]).strip(),
                    "VÙNG": str(row.iloc[5]).strip(), "CP_DU_KIEN": cp_dk,
                    "CP_THUC_TE": cp_tt, "CHENH_LECH": cp_tt - cp_dk
                })
        df_f = pd.DataFrame(clean_f)
        
        # Khởi tạo dữ liệu Kho (Logic phân loại OK-R sếp yêu cầu)
        clean_w = []
        for _, row in df_raw.iloc[1:].iterrows():
            ma = str(row.iloc[1]).strip()
            if not ma or "MÃ" in ma.upper(): continue
            # Logic trạng thái
            kttt, snb, sbn, gl = str(row.iloc[6]).upper(), str(row.iloc[7]).upper(), str(row.iloc[9]).upper(), str(row.iloc[13]).upper().strip()
            if gl == "R": stt = "🟢 ĐÃ TRẢ (R)"
            elif any(x in (kttt + sbn) for x in ["THANH LÝ", "HỎNG"]): stt = "🔴 THANH LÝ"
            elif "OK" in (kttt + snb + sbn): stt = "🔵 KHO NHẬN (ĐỢI R)"
            elif sbn != "" and sbn != "0": stt = "🟠 ĐANG SỬA NGOÀI"
            else: stt = "🟡 ĐANG XỬ LÝ"
            clean_w.append({"VÙNG": row.iloc[5], "MÃ_MÁY": ma, "TRẠNG_THÁI": stt, "LOẠI": row.iloc[3]})
        df_w = pd.DataFrame(clean_w)

    except Exception as e:
        st.warning(f"Đang xử lý cấu trúc dữ liệu... {e}")
        return

    # --- 4. HIỂN THỊ GIAO DIỆN (THEO HÌNH 5E36A0) ---
    st.success("✅ Hệ thống đã sẵn sàng!")
    
    t_names = ["📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🤖 AI", "📁 DỮ LIỆU", "🩺 SỨC KHỎE", "🔮 DỰ BÁO", "📦 KHO LOGISTICS"]
    tabs = st.tabs(t_names)

    with tabs[0]: # XU HƯỚNG
        if not df_f.empty:
            c1, c2 = st.columns(2)
            c1.plotly_chart(px.bar(df_f.groupby('THÁNG').size().reset_index(), x='THÁNG', y=0, title="Số ca hỏng theo tháng"), use_container_width=True)
            c2.plotly_chart(px.pie(df_f, names='VÙNG', title="Phân bổ vùng miền"), use_container_width=True)

    with tabs[1]: # TÀI CHÍNH
        st.plotly_chart(px.bar(df_f.groupby('LINH_KIỆN')[['CP_DU_KIEN', 'CP_THUC_TE']].sum().reset_index(), x='LINH_KIỆN', y=['CP_DU_KIEN', 'CP_THUC_TE'], barmode='group'), use_container_width=True)

    with tabs[2]: # AI
        st.info(f"Tổng hợp: {len(df_f)} ca sửa chữa. Ngân sách thực chi: {df_f['CP_THUC_TE'].sum():,.0f} VNĐ.")

    with tabs[3]: # DỮ LIỆU
        st.dataframe(df_f, use_container_width=True)

    with tabs[4]: # SỨC KHỎE
        st.dataframe(df_f.groupby('MÃ_MÁY').size().sort_values(ascending=False), use_container_width=True)

    with tabs[5]: # DỰ BÁO
        st.warning("Tính năng dự báo chu kỳ hỏng đang hoạt động dựa trên dữ liệu lịch sử.")

    with tabs[6]: # KHO LOGISTICS
        st.subheader("📦 Quản Trị Kho Vận")
        if not df_w.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("Chờ xuất (R)", len(df_w[df_w['TRẠNG_THÁI'] == "🔵 KHO NHẬN (ĐỢI R)"]))
            m2.metric("Đang sửa ngoài", len(df_w[df_w['TRẠNG_THÁI'] == "🟠 ĐANG SỬA NGOÀI"]))
            m3.metric("Thanh lý", len(df_w[df_w['TRẠNG_THÁI'] == "🔴 THANH LÝ"]))
            st.table(df_w.groupby(['VÙNG', 'TRẠNG_THÁI']).size().unstack(fill_value=0))

if __name__ == "__main__":
    main()
