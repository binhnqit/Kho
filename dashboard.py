import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from datetime import datetime

# --- 1. KẾT NỐI HỆ THỐNG ---
url = "https://cigbnbaanpebwrufzxfg.supabase.co"
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. HÀM XỬ LÝ DỮ LIỆU (KHỚP SCHEMA THỰC TẾ) ---
@st.cache_data(ttl=30)
def load_repair_data_final():
    try:
        res = supabase.table("repair_cases").select("*").order("created_at", desc=True).execute()
        if not res.data: return pd.DataFrame()
        
        df = pd.DataFrame(res.data)
        
        # --- ĐỒNG BỘ CỘT NGÀY THEO SCHEMA ---
        # Sử dụng 'confirmed_date' là gốc để tính toán báo cáo
        df['confirmed_dt'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        df['created_dt'] = pd.to_datetime(df['created_at'], errors='coerce')
        
        # Loại bỏ dòng không có ngày để tránh lỗi biểu đồ
        df = df.dropna(subset=['confirmed_dt'])

        # Chiều thời gian
        df['NĂM'] = df['confirmed_dt'].dt.year.astype(int)
        df['THÁNG'] = df['confirmed_dt'].dt.month.astype(int)
        day_map = {'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
                   'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ Nhật'}
        df['THỨ'] = df['confirmed_dt'].dt.day_name().map(day_map)

        # --- ĐỒNG BỘ CỘT CHI PHÍ THEO SCHEMA ---
        # Sử dụng 'compensation' thay vì 'compensa'
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)
        
        return df.sort_values(by='created_dt', ascending=False)
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
                    d_range = st.date_input("Chọn ngày", [df_db['confirmed_dt'].min().date(), df_db['confirmed_dt'].max().date()])
                    df_view = df_db[(df_db['confirmed_dt'].dt.date >= d_range[0]) & (df_db['confirmed_dt'].dt.date <= d_range[1])].copy() if len(d_range)==2 else df_db

            st.title("🚀 Chỉ Số Vận Hành")
            c1, c2, c3 = st.columns(3)
            c1.metric("💰 TỔNG CHI PHÍ", f"{df_view['CHI_PHÍ'].sum():,.0f} đ")
            c2.metric("🛠️ SỐ CA", f"{len(df_view)} ca")
            # Sử dụng 'branch' từ schema
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
                        f_machine = st.text_input("Mã máy (machine_id) *")
                        f_branch = st.selectbox("Chi nhánh *", ["Miền Bắc", "Miền Trung", "Miền Nam"])
                        f_cost = st.number_input("Chi phí (compensation)", min_value=0, step=10000)
                    with m2:
                        f_customer = st.text_input("Tên khách hàng (customer_name) *")
                        f_confirmed_date = st.date_input("Ngày xác nhận", value=datetime.now())
                        f_reason = st.text_input("Nguyên nhân (issue_reason) *")
                    
                    f_note = st.text_area("Ghi chú chi tiết")
                    if st.form_submit_button("💾 Lưu vào cơ sở dữ liệu", use_container_width=True, type="primary"):
                        if not f_machine or not f_customer or not f_reason:
                            st.warning("⚠️ Vui lòng điền đủ các trường (*)")
                        else:
                            # MAP CHÍNH XÁC TÊN CỘT THEO SCHEMA
                            record = {
                                "machine_id": f_machine.strip().upper(),
                                "branch": f_branch,
                                "customer_name": f_customer.strip(),
                                "received_date": datetime.now().isoformat(),
                                "confirmed_date": f_confirmed_date.isoformat(),
                                "issue_reason": f_reason.strip(),
                                "note": f_note.strip() if f_note else "",
                                "compensation": float(f_cost),
                                "is_unrepairable": False
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
                # Đồng bộ tên cột 'machine_id'
                m_col = 'machine_id' 
                df_b = df_db[df_db['branch'] == sel_b]
                if not df_b.empty:
                    m_view = df_b.groupby(m_col).agg(ca=('id','count'), tien=('CHI_PHÍ','sum')).reset_index()
                    st.dataframe(m_view.sort_values('ca', ascending=False), use_container_width=True)

        with ad_sub3:
            st.subheader("📜 Nhật ký gần đây")
            if not df_db.empty:
                st.dataframe(df_db.head(10), use_container_width=True)

    # --- TAB 3: AI INSIGHTS ---
    # --- TAB 3: AI ENTERPRISE INSIGHTS ---
with tab_ai:
    st.title("🧠 AI Decision Intelligence")
    st.caption("Phân tích – Chẩn đoán – Khuyến nghị – Dự báo")

    if df_db.empty or len(df_db) < 10:
        st.warning("⚠️ Chưa đủ dữ liệu để AI phân tích (tối thiểu 10 ca).")
    else:
        ai_warn, ai_root, ai_action, ai_forecast = st.tabs([
            "🚨 CẢNH BÁO SỚM",
            "🔍 NGUYÊN NHÂN GỐC",
            "🧩 KHUYẾN NGHỊ",
            "📈 DỰ BÁO"
        ])

        # =====================================================
        # 🚨 1. EARLY WARNING – CẢNH BÁO SỚM
        # =====================================================
        with ai_warn:
            st.subheader("🚨 Cảnh báo chi phí & tần suất bất thường")

            alerts = []

            for b in df_db['branch'].unique():
                df_b = df_db[df_db['branch'] == b]
                if len(df_b) < 5:
                    continue

                cost_th = df_b['CHI_PHÍ'].mean() + 2 * df_b['CHI_PHÍ'].std()
                freq_th = df_b.groupby('machine_id').size().mean() + 2

                ab_cost = df_b[df_b['CHI_PHÍ'] > cost_th]
                ab_freq = (
                    df_b.groupby('machine_id')
                    .size()
                    .reset_index(name='count')
                    .query("count > @freq_th")
                )

                if not ab_cost.empty:
                    alerts.append({
                        "branch": b,
                        "type": "Chi phí cao",
                        "cases": len(ab_cost),
                        "impact": "Nguy cơ vượt ngân sách"
                    })

                if not ab_freq.empty:
                    alerts.append({
                        "branch": b,
                        "type": "Tần suất cao",
                        "cases": len(ab_freq),
                        "impact": "Thiết bị kém ổn định"
                    })

            if alerts:
                st.error("⚠️ Phát hiện rủi ro vận hành")
                st.dataframe(pd.DataFrame(alerts), use_container_width=True)
            else:
                st.success("✅ Không phát hiện bất thường nghiêm trọng")

        # =====================================================
        # 🔍 2. ROOT CAUSE – NGUYÊN NHÂN GỐC
        # =====================================================
        with ai_root:
            st.subheader("🔍 Phân tích nguyên nhân gốc theo thiết bị")

            m_stats = df_db.groupby('machine_id').agg(
                total_cases=('id','count'),
                total_cost=('CHI_PHÍ','sum'),
                avg_cost=('CHI_PHÍ','mean'),
                branch=('branch','first')
            ).reset_index()

            # Chuẩn hoá score
            m_stats['freq_score'] = m_stats['total_cases'] / m_stats['total_cases'].max()
            m_stats['cost_score'] = m_stats['total_cost'] / m_stats['total_cost'].max()

            m_stats['risk_score'] = (0.6*m_stats['freq_score'] + 0.4*m_stats['cost_score']).round(2)

            def explain(r):
                if r['freq_score'] > 0.7 and r['cost_score'] > 0.7:
                    return "Tần suất cao + chi phí cao"
                if r['freq_score'] > 0.7:
                    return "Tần suất lỗi cao"
                if r['cost_score'] > 0.7:
                    return "Chi phí sửa cao"
                return "Bình thường"

            m_stats['root_cause'] = m_stats.apply(explain, axis=1)

            st.dataframe(
                m_stats.sort_values('risk_score', ascending=False)
                [['machine_id','branch','risk_score','root_cause']],
                use_container_width=True
            )

        # =====================================================
        # 🧩 3. ACTION RECOMMENDER – KHUYẾN NGHỊ
        # =====================================================
        with ai_action:
            st.subheader("🧩 Khuyến nghị hành động cho quản lý")

            recommendations = []

            for _, r in m_stats.iterrows():
                if r['risk_score'] >= 0.75:
                    recommendations.append({
                        "machine_id": r['machine_id'],
                        "branch": r['branch'],
                        "risk_score": r['risk_score'],
                        "recommendation": "Xem xét thay thế / kiểm tra toàn diện",
                        "expected_impact": "Giảm chi phí dài hạn"
                    })
                elif r['risk_score'] >= 0.55:
                    recommendations.append({
                        "machine_id": r['machine_id'],
                        "branch": r['branch'],
                        "risk_score": r['risk_score'],
                        "recommendation": "Tăng tần suất bảo trì",
                        "expected_impact": "Giảm số ca phát sinh"
                    })

            if recommendations:
                st.warning("📌 AI đề xuất các hành động ưu tiên")
                st.dataframe(pd.DataFrame(recommendations), use_container_width=True)
            else:
                st.success("✅ Không cần hành động đặc biệt")

        # =====================================================
        # 📈 4. FORECAST – DỰ BÁO
        # =====================================================
        with ai_forecast:
            st.subheader("📈 Dự báo chi phí theo chi nhánh")

            for b in df_db['branch'].unique():
                df_b = df_db[df_db['branch'] == b]
                monthly = df_b.groupby(['NĂM','THÁNG'])['CHI_PHÍ'].sum()

                if len(monthly) >= 3:
                    forecast = monthly.rolling(3, min_periods=1).mean().iloc[-1]
                    st.metric(
                        f"{b} – Dự báo tháng tới",
                        f"{forecast:,.0f} đ"
                    )


if __name__ == "__main__":
    main()
