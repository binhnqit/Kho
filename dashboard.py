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
        df['confirmed_dt'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        df['created_dt'] = pd.to_datetime(df['created_at'], errors='coerce')
        
        df = df.dropna(subset=['confirmed_dt'])

        df['NĂM'] = df['confirmed_dt'].dt.year.astype(int)
        df['THÁNG'] = df['confirmed_dt'].dt.month.astype(int)
        day_map = {'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
                   'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ Nhật'}
        df['THỨ'] = df['confirmed_dt'].dt.day_name().map(day_map)

        # --- ĐỒNG BỘ CỘT CHI PHÍ THEO SCHEMA ---
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)
        
        return df.sort_values(by='created_dt', ascending=False)
    except Exception as e:
        st.error(f"Lỗi hệ thống tải data: {e}")
        return pd.DataFrame()
def write_audit_log(action, table_name, record_id=None, old_data=None, new_data=None):
    """
    Ghi nhật ký hệ thống. 
    user_ctx lấy từ session_state (giả định bạn đã lưu khi login)
    """
    try:
        # Lấy thông tin người dùng từ session_state
        user_id = st.session_state.get('user_id', '00000000-0000-0000-0000-000000000000')
        user_role = st.session_state.get('user_role', 'guest')

        audit = {
            "user_id": user_id,
            "user_role": user_role,
            "action": action,
            "table_name": table_name,
            "record_id": str(record_id) if record_id else None,
            "old_data": old_data, # Supabase nhận dict cho cột jsonb
            "new_data": new_data,
            "created_at": datetime.now().isoformat()
        }
        supabase.table("audit_logs").insert(audit).execute()
    except Exception as e:
        st.error(f"Lỗi ghi Audit Log: {e}")
# --- 3. GIAO DIỆN CHÍNH ---
def main():
    st.set_page_config(page_title="4ORANGES OPS 2026", layout="wide", page_icon="🎨")
    df_db = load_repair_data_final()

    tab_dash, tab_admin, tab_ai, tab_alert, tab_kpi = st.tabs([
        "📊 BÁO CÁO VẬN HÀNH", 
        "📥 QUẢN TRỊ HỆ THỐNG", 
        "🧠 AI INSIGHTS",
        "🚨 CẢNH BÁO",
        "🎯 KPI QUẢN TRỊ"
    ])

    # =============================================================================
    # 📊 TAB BÁO CÁO VẬN HÀNH – ENTERPRISE EDITION
    # =============================================================================
    with tab_dash:
        st.title("📊 BÁO CÁO VẬN HÀNH – DECISION DASHBOARD")

        if df_db.empty:
            st.info("Chưa có dữ liệu. Vui lòng nạp ở Tab Quản trị.")
        else:
            # ---------- SIDEBAR FILTER ----------
            with st.sidebar:
                st.header("⚙️ BỘ LỌC BÁO CÁO")

                if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()

                f_mode = st.radio("Chế độ lọc thời gian", ["Tháng / Năm", "Khoảng ngày"])

                if f_mode == "Tháng / Năm":
                    y_list = sorted(df_db['NĂM'].unique(), reverse=True)
                    sel_y = st.selectbox("Năm", y_list)

                    m_list = sorted(df_db[df_db['NĂM'] == sel_y]['THÁNG'].unique())
                    sel_m = st.selectbox("Tháng", ["Tất cả"] + m_list)

                    df_view = df_db[df_db['NĂM'] == sel_y].copy()
                    if sel_m != "Tất cả":
                        df_view = df_view[df_view['THÁNG'] == sel_m]
                else:
                    d_range = st.date_input(
                        "Chọn khoảng ngày",
                        [
                            df_db['confirmed_dt'].min().date(),
                            df_db['confirmed_dt'].max().date()
                        ]
                    )
                    if isinstance(d_range, list) and len(d_range) == 2:
                        df_view = df_db[
                            (df_db['confirmed_dt'].dt.date >= d_range[0]) &
                            (df_db['confirmed_dt'].dt.date <= d_range[1])
                        ].copy()
                    else:
                        df_view = df_db.copy()

                sel_branch = st.multiselect(
                    "Chi nhánh",
                    options=sorted(df_db['branch'].unique()),
                    default=sorted(df_db['branch'].unique())
                )
                df_view = df_view[df_view['branch'].isin(sel_branch)]

            # ---------- KPI LAYER ----------
            st.subheader("🚀 Chỉ số tổng quan")

            if not df_view.empty:
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("💰 Tổng chi phí", f"{df_view['CHI_PHÍ'].sum():,.0f} đ")
                k2.metric("🛠️ Tổng số ca", f"{len(df_view)} ca")
                k3.metric("🏢 Chi nhánh HOT", df_view['branch'].value_counts().idxmax())
                k4.metric("⚠️ Máy rủi ro nhất", df_view['machine_id'].value_counts().idxmax())

                st.divider()

                # ---------- TREND ANALYSIS ----------
                st.subheader("📈 Xu hướng sự cố theo thời gian")
                trend = (
                    df_view
                    .groupby(['NĂM', 'THÁNG'])
                    .agg(so_ca=('id', 'count'), chi_phi=('CHI_PHÍ', 'sum'))
                    .reset_index()
                )
                fig_trend = px.line(
                    trend, x='THÁNG', y='so_ca', color='NĂM',
                    markers=True, title="Số ca theo tháng"
                )
                st.plotly_chart(fig_trend, use_container_width=True)

                # ---------- RISK SCORING ----------
                st.divider()
                st.subheader("⚠️ Bảng xếp hạng rủi ro thiết bị (Risk Scoring)")
                today = df_view['confirmed_dt'].max()

                risk_df = (
                    df_view.groupby('machine_id')
                    .agg(
                        so_ca=('id', 'count'),
                        tong_chi_phi=('CHI_PHÍ', 'sum'),
                        last_case=('confirmed_dt', 'max'),
                        branch=('branch', 'first')
                    )
                    .reset_index()
                )

                if not risk_df.empty:
                    risk_df['freq_score'] = risk_df['so_ca'] / risk_df['so_ca'].max()
                    risk_df['cost_score'] = risk_df['tong_chi_phi'] / risk_df['tong_chi_phi'].max()
                    risk_df['recent_score'] = ((today - risk_df['last_case']).dt.days <= 30).astype(int)
                    risk_df['risk_score'] = (0.5 * risk_df['freq_score'] + 0.4 * risk_df['cost_score'] + 0.1 * risk_df['recent_score']).round(2)

                    def risk_label(v):
                        if v >= 0.75: return "🔴 Cao"
                        elif v >= 0.5: return "🟠 Trung bình"
                        return "🟢 Thấp"

                    risk_df['mức_rủi_ro'] = risk_df['risk_score'].apply(risk_label)
                    st.dataframe(
                        risk_df.sort_values('risk_score', ascending=False)[
                            ['machine_id', 'branch', 'so_ca', 'tong_chi_phi', 'risk_score', 'mức_rủi_ro']
                        ], use_container_width=True
                    )

                    heat = risk_df.groupby('branch')['risk_score'].mean().reset_index()
                    fig_heat = px.bar(heat, x='branch', y='risk_score', title="🔥 Mức rủi ro trung bình theo Chi nhánh")
                    st.plotly_chart(fig_heat, use_container_width=True)

                # ---------- DRILL DOWN ----------
                st.divider()
                st.subheader("🔍 Drill-down chi tiết theo thiết bị")
                sel_machine = st.selectbox("Chọn máy để xem lịch sử", sorted(df_view['machine_id'].unique()))
                df_machine = df_view[df_view['machine_id'] == sel_machine]
                st.dataframe(df_machine.sort_values('confirmed_dt', ascending=False), use_container_width=True)
            else:
                st.warning("Không có dữ liệu phù hợp với bộ lọc.")

    # --- TAB 2: QUẢN TRỊ HỆ THỐNG ---
    with tab_admin:
        st.title("📥 Quản Trị & Điều Hành Chi Nhánh")

        # Khởi tạo các Sub-tabs bên trong Tab Quản trị
        ad_sub1, ad_sub2, ad_sub3 = st.tabs([
            "➕ NHẬP LIỆU", 
            "🏢 CHI NHÁNH", 
            "📜 AUDIT LOG"
        ])

        # ---------------------------------------------------------
        # SUB-TAB 1: NHẬP LIỆU
        # ---------------------------------------------------------
        with ad_sub1:
            c_up, c_man = st.columns([5, 5])

            # ---------- PHẦN A: CSV IMPORT ----------
            with c_up:
                st.subheader("📂 Import CSV (Enterprise)")

                expected_cols = {
                    "machine_id", "branch", "customer_name", 
                    "confirmed_date", "issue_reason", "compensation"
                }

                up_file = st.file_uploader(
                    "Chọn file CSV", 
                    type="csv", 
                    key="csv_admin_enterprise"
                )

                if up_file:
                    try:
                        df_up = pd.read_csv(up_file)
                        st.markdown("### 🔍 Kiểm tra cấu trúc dữ liệu")

                        missing_cols = expected_cols - set(df_up.columns)
                        extra_cols = set(df_up.columns) - expected_cols

                        if missing_cols:
                            st.error(f"❌ Thiếu cột bắt buộc: {', '.join(missing_cols)}")
                        else:
                            st.success("✅ Cấu trúc hợp lệ")
                            if extra_cols:
                                st.warning(f"⚠️ Cột dư sẽ bỏ qua: {', '.join(extra_cols)}")

                            st.markdown("### 👀 Xem trước dữ liệu (5 dòng)")
                            st.dataframe(df_up.head(5), use_container_width=True)

                            if st.button(f"🚀 Xác nhận import {len(df_up)} dòng", use_container_width=True, type="primary"):
                                records = []
                                audits = []
                                
                                for _, r in df_up.iterrows():
                                    # Chuẩn bị dữ liệu để insert vào repair_cases
                                    record = {
                                        "machine_id": str(r["machine_id"]).strip().upper(),
                                        "branch": r["branch"],
                                        "customer_name": r["customer_name"],
                                        "confirmed_date": pd.to_datetime(r["confirmed_date"]).isoformat(),
                                        "issue_reason": r["issue_reason"],
                                        "compensation": float(r["compensation"]),
                                        "received_date": datetime.now().isoformat(),
                                        "note": "",
                                        "is_unrepairable": False,
                                        "source": "csv",
                                        "created_by": "admin@system"
                                    }
                                    records.append(record)

                                    # Chuẩn bị dữ liệu log cho audit_logs
                                    audits.append({
                                        "action": "IMPORT_CSV",
                                        "table_name": "repair_cases",
                                        "actor": "admin@system",
                                        "source": "csv",
                                        "payload": str(record), # Convert dict sang string để lưu
                                        "created_at": datetime.now().isoformat()
                                    })

                                try:
                                    supabase.table("repair_cases").insert(records).execute()
                                    supabase.table("audit_logs").insert(audits).execute()
                                    st.success("✅ Import & Audit thành công")
                                    st.cache_data.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Lỗi import: {e}")

                    except Exception as e:
                        st.error(f"❌ Không đọc được CSV: {e}")

            # ---------- PHẦN B: MANUAL ENTRY ----------
            with c_man:
                st.subheader("✍️ Nhập ca sửa chữa đơn lẻ")

                with st.form("f_manual_enterprise", clear_on_submit=True):
                    m1, m2 = st.columns(2)
                    with m1:
                        f_machine = st.text_input("Mã máy *")
                        f_branch = st.selectbox("Chi nhánh *", ["Miền Bắc", "Miền Trung", "Miền Nam"])
                        f_cost = st.number_input("Chi phí", min_value=0, step=10000)
                    with m2:
                        f_customer = st.text_input("Khách hàng *")
                        f_confirmed = st.date_input("Ngày xác nhận", value=datetime.now())
                        f_reason = st.text_input("Nguyên nhân *")

                    f_note = st.text_area("Ghi chú")

                    if st.form_submit_button("💾 Lưu dữ liệu", use_container_width=True):
                        if not f_machine or not f_customer or not f_reason:
                            st.warning("⚠️ Vui lòng nhập đầy đủ các trường bắt buộc")
                        else:
                            record = {
                                "machine_id": f_machine.strip().upper(),
                                "branch": f_branch,
                                "customer_name": f_customer.strip(),
                                "confirmed_date": f_confirmed.isoformat(),
                                "received_date": datetime.now().isoformat(),
                                "issue_reason": f_reason.strip(),
                                "note": f_note.strip(),
                                "compensation": float(f_cost),
                                "is_unrepairable": False,
                                "source": "manual",
                                "created_by": "admin@system"
                            }
                            
                            audit = {
                                "action": "INSERT",
                                "table_name": "repair_cases",
                                "actor": "admin@system",
                                "source": "manual",
                                "payload": str(record),
                                "created_at": datetime.now().isoformat()
                            }

                            try:
                                supabase.table("repair_cases").insert(record).execute()
                                supabase.table("audit_logs").insert(audit).execute()
                                st.success("✅ Lưu & audit thành công")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Lỗi DB: {e}")

        # ---------------------------------------------------------
        # SUB-TAB 2: CHI NHÁNH
        # ---------------------------------------------------------
        with ad_sub2:
            st.subheader("🏢 Theo dõi vận hành theo chi nhánh")
            sel_b = st.selectbox("Chọn chi nhánh", ["Miền Bắc", "Miền Trung", "Miền Nam"])

            if not df_db.empty:
                df_b = df_db[df_db["branch"] == sel_b]
                if not df_b.empty:
                    view = (
                        df_b.groupby("machine_id")
                        .agg(so_ca=("id", "count"), tong_chi_phi=("compensation", "sum"))
                        .reset_index()
                        .sort_values("so_ca", ascending=False)
                    )
                    st.dataframe(view, use_container_width=True)
                else:
                    st.info("Không có dữ liệu chi nhánh này")

        # ---------------------------------------------------------
        # SUB-TAB 3: AUDIT LOG
        # ---------------------------------------------------------
        with ad_sub3:
            st.subheader("📜 Nhật ký Audit hệ thống")
            
            # Nút làm mới tay để tránh việc cache làm mất log mới
            if st.button("🔄 Làm mới Nhật ký"):
                st.rerun()

            try:
                # Thực hiện truy vấn trực tiếp vào bảng audit_logs
                res_audit = supabase.table("audit_logs").select("*").order("created_at", desc=True).limit(100).execute()
                
                if res_audit.data:
                    df_audit = pd.DataFrame(res_audit.data)
                    
                    # Định dạng lại cột thời gian cho dễ nhìn
                    if 'created_at' in df_audit.columns:
                        df_audit['created_at'] = pd.to_datetime(df_audit['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Hiển thị bảng log
                    st.dataframe(
                        df_audit, 
                        use_container_width=True,
                        column_config={
                            "payload": st.column_config.TextColumn("Dữ liệu chi tiết", width="medium"),
                            "action": st.column_config.TextColumn("Hành động"),
                            "created_at": st.column_config.TextColumn("Thời gian")
                        }
                    )
                else:
                    st.info("ℹ️ Hiện tại chưa có bản ghi nhật ký nào trong bảng 'audit_logs'.")
                    st.caption("Gợi ý: Hãy thử thực hiện một lệnh Nhập liệu để tạo log.")
                    
            except Exception as e:
                st.error("❌ Không thể kết nối với bảng 'audit_logs'")
                with st.expander("Chi tiết lỗi kỹ thuật"):
                    st.code(e)
                st.warning("Mẹo: Đảm bảo bạn đã tạo bảng 'audit_logs' trong Supabase SQL Editor với các cột: id, action, table_name, actor, payload, created_at.")

    with tab_alert:
        st.title("🚨 Trung Tâm Cảnh Báo Vận Hành")
        st.caption("Phát hiện sớm rủi ro – Giảm chi phí – Hành động kịp thời")

        if df_db.empty or len(df_db) < 3: # Giảm ngưỡng để dễ test dữ liệu
            st.info("📭 Chưa đủ dữ liệu để kích hoạt hệ thống cảnh báo.")
        else:
            # Chuẩn bị dữ liệu thời gian
            today = pd.Timestamp.now()
            df_db['week'] = df_db['confirmed_dt'].dt.isocalendar().week
            df_db['year'] = df_db['confirmed_dt'].dt.year

            # Tách dữ liệu tuần này và tuần trước
            this_week = df_db[df_db['week'] == today.isocalendar().week]
            last_week = df_db[df_db['week'] == today.isocalendar().week - 1]

            # 1️⃣ KPI TỔNG QUAN
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🚨 Tổng ca sửa chữa", f"{len(df_db)} ca")
            
            curr_cost = this_week['compensation'].sum()
            prev_cost = last_week['compensation'].sum()
            c2.metric(
                "💰 Chi phí tuần này", 
                f"{curr_cost:,.0f} đ",
                delta=f"{curr_cost - prev_cost:,.0f} đ" if not last_week.empty else None,
                delta_color="inverse" # Đỏ nếu tăng chi phí
            )

            c3.metric(
                "🛠️ Số ca tuần này", 
                len(this_week),
                delta=len(this_week) - len(last_week) if not last_week.empty else None,
                delta_color="inverse"
            )

            risk_branch = this_week['branch'].value_counts().idxmax() if not this_week.empty else "N/A"
            c4.metric("🏢 Nhánh rủi ro nhất", risk_branch)

            st.divider()

            # 2️⃣ CẢNH BÁO CHI PHÍ THEO CHI NHÁNH
            st.subheader("💰 Cảnh báo vượt ngưỡng chi phí")
            branch_cost = df_db.groupby('branch').agg(
                total_cost=('compensation', 'sum'),
                avg_cost=('compensation', 'mean'),
                cases=('id', 'count')
            ).reset_index()

            # Ngưỡng: Tổng chi phí > (Trung bình chi phí mỗi nhánh * 1.5)
            avg_all_branches = branch_cost['total_cost'].mean()
            branch_cost['threshold'] = avg_all_branches * 1.2 
            branch_cost['status'] = branch_cost['total_cost'] > branch_cost['threshold']

            high_cost_branch = branch_cost[branch_cost['status']]

            if not high_cost_branch.empty:
                st.error("⚠️ Phát hiện chi nhánh có tổng chi phí bất thường")
                st.dataframe(high_cost_branch, use_container_width=True)
            else:
                st.success("✅ Chi phí các chi nhánh đang trong tầm kiểm soát")

            st.divider()

            # 3️⃣ CẢNH BÁO MÁY SỬA QUÁ NHIỀU
            st.subheader("🛠️ Thiết bị có tần suất sửa bất thường")
            machine_stats = df_db.groupby(['machine_id', 'branch']).agg(
                total_cases=('id', 'count'),
                total_cost=('compensation', 'sum')
            ).reset_index()

            # Ngưỡng sửa > trung bình + 1 (áp dụng cho tập dữ liệu nhỏ)
            case_threshold = machine_stats['total_cases'].mean() + 1
            risky_machines = machine_stats[machine_stats['total_cases'] > case_threshold]

            if not risky_machines.empty:
                st.warning(f"⚠️ Phát hiện {len(risky_machines)} thiết bị sửa hơn {case_threshold:.1f} lần")
                st.dataframe(risky_machines.sort_values('total_cases', ascending=False), use_container_width=True)
            else:
                st.success("✅ Không có máy nào hỏng quá thường xuyên")

            st.divider()

            # 4️⃣ SO SÁNH XU HƯỚNG
            st.subheader("📈 Xu hướng vận hành (Tuần này vs Tuần trước)")
            trend_data = pd.DataFrame({
                "Chỉ số": ["Số lượng ca", "Tổng chi phí"],
                "Tuần trước": [len(last_week), prev_cost],
                "Tuần này": [len(this_week), curr_cost]
            })
            st.table(trend_data) # Dùng table để hiển thị tĩnh cho rõ ràng

            # 5️⃣ ĐIỂM RỦI RO (RISK SCORE)
            st.subheader("🎯 Top 5 đối tượng cần kiểm tra ngay")
            priority = machine_stats.copy()
            # Tính toán risk score từ 0-1
            max_cases = priority['total_cases'].max() if not priority.empty else 1
            max_cost = priority['total_cost'].max() if not priority.empty else 1
            
            priority['risk_score'] = (
                0.6 * (priority['total_cases'] / max_cases) + 
                0.4 * (priority['total_cost'] / max_cost)
            ).round(2)

            top_risk = priority.sort_values('risk_score', ascending=False).head(5)
            st.dataframe(top_risk, use_container_width=True)
    # TAB 5: 🎯 PERFORMANCE MANAGEMENT (KPI / SLA)
    # ======================================================
    with tab_kpi:
        st.title("🎯 Performance Management – KPI Dashboard")
        st.caption("Đánh giá hiệu suất – So sánh – Cảnh báo vượt ngưỡng")

        if df_db.empty:
            st.warning("⚠️ Chưa có dữ liệu để tính toán KPI")
        else:
            # 1️⃣ KPI TỔNG QUAN
            st.subheader("📌 KPI Tổng Quan Hệ Thống")
            k1, k2, k3, k4 = st.columns(4)

            total_cases = len(df_db)
            avg_cost_val = df_db['compensation'].mean()
            repeat_rate = (df_db.groupby('machine_id').size().gt(1).sum() / df_db['machine_id'].nunique()) * 100

            k1.metric("🛠️ Tổng số ca", total_cases)
            k2.metric("💰 Chi phí TB / ca", f"{avg_cost_val:,.0f} đ")
            k3.metric("♻️ Tỷ lệ máy lặp lỗi", f"{repeat_rate:.1f}%")
            k4.metric("🏢 Số chi nhánh", df_db['branch'].nunique())

            st.divider()

            # 2️⃣ KPI THEO CHI NHÁNH
            st.subheader("🏢 KPI Theo Chi Nhánh")
            branch_kpi = df_db.groupby('branch').agg(
                total_cases=('id', 'count'),
                total_cost=('compensation', 'sum'),
                avg_cost=('compensation', 'mean'),
                unique_machines=('machine_id', 'nunique')
            ).reset_index()

            branch_kpi['cost_per_machine'] = (branch_kpi['total_cost'] / branch_kpi['unique_machines']).round(0)
            st.dataframe(branch_kpi, use_container_width=True)

            fig_branch = px.bar(branch_kpi, x='branch', y='avg_cost', 
                                title="Chi phí trung bình / ca theo chi nhánh",
                                color='avg_cost', color_continuous_scale='Reds')
            st.plotly_chart(fig_branch, use_container_width=True)

            st.divider()

            # 3️⃣ KPI MÁY – TOP RỦI RO
            st.subheader("🧰 KPI Thiết Bị (Top rủi ro)")
            machine_kpi = df_db.groupby(['machine_id', 'branch']).agg(
                cases=('id', 'count'),
                cost=('compensation', 'sum')
            ).reset_index()

            # Tính toán điểm rủi ro
            machine_kpi['risk_score'] = (
                0.6 * (machine_kpi['cases'] / machine_kpi['cases'].max()) +
                0.4 * (machine_kpi['cost'] / machine_kpi['cost'].max())
            ).round(2)

            st.dataframe(
                machine_kpi.sort_values('risk_score', ascending=False).head(10),
                use_container_width=True
            )

            st.divider()

            # 4️⃣ KPI XU HƯỚNG
            st.subheader("📈 Xu Hướng Hiệu Suất")
            trend = df_db.groupby(['NĂM', 'THÁNG']).agg(
                cases=('id', 'count'),
                cost=('compensation', 'sum')
            ).reset_index()
            trend['period'] = trend['THÁNG'].astype(str) + "/" + trend['NĂM'].astype(str)

            fig_trend = px.line(trend, x='period', y='cost', markers=True, title="Xu hướng tổng chi phí theo tháng")
            st.plotly_chart(fig_trend, use_container_width=True)

            st.divider()

            # 5️⃣ KPI CẢNH BÁO SLA
            st.subheader("🚨 Cảnh Báo KPI Vượt Ngưỡng")
            SLA_COST = st.number_input("Ngưỡng chi phí trung bình tối đa cho phép / ca (đ)", 
                                      min_value=0, value=2000000, step=100000)

            breach = branch_kpi[branch_kpi['avg_cost'] > SLA_COST]

            if not breach.empty:
                st.error(f"⚠️ Phát hiện {len(breach)} chi nhánh vượt ngưỡng chi phí cam kết (SLA)")
                st.dataframe(breach[['branch', 'avg_cost', 'total_cases']], use_container_width=True)
            else:
                st.success("✅ Tất cả chi nhánh nằm trong ngưỡng kiểm soát chi phí")
    # --- TAB 3: AI INSIGHTS ---
    with tab_ai:
        st.title("🧠 AI Decision Intelligence")
        st.caption("Phân tích – Giải thích – Khuyến nghị – Dự báo vận hành")

        if df_db.empty or len(df_db) < 10:
            st.warning("⚠️ Chưa đủ dữ liệu để AI phân tích (tối thiểu 10 ca).")
        else:
            ai_risk, ai_root, ai_action, ai_forecast = st.tabs([
                "🚨 RỦI RO", "🔍 NGUYÊN NHÂN GỐC", "🧩 KHUYẾN NGHỊ", "📈 DỰ BÁO"
            ])

            # 1. AI Phân tích rủi ro
            with ai_risk:
                st.subheader("🚨 Phát hiện rủi ro vận hành")
                risk_branch = df_db.groupby('branch').agg(
                    total_cases=('id', 'count'),
                    total_cost=('compensation', 'sum'),
                    avg_cost=('compensation', 'mean')
                ).reset_index()

                cost_mean = risk_branch['avg_cost'].mean()
                cost_std = risk_branch['avg_cost'].std()
                risk_branch['risk_level'] = risk_branch['avg_cost'].apply(
                    lambda x: "CAO" if x > cost_mean + cost_std else "BÌNH THƯỜNG"
                )
                
                high_risk = risk_branch[risk_branch['risk_level'] == "CAO"]
                if not high_risk.empty:
                    st.error("⚠️ Phát hiện chi nhánh có rủi ro chi phí cao")
                    st.dataframe(high_risk, use_container_width=True)
                else:
                    st.success("✅ Không phát hiện rủi ro nghiêm trọng")

            # 2. AI Nguyên nhân gốc
            with ai_root:
                st.subheader("🔍 Phân tích nguyên nhân gốc (Root Cause)")
                machine_stats = df_db.groupby(['machine_id', 'branch']).agg(
                    total_cases=('id', 'count'),
                    total_cost=('compensation', 'sum'),
                    avg_cost=('compensation', 'mean')
                ).reset_index()

                machine_stats['freq_score'] = machine_stats['total_cases'] / machine_stats['total_cases'].max()
                machine_stats['cost_score'] = machine_stats['total_cost'] / machine_stats['total_cost'].max()
                machine_stats['risk_score'] = (0.6 * machine_stats['freq_score'] + 0.4 * machine_stats['cost_score']).round(2)

                def explain_root(row):
                    if row['freq_score'] > 0.7 and row['cost_score'] > 0.7: return "Thiết bị lỗi lặp lại + chi phí cao"
                    if row['freq_score'] > 0.7: return "Thiết bị lỗi lặp lại nhiều lần"
                    if row['cost_score'] > 0.7: return "Chi phí sửa chữa cao bất thường"
                    return "Bình thường"

                machine_stats['root_cause'] = machine_stats.apply(explain_root, axis=1)
                st.dataframe(machine_stats.sort_values('risk_score', ascending=False)[['machine_id', 'branch', 'risk_score', 'root_cause']], use_container_width=True)

            # 3. AI Khuyến nghị
            with ai_action:
                st.subheader("🧩 Khuyến nghị hành động cho quản lý")
                recommendations = []
                for _, r in machine_stats.iterrows():
                    if r['risk_score'] >= 0.75:
                        recommendations.append({"machine_id": r['machine_id'], "branch": r['branch'], "recommendation": "Thay thế thiết bị mới", "impact": "Giảm chi phí dài hạn"})
                    elif r['risk_score'] >= 0.55:
                        recommendations.append({"machine_id": r['machine_id'], "branch": r['branch'], "recommendation": "Bảo trì định kỳ khẩn cấp", "impact": "Giảm gián đoạn"})
                
                if recommendations:
                    st.dataframe(pd.DataFrame(recommendations), use_container_width=True)
                else:
                    st.success("✅ Hệ thống đang vận hành ổn định.")

            # 4. AI Dự báo
            with ai_forecast:
                st.subheader("📈 Dự báo chi phí tháng tiếp theo")
                forecast_results = []
                for b in df_db['branch'].unique():
                    df_b = df_db[df_db['branch'] == b]
                    monthly = df_b.groupby(['NĂM', 'THÁNG'])['compensation'].sum()
                    if len(monthly) >= 2:
                        # Dự báo đơn giản dựa trên trung bình trượt
                        forecast_value = monthly.mean()
                        forecast_results.append({"branch": b, "val": forecast_value})
                
                if forecast_results:
                    cols = st.columns(len(forecast_results))
                    for i, r in enumerate(forecast_results):
                        cols[i].metric(r['branch'], f"{r['val']:,.0f} đ")
                else:
                    st.info("Chưa đủ dữ liệu lịch sử (Tháng/Năm) để dự báo.")



if __name__ == "__main__":
    main()
