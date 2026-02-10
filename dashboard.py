import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from datetime import datetime

# =====================================================
# 1. KẾT NỐI SUPABASE
# =====================================================
url = "https://cigbnbaanpebwrufzxfg.supabase.co"
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# =====================================================
# 2. LOAD DATA
# =====================================================
@st.cache_data(ttl=30)
def load_repair_data_final():
    try:
        res = supabase.table("repair_cases").select("*").order("created_at", desc=True).execute()
        if not res.data:
            return pd.DataFrame()

        df = pd.DataFrame(res.data)

        df["confirmed_dt"] = pd.to_datetime(df["confirmed_date"], errors="coerce")
        df["created_dt"] = pd.to_datetime(df["created_at"], errors="coerce")
        df = df.dropna(subset=["confirmed_dt"])

        df["NĂM"] = df["confirmed_dt"].dt.year
        df["THÁNG"] = df["confirmed_dt"].dt.month

        day_map = {
            "Monday": "Thứ 2",
            "Tuesday": "Thứ 3",
            "Wednesday": "Thứ 4",
            "Thursday": "Thứ 5",
            "Friday": "Thứ 6",
            "Saturday": "Thứ 7",
            "Sunday": "Chủ Nhật",
        }
        df["THỨ"] = df["confirmed_dt"].dt.day_name().map(day_map)

        df["CHI_PHÍ"] = pd.to_numeric(df["compensation"], errors="coerce").fillna(0)

        return df.sort_values("created_dt", ascending=False)

    except Exception as e:
        st.error(f"Lỗi load dữ liệu: {e}")
        return pd.DataFrame()


def write_audit_log(action, table_name, record_id=None, new_data=None):
    try:
        audit = {
            "user_role": st.session_state.get("user_role", "admin"),
            "action": action,
            "table_name": table_name,
            "record_id": str(record_id) if record_id else None,
            "new_data": new_data,
            "created_at": datetime.now().isoformat(),
        }
        supabase.table("audit_logs").insert(audit).execute()
    except Exception as e:
        st.warning(f"Không ghi được audit log: {e}")


# =====================================================
# 3. MAIN APP
# =====================================================
def main():
    st.set_page_config(
        page_title="4ORANGES OPS 2026",
        layout="wide",
        page_icon="🎨",
    )

    df_db = load_repair_data_final()

    tab_dash, tab_admin, tab_ai, tab_alert, tab_kpi = st.tabs(
        [
            "📊 BÁO CÁO VẬN HÀNH",
            "📥 QUẢN TRỊ HỆ THỐNG",
            "🧠 AI INSIGHTS",
            "🚨 CẢNH BÁO",
            "🎯 KPI QUẢN TRỊ",
        ]
    )

    # =====================================================
    # TAB ADMIN
    # =====================================================
    with tab_admin:
        st.title("📥 Quản Trị Hệ Thống – Enterprise")

        ad_sub1, ad_sub2, ad_sub3 = st.tabs(
            ["➕ NHẬP LIỆU", "🏢 CHI NHÁNH", "📜 AUDIT LOG"]
        )

        # -------------------------------------------------
        # SUB TAB 1: NHẬP LIỆU
        # -------------------------------------------------
        with ad_sub1:
            c_up, c_man = st.columns([5, 5])

            # CSV IMPORT
            with c_up:
                st.subheader("📂 Import CSV")

                expected_cols = {
                    "machine_id",
                    "branch",
                    "customer_name",
                    "confirmed_date",
                    "issue_reason",
                    "compensation",
                }

                up_file = st.file_uploader("Chọn file CSV", type="csv")

                if up_file:
                    df_up = pd.read_csv(up_file)
                    missing = expected_cols - set(df_up.columns)

                    if missing:
                        st.error(f"Thiếu cột: {', '.join(missing)}")
                    else:
                        st.success("Cấu trúc file hợp lệ")
                        st.dataframe(df_up.head(), use_container_width=True)

                        if st.button("🚀 Import dữ liệu", type="primary"):
                            for _, r in df_up.iterrows():
                                record = {
                                    "machine_id": str(r["machine_id"]).strip(),
                                    "branch": r["branch"],
                                    "customer_name": r["customer_name"],
                                    "confirmed_date": pd.to_datetime(
                                        r["confirmed_date"]
                                    ).date().isoformat(),
                                    "issue_reason": r["issue_reason"],
                                    "compensation": float(r["compensation"]),
                                    "received_date": datetime.now().date().isoformat(),
                                    "is_unrepairable": False,
                                }
                                res = supabase.table("repair_cases").insert(record).execute()
                                if res.data:
                                    write_audit_log(
                                        "IMPORT_CSV",
                                        "repair_cases",
                                        res.data[0]["id"],
                                        record,
                                    )

                            st.success("Import thành công")
                            st.cache_data.clear()
                            st.rerun()

            # MANUAL INPUT
            with c_man:
                st.subheader("✍️ Nhập thủ công")

                with st.form("manual_form", clear_on_submit=True):
                    m1, m2 = st.columns(2)

                    with m1:
                        f_machine = st.text_input("Mã máy *")
                        f_branch = st.selectbox(
                            "Chi nhánh", ["Miền Bắc", "Miền Trung", "Miền Nam"]
                        )
                        f_cost = st.number_input(
                            "Chi phí", min_value=0, step=10000
                        )

                    with m2:
                        f_customer = st.text_input("Khách hàng *")
                        f_confirmed = st.date_input(
                            "Ngày xác nhận", value=datetime.now()
                        )
                        f_reason = st.text_input("Nguyên nhân *")

                    f_note = st.text_area("Ghi chú")

                    if st.form_submit_button("💾 Lưu dữ liệu"):
                        if not f_machine or not f_customer or not f_reason:
                            st.warning("Thiếu thông tin bắt buộc")
                        else:
                            record = {
                                "machine_id": f_machine.upper(),
                                "branch": f_branch,
                                "customer_name": f_customer,
                                "confirmed_date": f_confirmed.isoformat(),
                                "issue_reason": f_reason,
                                "note": f_note,
                                "received_date": datetime.now().date().isoformat(),
                                "compensation": float(f_cost),
                                "is_unrepairable": False,
                            }

                            res = supabase.table("repair_cases").insert(record).execute()
                            if res.data:
                                write_audit_log(
                                    "INSERT_MANUAL",
                                    "repair_cases",
                                    res.data[0]["id"],
                                    record,
                                )
                                st.success("Lưu thành công")
                                st.cache_data.clear()
                                st.rerun()

        # -------------------------------------------------
        # SUB TAB 2: CHI NHÁNH
        # -------------------------------------------------
        with ad_sub2:
            st.subheader("🏢 Theo dõi chi nhánh")

            sel_b = st.selectbox(
                "Chọn chi nhánh",
                ["Miền Bắc", "Miền Trung", "Miền Nam"],
            )

            if not df_db.empty:
                df_b = df_db[df_db["branch"] == sel_b]
                st.dataframe(
                    df_b.groupby("machine_id")
                    .agg(
                        so_ca=("id", "count"),
                        tong_chi_phi=("CHI_PHÍ", "sum"),
                    )
                    .reset_index()
                    .sort_values("so_ca", ascending=False),
                    use_container_width=True,
                )

        # -------------------------------------------------
        # SUB TAB 3: AUDIT LOG
        # -------------------------------------------------
        with ad_sub3:
            st.subheader("📜 Audit Logs")

            res = (
                supabase.table("audit_logs")
                .select("*")
                .order("created_at", desc=True)
                .limit(100)
                .execute()
            )

            if res.data:
                st.dataframe(pd.DataFrame(res.data), use_container_width=True)
            else:
                st.info("Chưa có audit log")


if __name__ == "__main__":
    main()
