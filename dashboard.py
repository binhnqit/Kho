import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="Strategic Management System V16.2", layout="wide")

# Link 3 nguồn dữ liệu độc lập (Đảm bảo không nhảy dữ liệu)
URL_FINANCE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?output=csv"
URL_KHO_BAC = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv"
URL_KHO_NAM = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"

@st.cache_data(ttl=300)
def fetch_data(url):
    try:
        return pd.read_csv(url, on_bad_lines='skip', low_memory=False).fillna("0")
    except:
        return pd.DataFrame()

# --- 2. XỬ LÝ DỮ LIỆU ---
def main():
    # Load raw
    df_f_raw = fetch_data(URL_FINANCE)
    df_kb_raw = fetch_data(URL_KHO_BAC)
    df_kn_raw = fetch_data(URL_KHO_NAM)

    # Clean Finance
    clean_f = []
    if not df_f_raw.empty:
        for _, row in df_f_raw.iloc[1:].iterrows():
            ma = str(row.iloc[1]).strip()
            if not ma or "MÃ" in ma.upper(): continue
            ngay = pd.to_datetime(row.iloc[6], dayfirst=True, errors='coerce')
            if pd.notnull(ngay):
                cp_tt = pd.to_numeric(str(row.iloc[8]).replace(',', ''), errors='coerce') or 0
                clean_f.append({
                    "NGÀY": ngay, "THÁNG": ngay.month, "NĂM": ngay.year,
                    "MÃ_MÁY": ma, "LINH_KIỆN": str(row.iloc[3]).strip(),
                    "VÙNG": str(row.iloc[5]).strip(), "CP_THUC_TE": cp_tt
                })
    df_f = pd.DataFrame(clean_f)

    # Clean Warehouse
    warehouse_list = []
    for region, df_raw in [("MIỀN BẮC", df_kb_raw), ("ĐÀ NẴNG", df_kn_raw)]:
        if not df_raw.empty:
            for _, row in df_raw.iloc[1:].iterrows():
                ma = str(row.iloc[1]).strip()
                if not ma or "MÃ" in ma.upper(): continue
                kttt, snb, sbn, gl = str(row.iloc[6]).upper(), str(row.iloc[7]).upper(), str(row.iloc[9]).upper(), str(row.iloc[13]).upper().strip()
                if gl == "R": stt = "🟢 ĐÃ TRẢ (R)"
                elif any(x in (kttt + sbn) for x in ["THANH LÝ", "HỎNG"]): stt = "🔴 THANH LÝ"
                elif "OK" in (kttt + snb + sbn): stt = "🔵 KHO NHẬN (ĐỢI R)"
                else: stt = "🟡 ĐANG XỬ LÝ"
                warehouse_list.append({"VÙNG": region, "MÃ_MÁY": ma, "TRẠNG_THÁI": stt, "LOẠI": row.iloc[3]})
    df_w = pd.DataFrame(warehouse_list)

    # --- 3. GIAO DIỆN CHUYÊN NGHIỆP ---
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3208/3208726.png", width=100)
    st.sidebar.title("CONTROL CENTER")
    
    # Bộ lọc toàn cầu
    sel_vung = st.sidebar.multiselect("Vùng miền", options=df_f['VÙNG'].unique(), default=df_f['VÙNG'].unique())
    df_f_filtered = df_f[df_f['VÙNG'].isin(sel_vung)]

    st.markdown("## 🛡️ HỆ THỐNG QUẢN TRỊ CHIẾN LƯỢC V16.2")
    st.info("💡 Dữ liệu được đồng bộ thời gian thực từ Cloud System.")

    tabs = st.tabs(["📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🧠 AI ANALYTICS", "📁 DỮ LIỆU", "🩺 SỨC KHỎE MÁY", "📦 KHO LOGISTICS"])

    # --- TAB 1: XU HƯỚNG ---
    with tabs[0]:
        c1, c2 = st.columns([2, 1])
        with c1:
            line_data = df_f_filtered.groupby('THÁNG')['CP_THUC_TE'].sum().reset_index()
            fig = px.line(line_data, x='THÁNG', y='CP_THUC_TE', title="Biến động chi phí theo tháng", markers=True)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            pie_fig = px.pie(df_f_filtered, names='VÙNG', hole=0.4, title="Tỷ lệ sự cố theo vùng")
            st.plotly_chart(pie_fig, use_container_width=True)

    # --- TAB 2: TÀI CHÍNH ---
    with tabs[1]:
        st.subheader("💰 Phân tích dòng vốn sửa chữa")
        bar_data = df_f_filtered.groupby('LINH_KIỆN')['CP_THUC_TE'].sum().sort_values(ascending=False).reset_index()
        fig_bar = px.bar(bar_data, x='LINH_KIỆN', y='CP_THUC_TE', color='CP_THUC_TE', title="Chi phí theo loại linh kiện")
        st.plotly_chart(fig_bar, use_container_width=True)

    # --- TAB 3: AI ANALYTICS ---
    with tabs[2]:
        st.subheader("🧠 Nhận định từ Trí tuệ nhân tạo")
        col_a, col_b = st.columns(2)
        total_cost = df_f_filtered['CP_THUC_TE'].sum()
        avg_cost = df_f_filtered['CP_THUC_TE'].mean()
        
        with col_a:
            st.metric("Tổng ngân sách đã chi", f"{total_cost:,.0f} VNĐ")
            st.write(f"👉 AI nhận định: Chi phí trung bình mỗi ca là **{avg_cost:,.0f} VNĐ**. Vùng **{df_f_filtered['VÙNG'].value_counts().idxmax()}** đang có tần suất hỏng cao nhất.")
        with col_b:
            st.metric("Số vụ việc cần xử lý", f"{len(df_f_filtered)} ca")
            if total_cost > 100000000:
                st.warning("⚠️ Cảnh báo AI: Ngân sách đang vượt ngưỡng an toàn hàng tháng.")

    # --- TAB 4: DỮ LIỆU ---
    with tabs[3]:
        st.subheader("📁 Nhật ký hệ thống chi tiết")
        st.dataframe(df_f_filtered, use_container_width=True)

    # --- TAB 5: SỨC KHỎE MÁY ---
    with tabs[4]:
        st.subheader("🩺 Đánh giá độ bền thiết bị")
        health_df = df_f.groupby('MÃ_MÁY').agg({'NGÀY': 'count', 'CP_THUC_TE': 'sum'}).reset_index()
        health_df.columns = ['Mã Máy', 'Số lần hỏng', 'Tổng chi phí']
        
        def health_status(x):
            if x >= 5: return "🔴 RẤT KÉM (Thay mới)"
            if x >= 3: return "🟡 TRUNG BÌNH (Bảo trì gấp)"
            return "🟢 TỐT"
        
        health_df['Trạng thái'] = health_df['Số lần hỏng'].apply(health_status)
        st.dataframe(health_df.sort_values('Số lần hỏng', ascending=False), use_container_width=True)

    # --- TAB 6: KHO LOGISTICS ---
    with tabs[5]:
        st.subheader("📦 Điều hành Kho & Logistics")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Chờ trả (R)", len(df_w[df_w['TRẠNG_THÁI'] == "🟢 ĐÃ TRẢ (R)"]))
        k2.metric("Chờ nhập kho", len(df_w[df_w['TRẠNG_THÁI'] == "🔵 KHO NHẬN (ĐỢI R)"]))
        k3.metric("Đang sửa", len(df_w[df_w['TRẠNG_THÁI'] == "🟡 ĐANG XỬ LÝ"]))
        k4.metric("Thanh lý", len(df_w[df_w['TRẠNG_THÁI'] == "🔴 THANH LÝ"]))
        
        st.divider()
        st.markdown("### 📊 Bảng đối soát trạng thái theo vùng")
        summary_wh = df_w.groupby(['VÙNG', 'TRẠNG_THÁI']).size().unstack(fill_value=0)
        st.table(summary_wh)

if __name__ == "__main__":
    main()
