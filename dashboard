import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CẤU HÌNH HỆ THỐNG MỚI ---
st.set_page_config(page_title="Hệ Thống Quản Lý Kho V1.0", layout="wide")

# --- 2. HÀM ĐỌC DỮ LIỆU TỪ 2 SHEET (ĐÀ NẴNG & MIỀN BẮC) ---
@st.cache_data(ttl=5)
def load_warehouse_data():
    sheet_id = "1GaWsUJutV4wixR3RUBZSTIMrgaD8fOIi"
    # GID 2 chi nhánh
    gid_dn = "602348620"
    gid_mb = "1626219342"
    
    def fetch_sheet(gid, branch_name):
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        try:
            df = pd.read_csv(url, skiprows=0).fillna("")
            df.columns = [c.strip().upper() for c in df.columns]
            df['CHI NHÁNH'] = branch_name
            return df
        except: return pd.DataFrame()

    df_dn = fetch_sheet(gid_dn, "ĐÀ NẴNG")
    df_mb = fetch_sheet(gid_mb, "MIỀN BẮC")
    
    combined = pd.concat([df_dn, df_mb], ignore_index=True)
    
    # --- XỬ LÝ LOGIC CHUYÊN GIA THEO YÊU CẦU CỦA SẾP ---
    processed = []
    for _, row in combined.iterrows():
        ma = str(row.get('MÃ SỐ MÁY', '')).strip()
        if not ma or len(ma) < 2: continue
        
        # Chuyển đổi ngày
        d_nhan = pd.to_datetime(row.get('NGÀY NHẬN', ''), dayfirst=True, errors='coerce')
        d_tra = pd.to_datetime(row.get('NGÀY TRẢ', ''), dayfirst=True, errors='coerce')
        
        # Lấy thông tin sửa chữa
        sua_nb = str(row.get('SỬA NỘI BỘ', '')).upper()
        sua_ngoai = str(row.get('SỬA BÊN NGOÀI', '')).strip()
        hu_hong = str(row.get('HƯ KHÔNG SỬA ĐƯỢC', '')).strip()
        giao_lai = str(row.get('GIAO LẠI ĐN', '')).upper()

        # PHÂN LOẠI TRẠNG THÁI
        # 1. Thanh lý: Sửa nội bộ ghi "Thanh lý" HOẶC cột Hư không sửa được có dữ liệu
        if "THANH LÝ" in sua_nb or hu_hong != "":
            status = "🔴 THANH LÝ/HỦY"
        # 2. Đã trả: Có ngày trả HOẶC Giao lại ĐN ghi "OK/Xong"
        elif pd.notnull(d_tra) or "OK" in giao_lai or "XONG" in giao_lai:
            status = "🟢 ĐÃ TRẢ VỀ"
        # 3. Còn lại là đang xử lý
        else:
            status = "🟡 ĐANG TRONG KHO"

        processed.append({
            "CHI NHÁNH": row['CHI NHÁNH'],
            "MÃ MÁY": ma,
            "LOẠI MÁY": row.get('LOẠI MÁY', ''),
            "TRẠNG THÁI": status,
            "NGÀY NHẬN": d_nhan,
            "NGÀY TRẢ": d_tra,
            "HÌNH THỨC": "SỬA NGOÀI" if sua_ngoai else "SỬA NỘI BỘ",
            "CHI TIẾT KIỂM TRA": row.get('KIỂM TRA THỰC TẾ', '')
        })
    return pd.DataFrame(processed)

# --- 3. GIAO DIỆN CHÍNH ---
df = load_warehouse_data()

st.title("🏭 HỆ THỐNG QUẢN TRỊ KHO THIẾT BỊ V1.0")
st.markdown("---")

if not df.empty:
    # BỘ LỌC SIDEBAR
    with st.sidebar:
        st.header("⚙️ CẤU HÌNH BỘ LỌC")
        branch_filter = st.multiselect("Chi nhánh", df['CHI NHÁNH'].unique(), default=df['CHI NHÁNH'].unique())
        status_filter = st.multiselect("Trạng thái", df['TRẠNG THÁI'].unique(), default=df['TRẠNG THÁI'].unique())
        
        df_final = df[(df['CHI NHÁNH'].isin(branch_filter)) & (df['TRẠNG THÁI'].isin(status_filter))]
        
        if st.button("🔄 CẬP NHẬT DỮ LIỆU"):
            st.cache_data.clear()
            st.rerun()

    # KPI DASHBOARD
    k1, k2, k3, k4 = st.columns(4)
    total_in = len(df_final)
    scrapped = len(df_final[df_final['TRẠNG THÁI'] == "🔴 THANH LÝ/HỦY"])
    
    # Số lượng nhận thực tế (Trừ máy thanh lý) như sếp yêu cầu
    k1.metric("Tổng Máy Nhận", total_in)
    k2.metric("Đã Thanh Lý (Loại bỏ)", scrapped)
    k3.metric("Đang Xử Lý (Tồn Kho)", len(df_final[df_final['TRẠNG THÁI'] == "🟡 ĐANG TRONG KHO"]))
    k4.metric("Sẵn Sàng/Đã Trả", len(df_final[df_final['TRẠNG THÁI'] == "🟢 ĐÃ TRẢ VỀ"]))

    # BIỂU ĐỒ PHÂN TÍCH
    st.write("---")
    col_left, col_right = st.columns(2)
    
    with col_left:
        # Biểu đồ trạng thái
        fig_pie = px.pie(df_final, names='TRẠNG THÁI', title="Tỷ lệ trạng thái thiết bị", 
                         color='TRẠNG THÁI', color_discrete_map={
                             "🔴 THANH LÝ/HỦY": "#FF4B4B",
                             "🟢 ĐÃ TRẢ VỀ": "#00CC96",
                             "🟡 ĐANG TRONG KHO": "#FFAA00"
                         }, hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_right:
        # So sánh 2 chi nhánh
        branch_stats = df_final.groupby(['CHI NHÁNH', 'TRẠNG THÁI']).size().reset_index(name='Số lượng')
        fig_bar = px.bar(branch_stats, x='CHI NHÁNH', y='Số lượng', color='TRẠNG THÁI', 
                         title="Tình trạng kho theo chi nhánh", barmode='group')
        st.plotly_chart(fig_bar, use_container_width=True)

    # DANH SÁCH CHI TIẾT
    st.write("---")
    st.subheader("📋 Bảng kê chi tiết thiết bị")
    st.dataframe(df_final.sort_values('NGÀY NHẬN', ascending=False), use_container_width=True)

else:
    st.error("❌ Không thể kết nối dữ liệu. Sếp hãy kiểm tra lại file Google Sheets.")
