import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from datetime import datetime

# --- 1. KẾT NỐI HỆ THỐNG ---
url = "https://cigbnbaanpebwrufzxfg.supabase.co"
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. HÀM XỬ LÝ DỮ LIỆU (HARDENED LOGIC) ---
@st.cache_data(ttl=30)
def load_repair_data_final():
    try:
        res = supabase.table("repair_cases").select("*").order("created_at", desc=True).execute()
        if not res.data: return pd.DataFrame()
        
        df = pd.DataFrame(res.data)
        df['confirmed_dt'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        df['created_dt'] = pd.to_datetime(df['created_at'], errors='coerce')
        df = df.dropna(subset=['confirmed_dt'])

        # Chiều thời gian
        df['NĂM'] = df['confirmed_dt'].dt.year.astype(int)
        df['THÁNG'] = df['confirmed_dt'].dt.month.astype(int)
        day_map = {'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
                   'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ Nhật'}
        df['THỨ'] = df['confirmed_dt'].dt.day_name().map(day_map)

        # Map đúng cột compensation từ DB thành CHI_PHÍ để vẽ biểu đồ
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)
        return df.sort_values(by='created_dt', ascending=False)
    except Exception as e:
        st.error(f"Lỗi hệ thống tải data: {e}")
        return pd.DataFrame()

# --- 3. GIAO DIỆN CHÍNH ---
def main():
    st.set_page_config(page_title="4ORANGES OPS 2026", layout="wide", page_icon="🎨")
    df_db = load_repair_data_final()

    # KHAI BÁO TABS TẬP TRUNG (FIX LỖI NAMEERROR)
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
            # Biểu đồ xu hướng (Fix lỗi Plotly index)
            order = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ Nhật']
            day_stats = df_view['THỨ'].value_counts().reindex(order).fillna(0).reset_index()
            day_stats.columns = ['NGÀY_TRONG_TUẦN', 'SỐ_CA']
            st.plotly_chart(px.area(day_stats, x='NGÀY_TRONG_TUẦN', y='SỐ_CA', markers=True, title="Xu hướng sự vụ theo thứ"), use_container_width=True)

    # --- TAB 2: QUẢN TRỊ (BẢN NÂNG CẤP AUDIT) ---
    with tab_admin:
        st.title("📥 Quản Trị & Điều Hành Chi Nhánh")
        ad_sub1, ad_sub2, ad_sub3 = st.tabs(["➕ NHẬP LIỆU", "🏢 TÌNH TRẠNG CHI NHÁNH", "📜 TRUY VẾT & AUDIT"])

        with ad_sub1:
            c_up, c_man = st.columns([4, 6])
            with c_up:
                st.subheader("📂 CSV Import")
                up_file = st.file_uploader("Upload CSV", type="csv")
                if up_file:
                    df_up = pd.read_csv(up_file)
                    b_id = f"BATCH_{datetime.now().strftime('%m%d_%H%M')}"
                    df_up['batch_id'], df_up['created_at'] = b_id, datetime.now().isoformat()
                    if st.button(f"🚀 Nạp Lô {b_id}"):
                        supabase.table("repair_cases").upsert(df_up.to_dict(orient='records')).execute()
                        st.cache_data.clear()
                        st.rerun()
            with c_man:
            # FORM NHẬP TAY CHUẨN ENTERPRISE
            with st.form("f_man_enterprise", clear_on_submit=True):
                st.subheader("✍️ Nhập ca sửa chữa đơn lẻ")
                c1, c2 = st.columns(2)
                with c1:
                    f_machine = st.text_input("Mã máy *")
                    f_branch = st.selectbox("Chi nhánh *", ["Miền Bắc", "Miền Trung", "Miền Nam"])
                    f_cost = st.number_input("Chi phí thực tế (đ)", min_value=0, step=10000)
                with c2:
                    f_confirmer = st.text_input("Người xác nhận *")
                    f_confirmed_date = st.date_input("Ngày xác nhận", value=datetime.now())
                    # Sửa theo ý sếp: Nhân viên tự đánh nguyên nhân thay vì chọn mẫu
                    f_reason = st.text_input("Nguyên nhân hư hỏng *", placeholder="VD: Bể bạc đạn, chập mạch...")
                
                f_note = st.text_area("Ghi chú chi tiết (nếu có)")

                if st.form_submit_button("💾 Lưu vào cơ sở dữ liệu", use_container_width=True, type="primary"):
                    if not f_machine or not f_confirmer or not f_reason:
                        st.warning("⚠️ Vui lòng điền đủ: Mã máy, Người xác nhận và Nguyên nhân.")
                    else:
                        # Gói dữ liệu khớp hoàn toàn với cấu trúc bảng Supabase
                        record = {
                            "machine_id": f_machine.strip().upper(),
                            "branch": f_branch,
                            "compensation": float(f_cost),
                            "confirmed_by": f_confirmer.strip(),
                            "confirmed_date": f_confirmed_date.isoformat(),
                            "issue_reason": f_reason.strip(), # Nhân viên tự đánh
                            "note": f_note.strip() if f_note else "",
                            "batch_id": f"MANUAL_{datetime.now().strftime('%Y%m%d')}",
                            "created_at": datetime.now().isoformat()
                        }
                        
                        try:
                            # Thực thi lệnh insert
                            supabase.table("repair_cases").insert(record).execute()
                            st.success("✅ Đã lưu ca sửa chữa thành công!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            # Hiện lỗi chi tiết để debug nếu API vẫn từ chối
                            st.error(f"Lỗi Database: {e}")

        with ad_sub2:
            sel_branch = st.selectbox("Chọn chi nhánh xem nhanh", ["Miền Bắc", "Miền Trung", "Miền Nam"])
            df_b = df_db[df_db['branch'] == sel_branch]
            if not df_b.empty:
                m_view = df_b.groupby('machine_id').agg(so_lan=('id','count'), tong_tien=('CHI_PHÍ','sum')).reset_index()
                st.dataframe(m_view.sort_values('so_lan', ascending=False), use_container_width=True, hide_index=True)

        with ad_sub3:
            if 'batch_id' in df_db.columns:
                history = df_db.groupby('batch_id').agg(dong=('id','count'), tien=('CHI_PHÍ','sum'), ngay=('created_dt','max')).reset_index()
                st.dataframe(history.sort_values('ngay', ascending=False), use_container_width=True)
                target = st.selectbox("Chọn lô Rollback:", history['batch_id'].unique())
                if st.button("🗑️ XOÁ VĨNH VIỄN LÔ NÀY"):
                    supabase.table("repair_cases").delete().eq("batch_id", target).execute()
                    st.cache_data.clear()
                    st.rerun()
    with tab_ai:
        st.title("🧠 Trợ Lý AI Phân Tích")
        
        # 1. Hardening Data
        cost_series = df_db['CHI_PHÍ'].dropna()
        if len(cost_series) < 10:
            st.warning("⚠️ Dữ liệu quá mỏng để AI phân tích. Cần tối thiểu 10 ca.")
            st.stop()

        ai_1, ai_2, ai_3 = st.tabs(["🚩 CẢNH BÁO", "🏗️ RỦI RO THIẾT BỊ", "📊 DỰ BÁO"])

        with ai_1:
            # Anomaly Detection (2-Sigma)
            threshold = cost_series.mean() + 2 * cost_series.std()
            anomalies = df_db[df_db['CHI_PHÍ'] > threshold]
            if not anomalies.empty:
                st.error(f"Phát hiện {len(anomalies)} ca vượt ngưỡng chi phí an toàn!")
                st.dataframe(anomalies[['confirmed_dt', 'machine_id', 'CHI_PHÍ']])
            else:
                st.success("Không phát hiện bất thường về chi phí.")

        with ai_2:
            # Risk Scoring (Normalized)
            m_stats = df_db.groupby('machine_id').agg(count=('machine_id','count'), cost=('CHI_PHÍ','sum')).reset_index()
            # Normalize về thang 0-1
            m_stats['freq_norm'] = m_stats['count'] / m_stats['count'].max()
            m_stats['cost_norm'] = m_stats['cost'] / m_stats['cost'].max()
            m_stats['risk_score'] = (m_stats['freq_norm'] * 0.6 + m_stats['cost_norm'] * 0.4).round(2)
            
            st.plotly_chart(px.bar(m_stats.nlargest(10, 'risk_score'), x='risk_score', y='machine_id', orientation='h', title="Top 10 Máy Rủi Ro Cao (Đã Normalize)"))

        with ai_3:
            # Forecast & Latest Month Fix
            monthly = df_db.groupby(['NĂM', 'THÁNG'])['CHI_PHÍ'].sum().reset_index()
            if len(monthly) >= 2:
                # Dùng MAX để lấy tháng mới nhất
                latest_data = monthly.sort_values(['NĂM', 'THÁNG']).iloc[-1]
                curr_month_val = latest_data['CHI_PHÍ']
                forecast_val = monthly['CHI_PHÍ'].rolling(3, min_periods=1).mean().iloc[-1]
                
                # Bọc chia cho 0
                diff = ((forecast_val / curr_month_val) - 1) * 100 if curr_month_val > 0 else 0
                
                c_f1, c_f2 = st.columns(2)
                c_f1.metric("Dự báo tháng tới", f"{forecast_val:,.0f} đ")
                c_f2.metric("Biến động dự kiến", f"{diff:.1f}%", delta=f"{diff:.1f}%", delta_color="inverse")

            # NLP Parser nhẹ
            st.divider()
            q = st.text_input("💬 Hỏi AI (Ví dụ: 'Máy nào hỏng ở Miền Bắc?')")
            if q:
                branch_key = "Miền Bắc" if "bắc" in q.lower() else "Miền Nam" if "nam" in q.lower() else None
                if branch_key:
                    res_q = df_db[df_db['branch'] == branch_key]['machine_id'].value_counts()
                    st.info(f"🤖 Vùng {branch_key}: Máy {res_q.index[0]} hỏng nhiều nhất ({res_q.values[0]} lần).")

if __name__ == "__main__":
    main()
