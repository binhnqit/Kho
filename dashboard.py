import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="Hệ Thống Quản Trị Kho V1.0", layout="wide")

# --- 2. HÀM ĐỌC DỮ LIỆU TỪ LINK CÔNG KHAI ---
@st.cache_data(ttl=2)
def load_warehouse_data_fixed():
    # Link công khai sếp đã xuất bản (Publish to web)
    url_mb = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv"
    url_dn = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"

    def fetch_data(url, branch_label):
        try:
            # Đọc file CSV từ link công khai
            df = pd.read_csv(url).fillna("")
            # Chuẩn hóa tên cột: Xóa khoảng trắng thừa và viết hoa
            df.columns = [str(c).strip().upper() for c in df.columns]
            df['BRANCH_TAG'] = branch_label
            return df
        except Exception as e:
            return pd.DataFrame()

    df_mb = fetch_data(url_mb, "MIỀN BẮC")
    df_dn = fetch_data(url_dn, "ĐÀ NẴNG")
    
    combined = pd.concat([df_mb, df_dn], ignore_index=True)
    
    if combined.empty:
        return pd.DataFrame()

    # --- 3. XỬ LÝ LOGIC THEO CẤU TRÚC FILE SẾP GỬI ---
    processed = []
    for _, row in combined.iterrows():
        # Lấy Mã Số Máy (Cột khóa chính)
        ma = str(row.get('MÃ SỐ MÁY', '')).strip()
        if not ma or ma.upper() == "MÃ SỐ MÁY" or len(ma) < 2:
            continue
        
        # Xử lý Ngày Nhận và Ngày Trả (Dùng cột NGÀY NHẬN và NGÀY TRẢ)
        d_nhan = pd.to_datetime(row.get('NGÀY NHẬN', ''), dayfirst=True, errors='coerce')
        d_tra = pd.to_datetime(row.get('NGÀY TRẢ', ''), dayfirst=True, errors='coerce')
        
        # Nhận diện cột trạng thái theo cấu trúc file mới
        sua_nb = str(row.get('SỬA NỘI BỘ', '')).upper()
        hu_hong = str(row.get('HƯ KHÔNG SỬA ĐƯỢC', '')).strip()
        
        # Xác định cột "GIAO LẠI" (Linh hoạt cho cả Miền Bắc và Đà Nẵng)
        giao_lai_mb = str(row.get('GIAO LẠI MIỀN BẮC', '')).upper()
        giao_lai_dn = str(row.get('GIAO LẠI ĐN', '')).upper()
        is_giao_lai = "OK" in giao_lai_mb or "XONG" in giao_lai_mb or "OK" in giao_lai_dn or "XONG" in giao_lai_dn

        # LOGIC PHÂN LOẠI TRẠNG THÁI (ƯU TIÊN THANH LÝ)
        if "THANH LÝ" in sua_nb or hu_hong != "":
            status = "🔴 THANH LÝ/HỦY"
        elif pd.notnull(d_tra) or is_giao_lai:
            status = "🟢 ĐÃ TRẢ VỀ"
        else:
            status = "🟡 ĐANG TRONG KHO"

        processed.append({
            "CHI NHÁNH": row['BRANCH_TAG'],
            "MÃ MÁY": ma,
            "KHU VỰC": row.get('KHU VỰC', ''),
            "LOẠI MÁY": row.get('LOẠI MÁY', ''),
            "TRẠNG THÁI": status,
            "NGÀY NHẬN": d_nhan,
            "NGÀY TRẢ": d_tra,
            "KIỂM TRA": row.get('KIỂM TRA THỰC TẾ', ''),
            "HÌNH THỨC": "SỬA NGOÀI" if str(row.get('SỬA BÊN NGOÀI', '')).strip() else "SỬA NỘI BỘ"
        })
    return pd.DataFrame(processed)

# --- 4. GIAO DIỆN HIỂN THỊ ---
df = load_warehouse_data_fixed()

st.title("🏭 HỆ THỐNG QUẢN TRỊ KHO V1.0")

if not df.empty:
    with st.sidebar:
        st.header("🔍 BỘ LỌC")
        br_sel = st.multiselect("Chi nhánh", df['CHI NHÁNH'].unique(), default=df['CHI NHÁNH'].unique())
        st_sel = st.multiselect("Trạng thái", df['TRẠNG THÁI'].unique(), default=df['TRẠNG THÁI'].unique())
        
        df_view = df[(df['CHI NHÁNH'].isin(br_sel)) & (df['TRẠNG THÁI'].isin(st_sel))]
        
        if st.button("🔄 LÀM MỚI DỮ LIỆU"):
            st.cache_data.clear()
            st.rerun()

    # KPI TOP
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng Nhận", len(df_view))
    c2.metric("Đang Xử Lý", len(df_view[df_view['TRẠNG THÁI'] == "🟡 ĐANG TRONG KHO"]))
    c3.metric("Đã Trả", len(df_view[df_view['TRẠNG THÁI'] == "🟢 ĐÃ TRẢ VỀ"]))
    c4.metric("Thanh Lý", len(df_view[df_view['TRẠNG THÁI'] == "🔴 THANH LÝ/HỦY"]))

    # BIỂU ĐỒ
    col_l, col_r = st.columns(2)
    with col_l:
        st.plotly_chart(px.pie(df_view, names='TRẠNG THÁI', title="Cơ cấu kho", hole=0.4), use_container_width=True)
    with col_r:
        st.plotly_chart(px.bar(df_view.groupby(['CHI NHÁNH', 'TRẠNG THÁI']).size().reset_index(name='SL'), 
                               x='CHI NHÁNH', y='SL', color='TRẠNG THÁI', barmode='group', title="So sánh 2 miền"), use_container_width=True)

    # CHI TIẾT
    st.subheader("📋 Danh sách chi tiết")
    st.dataframe(df_view.sort_values('NGÀY NHẬN', ascending=False), use_container_width=True)
else:
    st.info("⌛ Hệ thống đang tải dữ liệu từ Google Sheets. Sếp vui lòng đợi trong giây lát...")
