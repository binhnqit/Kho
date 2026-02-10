import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from datetime import datetime

# --- 1. KẾT NỐI HỆ THỐNG ---
url = "https://cigbnbaanpebwrufzxfg.supabase.co"
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. HÀM XỬ LÝ DỮ LIỆU (ANTI-NGỐC MODE) ---
@st.cache_data(ttl=30)
def load_repair_data_final():
    try:
        res = supabase.table("repair_cases").select("*").order("created_at", desc=True).execute()
        if not res.data: return pd.DataFrame()
        
        df = pd.DataFrame(res.data)
        
        # 🛡️ CHIẾN THUẬT QUÉT CỘT: Tìm cột ngày xác nhận
        # Thử mọi khả năng có thể xảy ra trong DB của sếp
        date_candidates = ['confirmed', 'confirmed_', 'confirmed_date', 'received_', 'created_at']
        found_date_col = next((c for c in date_candidates if c in df.columns), None)
        
        if found_date_col:
            df['confirmed_dt'] = pd.to_datetime(df[found_date_col], errors='coerce')
        else:
            # Nếu không tìm thấy cột nào, dùng tạm thời gian hiện tại để cứu App
            df['confirmed_dt'] = pd.Timestamp.now()

        # 🛡️ QUÉT CỘT CHI PHÍ
        cost_candidates = ['compensa', 'compensation', 'cost', 'money']
        found_cost_col = next((c for c in cost_candidates if c in df.columns), None)
        df['CHI_PHÍ'] = pd.to_numeric(df[found_cost_col], errors='coerce').fillna(0) if found_cost_col else 0

        # Loại bỏ rác và tạo chiều thời gian
        df = df.dropna(subset=['confirmed_dt'])
        df['NĂM'] = df['confirmed_dt'].dt.year.astype(int)
        df['THÁNG'] = df['confirmed_dt'].dt.month.astype(int)
        day_map = {'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
                   'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ Nhật'}
        df['THỨ'] = df['confirmed_dt'].dt.day_name().map(day_map)
        
        return df
    except Exception as e:
        st.error(f"Lỗi hệ thống tải data: {e}")
        return pd.DataFrame()

# --- 3. GIAO DIỆN CHÍNH ---
def main():
    st.set_page_config(page_title="4ORANGES OPS 2026", layout="wide", page_icon="🎨")
    df_db = load_repair_data_final()

    tab_dash, tab_admin, tab_ai = st.tabs(["📊 BÁO CÁO VẬN HÀNH", "📥 QUẢN TRỊ HỆ THỐNG", "🧠 AI INSIGHTS"])

    # --- TAB 1: BÁO CÁO VẬN HÀNH ---
    with tab_dash:
        if df_db.empty:
            st.info("Chưa có dữ liệu hoặc DB không phản hồi. Vui lòng kiểm tra Tab Quản trị.")
        else:
            st.title("🚀 Chỉ Số Vận Hành")
            c1, c2, c3 = st.columns(3)
            c1.metric("💰 TỔNG CHI PHÍ", f"{df_db['CHI_PHÍ'].sum():,.0f} đ")
            c2.metric("🛠️ SỐ CA", f"{len(df_db)} ca")
            
            # Kiểm tra cột branch để tránh lỗi idxmax
            if 'branch' in df_db.columns:
                c3.metric("🏢 ĐIỂM NÓNG", df_db['branch'].value_counts().idxmax())
            
            st.divider()
            # Vẽ biểu đồ (Chỉ vẽ khi có dữ liệu thời gian chuẩn)
            order = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ Nhật']
            day_stats = df_db['THỨ'].value_counts().reindex(order).fillna(0).reset_index()
            day_stats.columns = ['NGÀY_TRONG_TUẦN', 'SỐ_CA']
            st.plotly_chart(px.area(day_stats, x='NGÀY_TRONG_TUẦN', y='SỐ_CA', markers=True, title="Xu hướng sự vụ theo thứ"), use_container_width=True)

    # --- TAB 2: QUẢN TRỊ HỆ THỐNG ---
    with tab_admin:
        st.title("📥 Quản Trị & Điều Hành")
        
        # PHẦN GỠ RỐI (DEBUG) - GIÚP SẾP NHÌN THẤY TÊN CỘT THẬT
        with st.expander("🛠️ KIỂM TRA CẤU TRÚC DATABASE (DÀNH CHO SẾP)"):
            if not df_db.empty:
                st.write("Danh sách cột App đang nhận được từ Supabase:")
                st.code(list(df_db.columns))
                st.write("Dữ liệu mẫu:")
                st.write(df_db.head(3))
            else:
                st.error("Không thể kết nối lấy cột. Kiểm tra SUPABASE_KEY.")

        # FORM NHẬP LIỆU (GỬI ĐÚNG THEO ẢNH SẾP GỬI)
        with st.form("f_fix_input"):
            st.subheader("✍️ Nhập ca sửa chữa đơn lẻ")
            m1, m2 = st.columns(2)
            f_machine = m1.text_input("Mã máy (machine_)")
            f_customer = m2.text_input("Tên khách hàng (customer_)")
            f_cost = m1.number_input("Chi phí (compensa)", min_value=0)
            f_confirmed = m2.date_input("Ngày xác nhận (confirmed)", value=datetime.now())
            f_reason = st.text_input("Nguyên nhân (issue_reason)")
            
            if st.form_submit_button("💾 LƯU VÀO DATABASE"):
                record = {
                    "machine_": f_machine.strip().upper(),
                    "customer_": f_customer.strip(),
                    "compensa": float(f_cost),
                    "confirmed": f_confirmed.isoformat(),
                    "issue_reason": f_reason,
                    "branch": "Miền Nam", # Mặc định để tránh lỗi NULL
                    "is_unrepa": False,
                    "received_": datetime.now().isoformat()
                }
                try:
                    supabase.table("repair_cases").insert(record).execute()
                    st.success("✅ Đã lưu! Đang làm mới...")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi lưu: {e}")

    # --- TAB 3: AI INSIGHTS ---

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
