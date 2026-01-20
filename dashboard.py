import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="Hệ Thống Quản Trị Kho V3.0", layout="wide")

# Hàm xóa cache để cập nhật dữ liệu tức thì
def refresh_data():
    st.cache_data.clear()
    st.toast("✅ Đã làm mới dữ liệu từ Google Sheets!", icon="🔄")

@st.cache_data(ttl=600)
def load_full_data():
    sources = {
        "MIỀN BẮC": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv",
        "ĐÀ NẴNG": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"
    }
    final_df = pd.DataFrame()
    now = datetime.now()
    
    for region, url in sources.items():
        try:
            # Đọc dữ liệu (bỏ qua dòng tiêu đề phụ)
            df_raw = pd.read_csv(url, skiprows=1, header=None, dtype=str).fillna("")
            data_clean = []
            for i in range(1, len(df_raw)):
                row = df_raw.iloc[i]
                ma = str(row[1]).strip()
                if not ma or ma.upper() in ["NAN", "0", "STT"]: continue
                
                # Phân tách cột theo quy chuẩn của sếp
                kttt = str(row[6]).upper()       # Cột G
                snb = (str(row[7]) + str(row[8])).upper()   # Cột H, I
                sbn = (str(row[9]) + str(row[11])).upper()  # Cột J, L
                gl = str(row[13]).upper().strip()           # Cột N
                
                # Tính ngày tồn kho (Aging)
                d_nhan = pd.to_datetime(row[5], dayfirst=True, errors='coerce')
                days_in_stock = (now - d_nhan).days if pd.notnull(d_nhan) else 0

                # Logic phân loại trạng thái (Sếp duyệt)
                if gl == "R":
                    stt = "🟢 ĐÃ TRẢ (R)"
                    color_code = "green"
                elif any(x in (kttt + sbn) for x in ["THANH LÝ", "KHÔNG SỬA", "HỎNG"]):
                    stt = "🔴 THANH LÝ"
                    color_code = "red"
                elif "OK" in (kttt + snb + sbn):
                    stt = "🔵 KHO NHẬN (ĐỢI R)"
                    color_code = "blue"
                elif sbn != "" and "OK" not in sbn:
                    stt = "🟠 ĐANG SỬA NGOÀI"
                    color_code = "orange"
                else:
                    stt = "🟡 ĐANG XỬ LÝ"
                    color_code = "yellow"

                data_clean.append({
                    "VÙNG": region,
                    "MÃ MÁY": ma,
                    "TRẠNG THÁI": stt,
                    "SỐ NGÀY TỒN": days_in_stock,
                    "LOẠI MÁY": row[3],
                    "NGÀY NHẬN": row[5],
                    "CHI TIẾT KIỂM": row[6],
                    "SỬA NGOÀI": sbn,
                    "GIAO LẠI": gl,
                    "COLOR": color_code
                })
            final_df = pd.concat([final_df, pd.DataFrame(data_clean)], ignore_index=True)
        except Exception as e:
            continue
    return final_df

# --- 2. GIAO DIỆN ĐIỀU KHIỂN CHÍNH ---
col_logo, col_btn = st.columns([4, 1])
with col_logo:
    st.title("💠 LOGISTICS MANAGER V3.0")
    st.caption("Hệ thống quản trị kho thiết bị Miền Bắc & Đà Nẵng | Real-time Update")
with col_btn:
    if st.button("🔄 LÀM MỚI DỊ LIỆU", use_container_width=True, type="primary"):
        refresh_data()
        st.rerun()

df = load_full_data()

if not df.empty:
    # --- 3. KHU VỰC THỐNG KÊ TỔNG QUÁT ---
    total_in = len(df)
    total_out = len(df[df['TRẠNG THÁI'] == "🟢 ĐÃ TRẢ (R)"])
    total_tl = len(df[df['TRẠNG THÁI'] == "🔴 THANH LÝ"])
    total_stock = total_in - total_out

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TỔNG MÁY NHẬN", total_in)
    m2.metric("ĐÃ XUẤT KHO (R)", total_out, help="Số máy đã có dấu R")
    m3.metric("HÀNG THANH LÝ", total_tl)
    m4.metric("TỒN KHO VẬT LÝ", total_stock, delta=f"Gồm cả máy đang sửa", delta_color="inverse")

    st.write("---")

    # --- 4. HỆ THỐNG TAB HỢP NHẤT ---
    tab_summary, tab_status, tab_tl, tab_search = st.tabs([
        "📊 ĐỐI SOÁT TỔNG HỢP", 
        "🛠️ TRẠNG THÁI VẬN HÀNH", 
        "🔴 QUẢN TRỊ THANH LÝ", 
        "🔍 TRUY VẾT MÃ MÁY"
    ])

    with tab_summary:
        st.subheader("📍 Thống kê số liệu theo vùng")
        summary_vung = df.groupby('VÙNG').agg(
            Tổng_Nhận=('MÃ MÁY', 'count'),
            Đã_Trả_R=('TRẠNG THÁI', lambda x: (x == '🟢 ĐÃ TRẢ (R)').sum()),
            Chờ_Xuất_Kho=('TRẠNG THÁI', lambda x: (x == '🔵 KHO NHẬN (ĐỢI R)').sum()),
            Đang_Sửa_Ngoài=('TRẠNG THÁI', lambda x: (x == '🟠 ĐANG SỬA NGOÀI').sum()),
            Thanh_Lý=('TRẠNG THÁI', lambda x: (x == '🔴 THANH LÝ').sum())
        ).reset_index()
        st.table(summary_vung)

        # Biểu đồ so sánh
        fig_compare = px.bar(summary_vung, x='VÙNG', y=['Đã_Trả_R', 'Chờ_Xuất_Kho', 'Đang_Sửa_Ngoài', 'Thanh_Lý'],
                             title="Cơ cấu hàng hóa theo khu vực", barmode='group')
        st.plotly_chart(fig_compare, use_container_width=True)

    with tab_status:
        c_ngoai, c_kho = st.columns(2)
        with c_ngoai:
            st.info("📋 **MÁY ĐANG Ở TIỆM SỬA NGOÀI**")
            df_ngoai = df[df['TRẠNG THÁI'] == "🟠 ĐANG SỬA NGOÀI"]
            st.dataframe(df_ngoai[['VÙNG', 'MÃ MÁY', 'SỬA NGOÀI', 'SỐ NGÀY TỒN']], use_container_width=True, hide_index=True)
        
        with c_kho:
            st.warning("📦 **MÁY ĐÃ XONG - CHỜ GIAO (CHỜ R)**")
            df_kho = df[df['TRẠNG THÁI'] == "🔵 KHO NHẬN (ĐỢI R)"]
            st.dataframe(df_kho[['VÙNG', 'MÃ MÁY', 'GIAO LẠI', 'SỐ NGÀY TỒN']], use_container_width=True, hide_index=True)

    with tab_tl:
        st.subheader("🔴 Danh sách thiết bị ngưng vận hành (Thanh lý)")
        df_tl_list = df[df['TRẠNG THÁI'] == "🔴 THANH LÝ"]
        if not df_tl_list.empty:
            v_filter = st.multiselect("Lọc vùng thanh lý:", df_tl_list['VÙNG'].unique(), default=df_tl_list['VÙNG'].unique())
            st.dataframe(df_tl_list[df_tl_list['VÙNG'].isin(v_filter)][['VÙNG', 'MÃ MÁY', 'LOẠI MÁY', 'CHI TIẾT KIỂM', 'SỬA NGOÀI', 'NGÀY NHẬN']], use_container_width=True, hide_index=True)
            
            # Xuất file báo cáo thanh lý (Gợi ý chuyên môn)
            csv = df_tl_list.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 Tải danh sách thanh lý (Excel/CSV)", data=csv, file_name='danh_sach_thanh_ly.csv', mime='text/csv')
        else:
            st.success("Không có máy hỏng/thanh lý trong kho.")

    with tab_search:
        st.subheader("🔍 Truy tìm lịch sử thiết bị")
        search_q = st.text_input("Nhập mã số máy hoặc loại máy:")
        if search_q:
            mask = df['MÃ MÁY'].str.contains(search_q, case=False) | df['LOẠI MÁY'].str.contains(search_q, case=False)
            search_res = df[mask]
            if not search_res.empty:
                st.write(f"Tìm thấy {len(search_res)} bản ghi phù hợp:")
                st.dataframe(search_res, use_container_width=True, hide_index=True)
            else:
                st.error("Không tìm thấy dữ liệu máy này.")

else:
    st.info("Dữ liệu đang được kết nối, vui lòng đợi trong giây lát...")

# --- 5. CHÂN TRANG ---
st.write("---")
st.caption(f"Cập nhật lần cuối: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}")
