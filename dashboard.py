import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="Hệ Thống Quản Trị V15.3", layout="wide")

# Hàm làm mới dữ liệu
def refresh_all():
    st.cache_data.clear()
    st.toast("✅ Đã đồng bộ toàn bộ hệ thống Tài chính & Kho vận!", icon="🔄")

# --- 2. LOAD DỮ LIỆU TÀI CHÍNH (V15.2) ---
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

# --- 3. LOAD DỮ LIỆU KHO VẬN (OK-R PRO) ---
@st.cache_data(ttl=600)
def load_warehouse_data():
    sources = {
        "MIỀN BẮC": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv",
        "ĐÀ NẴNG": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"
    }
    final_warehouse = []
    now = datetime.now()
    for region, url in sources.items():
        try:
            df_raw = pd.read_csv(url, skiprows=1, header=None, dtype=str).fillna("")
            for i in range(1, len(df_raw)):
                row = df_raw.iloc[i]
                ma = str(row[1]).strip()
                if not ma or ma.upper() in ["NAN", "0", "STT"]: continue
                kttt, snb, sbn, gl = str(row[6]).upper(), (str(row[7])+str(row[8])).upper(), (str(row[9])+str(row[11])).upper(), str(row[13]).upper().strip()
                d_nhan = pd.to_datetime(row[5], dayfirst=True, errors='coerce')
                aging = (now - d_nhan).days if pd.notnull(d_nhan) else 0
                
                if gl == "R": stt = "🟢 ĐÃ TRẢ (R)"
                elif any(x in (kttt + sbn) for x in ["THANH LÝ", "KHÔNG SỬA", "HỎNG"]): stt = "🔴 THANH LÝ"
                elif "OK" in (kttt + snb + sbn): stt = "🔵 KHO NHẬN (ĐỢI R)"
                elif sbn != "" and "OK" not in sbn: stt = "🟠 ĐANG SỬA NGOÀI"
                else: stt = "🟡 ĐANG XỬ LÝ"
                
                final_warehouse.append({"VÙNG": region, "MÃ_MÁY": ma, "TRẠNG_THÁI": stt, "AGING": aging, "LOẠI": row[3], "GIAO_LAI": gl, "KTTT": row[6], "SBN": sbn})
        except: continue
    return pd.DataFrame(final_warehouse)

# --- 4. KHỞI CHẠY DỮ LIỆU ---
df_fin = load_finance_data()
df_wh = load_warehouse_data()

if not df_fin.empty:
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3208/3208726.png", width=80)
        st.title("EXECUTIVE HUB")
        if st.button('🔄 ĐỒNG BỘ TOÀN HỆ THỐNG', type="primary", use_container_width=True):
            refresh_all()
            st.rerun()
        
        sel_year = st.selectbox("📅 Năm báo cáo", sorted(df_fin['NĂM'].unique(), reverse=True))
        df_y = df_fin[df_fin['NĂM'] == sel_year]
        sel_month = st.multiselect("🗓️ Lọc Tháng", sorted(df_y['THÁNG'].unique()), default=sorted(df_y['THÁNG'].unique()))
        df_final = df_y[df_y['THÁNG'].isin(sel_month)]

    st.markdown(f"## 🛡️ HỆ THỐNG QUẢN TRỊ CHIẾN LƯỢC V15.3")
    
    # THÊM TAB THỨ 7: QUẢN TRỊ KHO LOGISTICS
    t1, t2, t3, t4, t5, t6, t7 = st.tabs([
        "📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🤖 TRỢ LÝ AI", 
        "📁 DỮ LIỆU", "🩺 SỨC KHỎE", "🔮 DỰ BÁO", "📦 KHO LOGISTICS"
    ])

    # --- GIỮ NGUYÊN CÁC TAB CŨ CỦA V15.2 ---
    with t1:
        c_tr, c_pi, c_to = st.columns([1.5, 1, 1])
        with c_tr:
            m_t = df_y.groupby('THÁNG').size().reset_index(name='Số ca')
            st.plotly_chart(px.bar(m_t, x='THÁNG', y='Số ca', text_auto=True, title="Số ca hỏng theo tháng"), use_container_width=True)
        with c_pi:
            st.plotly_chart(px.pie(df_final['VÙNG'].value_counts().reset_index(), values='count', names='VÙNG', hole=0.5, title="Tỷ lệ theo vùng"), use_container_width=True)
        with c_to:
            st.plotly_chart(px.bar(df_final['MÃ_MÁY'].value_counts().head(10).reset_index(), x='count', y='MÃ_MÁY', orientation='h', text_auto=True, title="Top 10 máy hỏng nhiều"), use_container_width=True)

    with t2:
        cost_data = df_final.groupby('LIN_KIỆN')[['CP_DU_KIEN', 'CP_THUC_TE']].sum().reset_index()
        st.plotly_chart(px.bar(cost_data, x='LIN_KIỆN', y=['CP_DU_KIEN', 'CP_THUC_TE'], barmode='group', title="So sánh Chi phí Dự kiến vs Thực tế"), use_container_width=True)

    with t3:
        st.subheader("🤖 Trợ lý AI - Nhận định dữ liệu")
        total_ca = len(df_final)
        top_may = df_final['MÃ_MÁY'].value_counts().idxmax()
        cl = df_final['CHENH_LECH'].sum()
        st.info(f"**Nhận xét:** Ghi nhận {total_ca} ca. Máy {top_may} cần lưu ý đặc biệt. Tài chính lệch {cl:,.0f} VNĐ.")

    with t4: st.dataframe(df_final, use_container_width=True)

    with t5:
        h_db = df_fin.groupby('MÃ_MÁY').agg({'NGÀY': 'count', 'CP_THUC_TE': 'sum'}).reset_index()
        h_db.columns = ['Mã Máy', 'Tổng lần hỏng', 'Tổng chi phí']
        st.dataframe(h_db.sort_values('Tổng lần hỏng', ascending=False), use_container_width=True)

    with t6:
        st.subheader("🔮 Dự báo & Cảnh báo sớm")
        df_sorted = df_fin.sort_values(['MÃ_MÁY', 'NGÀY'])
        df_sorted['KHOANG_CACH'] = df_sorted.groupby('MÃ_MÁY')['NGÀY'].diff().dt.days
        warnings = df_sorted[df_sorted['KHOANG_CACH'] <= 60]
        if not warnings.empty:
            st.warning(f"Cảnh báo: {len(warnings)} ca hỏng lại trong vòng 60 ngày!")
            st.dataframe(warnings[['MÃ_MÁY', 'NGÀY', 'KHOANG_CACH']], use_container_width=True)

    # --- TAB 7: ĐÂY LÀ PHẦN KHO LOGISTICS HỢP NHẤT ---
    with t7:
        if not df_wh.empty:
            st.subheader("📦 Điều hành Kho & Logistics (Real-time)")
            
            # KPI Kho
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Tổng thiết bị nhận", len(df_wh))
            k2.metric("Chờ xuất kho (Đợi R)", len(df_wh[df_wh['TRẠNG_THÁI'] == "🔵 KHO NHẬN (ĐỢI R)"]))
            k3.metric("Đang sửa ngoài", len(df_wh[df_wh['TRẠNG_THÁI'] == "🟠 ĐANG SỬA NGOÀI"]))
            k4.metric("Máy Thanh lý", len(df_wh[df_wh['TRẠNG_THÁI'] == "🔴 THANH LÝ"]))
            
            # Đối soát vùng miền
            st.write("---")
            sum_wh = df_wh.groupby(['VÙNG', 'TRẠNG_THÁI']).size().unstack(fill_value=0).reset_index()
            st.markdown("**Bảng đối soát tồn kho theo Vùng:**")
            st.table(sum_wh)

            # Chi tiết tồn đọng
            c_l, c_r = st.columns(2)
            with c_l:
                st.error("🚨 **DANH SÁCH THANH LÝ (Cần thu hồi)**")
                st.dataframe(df_wh[df_wh['TRẠNG_THÁI'] == "🔴 THANH LÝ"][['VÙNG','MÃ_MÁY','KTTT','SBN']], use_container_width=True, hide_index=True)
            with c_r:
                st.info("📦 **MÁY CHỜ XUẤT KHO (Cần lệnh R)**")
                st.dataframe(df_wh[df_wh['TRẠNG_THÁI'] == "🔵 KHO NHẬN (ĐỢI R)"][['VÙNG','MÃ_MÁY','AGING','GIAO_LAI']], use_container_width=True, hide_index=True)
        else:
            st.error("Không tìm thấy dữ liệu Kho vận. Vui lòng kiểm tra lại Sheets Miền Bắc/Đà Nẵng.")

else:
    st.warning("Hệ thống đang chờ kết nối dữ liệu...")
