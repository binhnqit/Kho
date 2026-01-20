import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="Hệ Thống Quản Trị Kho V1.0", layout="wide")

# --- 2. HÀM ĐỌC DỮ LIỆU TỪ LINK CÔNG KHAI CỦA SẾP ---
@st.cache_data(ttl=2)
def load_warehouse_data_final():
    # Link sếp cung cấp
    url_mb = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv"
    url_dn = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"

    def fetch_data(url, branch_name):
        try:
            # Đọc dữ liệu, bỏ qua dòng trống và chuẩn hóa tiêu đề
            df = pd.read_csv(url).fillna("")
            df.columns = [c.strip().upper() for c in df.columns]
            df['CHI NHÁNH'] = branch_name
            return df
        except Exception as e:
            st.error(f"Lỗi khi đọc dữ liệu {branch_name}: {e}")
            return pd.DataFrame()

    df_mb = fetch_data(url_mb, "MIỀN BẮC")
    df_dn = fetch_data(url_dn, "ĐÀ NẴNG")
    
    combined = pd.concat([df_mb, df_dn], ignore_index=True)
    
    if combined.empty:
        return pd.DataFrame()

    # --- XỬ LÝ LOGIC PHÂN LOẠI TRẠNG THÁI ---
    processed = []
    for _, row in combined.iterrows():
        ma = str(row.get('MÃ SỐ MÁY', '')).strip()
        if not ma or "MÃ" in ma.upper() or len(ma) < 2: 
            continue
        
        # Xử lý ngày tháng
        d_nhan = pd.to_datetime(row.get('NGÀY NHẬN', ''), dayfirst=True, errors='coerce')
        d_tra = pd.to_datetime(row.get('NGÀY TRẢ', ''), dayfirst=True, errors='coerce')
        
        # Nhận diện các cột nội dung
        sua_nb = str(row.get('SỬA NỘI BỘ', '')).upper()
        hu_hong = str(row.get('HƯ KHÔNG SỬA ĐƯỢC', '')).strip()
        giao_lai = str(row.get('GIAO LẠI ĐN', '')).upper()

        # LOGIC TRẠNG THÁI CHUYÊN GIA
        if "THANH LÝ" in sua_nb or hu_hong != "" or "THANH LÝ" in hu_hong.upper():
            status = "🔴 THANH LÝ/HỦY"
        elif pd.notnull(d_tra) or "OK" in giao_lai or "XONG" in giao_lai:
            status = "🟢 ĐÃ TRẢ VỀ"
        else:
            status = "🟡 ĐANG TRONG KHO"

        processed.append({
            "CHI NHÁNH": row['CHI NHÁNH'],
            "MÃ MÁY": ma,
            "LOẠI MÁY": row.get('LOẠI MÁY', 'Laptop'),
            "TRẠNG THÁI": status,
            "NGÀY NHẬN": d_nhan,
            "NGÀY TRẢ": d_tra,
            "KIỂM TRA THỰC TẾ": row.get('KIỂM TRA THỰC TẾ', ''),
            "GHI CHÚ": row.get('SỬA NỘI BỘ', '')
        })
    return pd.DataFrame(processed)

# --- 3. GIAO DIỆN EXECUTIVE DASHBOARD ---
df = load_warehouse_data_final()

st.title("🏭 HỆ THỐNG QUẢN TRỊ KHO THIẾT BỊ V1.0")
st.markdown("---")

if not df.empty:
    with st.sidebar:
        st.header("⚙️ BỘ LỌC HỆ THỐNG")
        branch_filter = st.multiselect("Chọn Chi Nhánh", df['CHI NHÁNH'].unique(), default=df['CHI NHÁNH'].unique())
        status_filter = st.multiselect("Trạng Thái", df['TRẠNG THÁI'].unique(), default=df['TRẠNG THÁI'].unique())
        
        df_final = df[(df['CHI NHÁNH'].isin(branch_filter)) & (df['TRẠNG THÁI'].isin(status_filter))]
        
        if st.button("🔄 LÀM MỚI DỮ LIỆU"):
            st.cache_data.clear()
            st.rerun()
        
        st.write("---")
        st.info("Dữ liệu được cập nhật trực tiếp từ Google Sheets công khai.")

    # KHỐI KPI CHIẾN LƯỢC
    m1, m2, m3, m4 = st.columns(4)
    total_received = len(df_final)
    scrapped = len(df_final[df_final['TRẠNG THÁI'] == "🔴 THANH LÝ/HỦY"])
    pending = len(df_final[df_final['TRẠNG THÁI'] == "🟡 ĐANG TRONG KHO"])
    completed = len(df_final[df_final['TRẠNG THÁI'] == "🟢 ĐÃ TRẢ VỀ"])

    m1.metric("Tổng Máy Nhận", total_received)
    m2.metric("Đang Xử Lý", pending, delta=f"{pending} máy", delta_color="inverse")
    m3.metric("Đã Hoàn Tất", completed)
    m4.metric("Thanh Lý (Loại biên)", scrapped)

    # KHỐI BIỂU ĐỒ
    st.write("---")
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        fig_p = px.pie(df_final, names='TRẠNG THÁI', title="Cơ cấu tình trạng thiết bị",
                       color='TRẠNG THÁI', color_discrete_map={
                           "🔴 THANH LÝ/HỦY": "#ef553b",
                           "🟢 ĐÃ TRẢ VỀ": "#00cc96",
                           "🟡 ĐANG TRONG KHO": "#ab63fa"
                       }, hole=0.5)
        st.plotly_chart(fig_p, use_container_width=True)

    with col_chart2:
        branch_counts = df_final.groupby(['CHI NHÁNH', 'TRẠNG THÁI']).size().reset_index(name='Số lượng')
        fig_b = px.bar(branch_counts, x='CHI NHÁNH', y='Số lượng', color='TRẠNG THÁI',
                       title="So sánh tồn kho 2 chi nhánh", barmode='group')
        st.plotly_chart(fig_b, use_container_width=True)

    # BẢNG DỮ LIỆU CHI TIẾT
    st.subheader("📋 Chi tiết danh sách thiết bị")
    st.dataframe(df_final.sort_values('NGÀY NHẬN', ascending=False), use_container_width=True)

else:
    st.warning("⚠️ Đang kết nối dữ liệu từ Google Sheets. Nếu quá lâu, sếp hãy kiểm tra lại trạng thái 'Publish to web' của file.")
