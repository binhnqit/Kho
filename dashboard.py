import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from supabase import create_client

# ================== CONFIG ==================
st.set_page_config(
    page_title="4ORANGES - REPAIR OPS",
    layout="wide",
    page_icon="🎨"
)

ORANGE_COLORS = ["#FF8C00", "#FFA500", "#FF4500", "#E67E22", "#D35400"]

SUPABASE_URL = "https://cigbnbaanpebwrufzxfg.supabase.co"
SUPABASE_KEY = st.secrets.get(
    "SUPABASE_KEY",
    "sb_publishable_NQzqwJ4YhKC4sQGLxyLAyw_mwRFhkRf"
)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================== DATA ==================
@st.cache_data(ttl=120)
def fetch_repair_cases():
    res = supabase.table("repair_cases") \
        .select("id, machine_id, branch, confirmed_date, issue_reason, customer_name") \
        .order("confirmed_date", desc=True) \
        .limit(2000) \
        .execute()
    return res.data or []

def load_data_from_db():
    df = pd.DataFrame(fetch_repair_cases())
    if df.empty:
        return df

    df["confirmed_date"] = pd.to_datetime(df["confirmed_date"], errors="coerce")
    df = df.dropna(subset=["confirmed_date"])

    df["NĂM"] = df["confirmed_date"].dt.year
    df["THÁNG"] = df["confirmed_date"].dt.month
    df["NGÀY_HIỂN_THỊ"] = df["confirmed_date"].dt.strftime("%d/%m/%Y")

    df.rename(columns={"branch": "VÙNG"}, inplace=True)
    df["CHI_PHÍ_THỰC"] = 0

    return df

# ================== CSV CLEAN ==================
def clean_excel_data(df):
    mapping = {
        "Ngày Xác nhận": ["Ngay Xac nhan", "Ngày xác nhận"],
        "Tên KH": ["Ten KH"],
        "Lý Do": ["Ly Do"],
        "Chi Nhánh": ["Chi nhanh"],
        "Mã số máy": ["Ma so may"]
    }

    for std, aliases in mapping.items():
        for a in aliases:
            if a in df.columns:
                df.rename(columns={a: std}, inplace=True)

    df["Ngày Xác nhận"] = df["Ngày Xác nhận"].astype(str).replace(["", "nan"], pd.NA).ffill()
    return df

# ================== IMPORT ==================
def import_to_enterprise_schema(df_chunk):
    ok = 0
    for _, r in df_chunk.iterrows():
        try:
            code = str(r["Mã số máy"]).strip()
            if not code:
                continue

            m = supabase.table("machines").upsert(
                {"machine_code": code, "region": r["Chi Nhánh"]},
                on_conflict="machine_code"
            ).execute().data[0]

            date = pd.to_datetime(r["Ngày Xác nhận"], dayfirst=True, errors="coerce")
            date = date.strftime("%Y-%m-%d") if pd.notna(date) else None

            supabase.table("repair_cases").insert({
                "machine_id": m["id"],
                "branch": r["Chi Nhánh"],
                "customer_name": r["Tên KH"],
                "issue_reason": r["Lý Do"],
                "confirmed_date": date
            }).execute()

            ok += 1
        except:
            continue
    return ok

# ================== APP ==================
def main():
    df_db = load_data_from_db()

    # -------- SIDEBAR --------
    with st.sidebar:
        st.title("🎨 4ORANGES OPS")

        if st.button("🔄 REFRESH DATABASE"):
            st.cache_data.clear()
            st.rerun()

        if not df_db.empty:
            year = st.selectbox("📅 Năm", sorted(df_db["NĂM"].unique(), reverse=True))
            month = st.selectbox(
                "📆 Tháng",
                ["Tất cả"] + sorted(df_db[df_db["NĂM"] == year]["THÁNG"].unique().tolist())
            )
        else:
            year, month = datetime.datetime.now().year, "Tất cả"

    tabs = st.tabs(["📊 XU HƯỚNG", "📥 NHẬP DỮ LIỆU"])

    # -------- DASHBOARD --------
    with tabs[0]:
        if df_db.empty:
            st.info("Chưa có dữ liệu")
            return

        df = df_db[df_db["NĂM"] == year]
        if month != "Tất cả":
            df = df[df["THÁNG"] == month]

        k1, k2, k3 = st.columns(3)
        k1.metric("💰 TỔNG CHI PHÍ", f"{df['CHI_PHÍ_THỰC'].sum():,.0f} đ")
        k2.metric("📋 SỰ VỤ", len(df))
        k3.metric("📈 TB/CA", f"{df['CHI_PHÍ_THỰC'].mean():,.0f} đ")

        st.dataframe(
            df.sort_values("confirmed_date", ascending=False)[
                ["machine_id", "customer_name", "VÙNG", "NGÀY_HIỂN_THỊ"]
            ].rename(columns={
                "machine_id": "MÃ MÁY",
                "customer_name": "KHÁCH HÀNG"
            }),
            use_container_width=True
        )

    # -------- IMPORT --------
    with tabs[1]:
        file = st.file_uploader("Upload CSV", type="csv")
        if file:
            df = clean_excel_data(pd.read_csv(file, encoding="utf-8-sig"))
            st.dataframe(df.head())

            if st.button("🚀 IMPORT"):
                count = import_to_enterprise_schema(df)
                st.success(f"✅ Đã nhập {count} dòng")
                st.cache_data.clear()
                st.balloons()

if __name__ == "__main__":
    main()
