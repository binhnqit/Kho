import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from datetime import datetime

# --- 1. KẾT NỐI HỆ THỐNG ---
url = "https://cigbnbaanpebwrufzxfg.supabase.co"
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. HÀM XỬ LÝ DỮ LIỆU (BỀN BỈ) ---
@st.cache_data(ttl=30)
def load_repair_data_final():
    try:
        res = supabase.table("repair_cases").select("*").order("created_at", desc=True).execute()
        if not res.data or len(res.data) == 0: 
            return pd.DataFrame()
        
        df = pd.DataFrame(res.data)
        
        # Dò tìm cột ngày (confirmed hoặc confirmed_ hoặc created_at)
        date_col = next((c for c in ['confirmed', 'confirmed_', 'created_at'] if c in df.columns), None)
        if date_col:
            df['confirmed_dt'] = pd.to_datetime(df[date_col], errors='coerce')
        else:
            df['confirmed_dt'] = pd.Timestamp.now()

        # Dò tìm cột chi phí (compensa hoặc compensation)
        cost_col = next((c for c in ['compensa', 'compensation'] if c in df.columns), None)
        df['CHI_PHÍ'] = pd.to_numeric(df[cost_col], errors='coerce').fillna(0) if cost_col else 0
        
        # Tạo các cột thời gian phục vụ báo cáo
        df['NĂM'] = df['confirmed_dt'].dt.year
        df['THÁNG'] = df['confirmed_dt'].dt.month
        day_map = {'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
                   'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ Nhật'}
        df['THỨ'] = df['confirmed_dt'].dt.day_name().map(day_map)
        
        return df
    except Exception as e:
        return pd.DataFrame()

# --- 3. GIAO DIỆN CHÍNH ---
def main():
    st.set_page_config(page_title="4ORANGES OPS 2026", layout="wide", page_icon="🎨")
    df_db = load_repair_data_final()

    tab_dash, tab_admin, tab_ai = st.tabs(["📊 BÁO CÁO", "📥 QUẢN TRỊ", "🧠 AI INSIGHTS"])

    with tab_dash:
        if df_db.empty:
            st.info("Hệ thống đang chờ dữ liệu từ Tab Quản trị.")
        else:
            st.title("🚀 Chỉ Số Vận Hành")
            c1, c2 = st.columns(2)
            c1.metric("💰 TỔNG CHI PHÍ", f"{df_db['CHI_PHÍ'].sum():,.0f} đ")
            c2.metric("🛠️ SỐ CA", f"{len(df_db)} ca")
            st.dataframe(df_db.head(10))

    with tab_admin:
        st.subheader("✍️ Nhập ca sửa chữa")
        with st.form("f_input", clear_on_submit=True):
            m1, m2 = st.columns(2)
            f_m = m1.text_input("Mã máy (machine_) *")
            f_c = m2.text_input("Khách hàng (customer_) *")
            f_p = m1.number_input("Chi phí (compensa)", min_value=0)
            f_r = m2.text_input("Nguyên nhân (issue_reason) *")
            
            if st.form_submit_button("💾 LƯU DỮ LIỆU"):
                if f_m and f_c and f_r:
                    record = {
                        "machine_": f_m.strip().upper(),
                        "customer_": f_c.strip(),
                        "compensa": float(f_p),
                        "confirmed": datetime.now().isoformat(),
                        "issue_reason": f_r.strip(),
                        "branch": "Miền Nam",
                        "is_unrepa": False
                    }
                    supabase.table("repair_cases").insert(record).execute()
                    st.success("Đã lưu thành công!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.warning("Vui lòng điền đủ các mục có dấu *")
    # --- TAB 3: AI INSIGHTS (BẢO TỒN DI SẢN) ---
    with tab_ai:
        st.title("🧠 Trợ Lý AI Phân Tích")
        if df_db.empty or len(df_db) < 5:
            st.warning("⚠️ Cần tối thiểu 5 ca để AI bắt đầu phân tích.")
        else:
            ai_1, ai_2, ai_3 = st.tabs(["🚩 CẢNH BÁO", "🏗️ RỦI RO THIẾT BỊ", "📊 DỰ BÁO"])

            with ai_1:
                cost_series = df_db['CHI_PHÍ']
                threshold = cost_series.mean() + 2 * cost_series.std()
                anomalies = df_db[df_db['CHI_PHÍ'] > threshold]
                if not anomalies.empty:
                    st.error(f"Phát hiện {len(anomalies)} ca chi phí cao bất thường!")
                    st.dataframe(anomalies[['confirmed', 'machine_', 'CHI_PHÍ']])
                else:
                    st.success("Chi phí ổn định.")

            with ai_2:
                m_stats = df_db.groupby('machine_').agg(count=('id','count'), cost=('CHI_PHÍ','sum')).reset_index()
                m_stats['risk_score'] = ((m_stats['count']/m_stats['count'].max())*0.6 + (m_stats['cost']/m_stats['cost'].max())*0.4).round(2)
                st.plotly_chart(px.bar(m_stats.nlargest(10, 'risk_score'), x='risk_score', y='machine_', orientation='h', title="Top 10 Máy Rủi Ro Cao"))

            with ai_3:
                monthly = df_db.groupby(['NĂM', 'THÁNG'])['CHI_PHÍ'].sum().reset_index()
                if len(monthly) >= 2:
                    forecast_val = monthly['CHI_PHÍ'].rolling(3, min_periods=1).mean().iloc[-1]
                    st.metric("Dự báo chi phí tháng tới", f"{forecast_val:,.0f} đ")

if __name__ == "__main__":
    main()
