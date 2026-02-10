import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from datetime import datetime

# --- 1. KẾT NỐI HỆ THỐNG ---
url = "https://cigbnbaanpebwrufzxfg.supabase.co"
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. HÀM XỬ LÝ DỮ LIỆU (BẢO TỒN DI SẢN) ---
@st.cache_data(ttl=30)
def load_repair_data_final():
    try:
        res = supabase.table("repair_cases").select("*").order("created_at", desc=True).execute()
        if not res.data: return pd.DataFrame()
        
        df = pd.DataFrame(res.data)
        
        # --- FIX CỘT NGÀY (Mapping di sản sang DB thực tế) ---
        # Kiểm tra nếu DB dùng 'confirmed_' thay vì 'confirmed_date'
        target_date_col = 'confirmed_' if 'confirmed_' in df.columns else 'confirmed_date'
        
        df['confirmed_dt'] = pd.to_datetime(df[target_date_col], errors='coerce')
        df['created_dt'] = pd.to_datetime(df['created_at'], errors='coerce')
        
        # Loại bỏ dòng không có ngày để tránh lỗi biểu đồ
        df = df.dropna(subset=['confirmed_dt'])

        # Chiều thời gian
        df['NĂM'] = df['confirmed_dt'].dt.year.astype(int)
        df['THÁNG'] = df['confirmed_dt'].dt.month.astype(int)
        day_map = {'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
                   'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ Nhật'}
        df['THỨ'] = df['confirmed_dt'].dt.day_name().map(day_map)

        # --- FIX CỘT CHI PHÍ ---
        # Map đúng cột compensation từ DB thành CHI_PHÍ
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)
        
        return df.sort_values(by='created_dt', ascending=False)
    except Exception as e:
        st.error(f"Lỗi hệ thống tải data: {e}")
        return pd.DataFrame()

# --- 3. GIAO DIỆN CHÍNH ---
def main():
    st.set_page_config(page_title="4ORANGES OPS 2026", layout="wide", page_icon="🎨")
    df_db = load_repair_data_final()

    # Tabs tập trung
    tab_dash, tab_admin, tab_ai = st.tabs(["📊 BÁO CÁO VẬN HÀNH", "📥 QUẢN TRỊ HỆ THỐNG", "🧠 AI INSIGHTS"])

    # --- TAB 1: BÁO CÁO VẬN HÀNH ---
    with tab_dash:
        if df_db.empty:
            st.info("Chưa có dữ liệu. Vui lòng nạp ở Tab Quản trị.")
        else:
            with st.sidebar:
                st.header("⚙️ BỘ LỌC")
                if st.button("🔄 LÀM MỚI DỮ LIỆU", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()
                
                f_mode = st.radio("Chế độ lọc:", ["Tháng/Năm", "Khoảng ngày"])
                if f_mode == "Tháng/Năm":
                    y_list = sorted(df_db['NĂM'].unique(), reverse=True)
                    sel_y = st.selectbox("📅 Năm", y_list)
                    m_list = sorted(df_db[df_db['NĂM'] == sel_y]['THÁNG'].unique().tolist())
                    sel_m = st.selectbox("📆 Tháng", ["Tất cả"] + m_list)
                    df_view = df_db[df_db['NĂM'] == sel_y].copy()
                    if sel_m != "Tất cả": df_view = df_view[df_view['THÁNG'] == sel_m]
                else:
                    d_range = st.date_input("Chọn ngày", [df_db['confirmed_dt'].min(), df_db['confirmed_dt'].max()])
                    df_view = df_db[(df_db['confirmed_dt'].dt.date >= d_range[0]) & (df_db['confirmed_dt'].dt.date <= d_range[1])].copy() if len(d_range)==2 else df_db

            st.title("🚀 Chỉ Số Vận Hành")
            c1, c2, c3 = st.columns(3)
            c1.metric("💰 TỔNG CHI PHÍ", f"{df_view['CHI_PHÍ'].sum():,.0f} đ")
            c2.metric("🛠️ SỐ CA", f"{len(df_view)} ca")
            c3.metric("🏢 ĐIỂM NÓNG", df_view['branch'].value_counts().idxmax() if not df_view.empty else "N/A")

            st.divider()
            order = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ Nhật']
            day_stats = df_view['THỨ'].value_counts().reindex(order).fillna(0).reset_index()
            day_stats.columns = ['NGÀY_TRONG_TUẦN', 'SỐ_CA']
            st.plotly_chart(px.area(day_stats, x='NGÀY_TRONG_TUẦN', y='SỐ_CA', markers=True, title="Xu hướng sự vụ theo thứ"), use_container_width=True)

    # --- TAB 2: QUẢN TRỊ HỆ THỐNG ---
    with tab_admin:
        st.title("📥 Quản Trị & Điều Hành Chi Nhánh")
        ad_sub1, ad_sub2, ad_sub3 = st.tabs(["➕ NHẬP LIỆU", "🏢 CHI NHÁNH", "📜 AUDIT"])

        with ad_sub1:
            c_up, c_man = st.columns([4, 6])
            with c_up:
                st.subheader("📂 CSV Import")
                up_file = st.file_uploader("Chọn file CSV", type="csv", key="csv_admin")
                if up_file:
                    df_up = pd.read_csv(up_file)
                    if st.button(f"🚀 Xác nhận nạp {len(df_up)} dòng", use_container_width=True):
                        try:
                            supabase.table("repair_cases").upsert(df_up.to_dict(orient='records')).execute()
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi nạp File: {e}")

            with c_man:
                with st.form("f_man_enterprise", clear_on_submit=True):
                    st.subheader("✍️ Nhập ca sửa chữa đơn lẻ")
                    m1, m2 = st.columns(2)
                    with m1:
                        f_machine = st.text_input("Mã máy *")
                        f_branch = st.selectbox("Chi nhánh *", ["Miền Bắc", "Miền Trung", "Miền Nam"])
                        f_cost = st.number_input("Chi phí thực tế (đ)", min_value=0, step=10000)
                    with m2:
                        f_customer = st.text_input("Tên khách hàng *")
                        f_confirmed_date = st.date_input("Ngày xác nhận", value=datetime.now())
                        f_reason = st.text_input("Nguyên nhân hư hỏng *") # Sếp muốn nhân viên tự đánh
                    
                    f_note = st.text_area("Ghi chú chi tiết")
                    if st.form_submit_button("💾 Lưu vào cơ sở dữ liệu", use_container_width=True, type="primary"):
                        if not f_machine or not f_customer or not f_reason:
                            st.warning("⚠️ Vui lòng điền đủ các trường (*)")
                        else:
                            record = {
                                "machine_": f_machine.strip().upper(),
                                "branch": f_branch,
                                "customer_": f_customer.strip(),
                                "confirmed_": f_confirmed_date.isoformat(),
                                "issue_reason": f_reason.strip(),
                                "note": f_note.strip() if f_note else "",
                                "compensation": float(f_cost),
                                "is_unrepa": False
                            }
                            try:
                                supabase.table("repair_cases").insert(record).execute()
                                st.success("✅ Đã lưu thành công!")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Lỗi Database: {e}")

        with ad_sub2:
            st.subheader("🏢 Theo dõi vận hành theo chi nhánh")
            sel_b = st.selectbox("Chọn chi nhánh xem nhanh", ["Miền Bắc", "Miền Trung", "Miền Nam"])
            if not df_db.empty:
                # Dùng machine_ (có gạch dưới) theo đúng DB sếp gửi
                m_col = 'machine_' if 'machine_' in df_db.columns else 'machine_id'
                df_b = df_db[df_db['branch'] == sel_b]
                if not df_b.empty:
                    m_view = df_b.groupby(m_col).agg(ca=('id','count'), tien=('CHI_PHÍ','sum')).reset_index()
                    st.dataframe(m_view.sort_values('ca', ascending=False), use_container_width=True)

        with ad_sub3:
            st.subheader("📜 Nhật ký gần đây")
            if not df_db.empty:
                st.dataframe(df_db.head(10), use_container_width=True)

    # --- TAB 3: AI INSIGHTS ---
    with tab_ai:
        st.title("🧠 Trợ Lý AI Phân Tích")
        if df_db.empty or len(df_db) < 5:
            st.warning("⚠️ Cần thêm dữ liệu để AI phân tích.")
        else:
            # FIX: Đảm bảo dùng đúng tên cột machine_ cho toàn bộ AI
            m_col_ai = 'machine_' if 'machine_' in df_db.columns else 'machine_id'
            
            ai_1, ai_2, ai_3 = st.tabs(["🚩 CẢNH BÁO", "🏗️ RỦI RO THIẾT BỊ", "📊 DỰ BÁO"])

            with ai_1:
                threshold = df_db['CHI_PHÍ'].mean() + 2 * df_db['CHI_PHÍ'].std()
                anomalies = df_db[df_db['CHI_PHÍ'] > threshold]
                if not anomalies.empty:
                    st.error(f"Phát hiện {len(anomalies)} ca vượt ngưỡng chi phí!")
                    st.dataframe(anomalies[['confirmed_dt', m_col_ai, 'CHI_PHÍ']])
                else:
                    st.success("Không có bất thường chi phí.")

            with ai_2:
                m_stats = df_db.groupby(m_col_ai).agg(count=('id','count'), cost=('CHI_PHÍ','sum')).reset_index()
                m_stats['risk_score'] = ((m_stats['count']/m_stats['count'].max())*0.6 + (m_stats['cost']/m_stats['cost'].max())*0.4).round(2)
                st.plotly_chart(px.bar(m_stats.nlargest(10, 'risk_score'), x='risk_score', y=m_col_ai, orientation='h', title="Top 10 Máy Rủi Ro Cao"))

            with ai_3:
                monthly = df_db.groupby(['NĂM', 'THÁNG'])['CHI_PHÍ'].sum().reset_index()
                if len(monthly) >= 2:
                    forecast_val = monthly['CHI_PHÍ'].rolling(3, min_periods=1).mean().iloc[-1]
                    st.metric("Dự báo chi phí tháng tới", f"{forecast_val:,.0f} đ")
                    
            st.divider()
            q = st.text_input("💬 Hỏi nhanh dữ liệu (Ví dụ: 'Máy nào hỏng nhất?')")
            if q and not df_db.empty:
                top_m = df_db[m_col_ai].value_counts().index[0]
                st.info(f"🤖 Theo dữ liệu: Máy **{top_m}** đang có tần suất sửa chữa cao nhất.")

if __name__ == "__main__":
    main()
