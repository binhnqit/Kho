import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from supabase import create_client

# --- 1. CẤU HÌNH & KẾT NỐI ---
st.set_page_config(page_title="4ORANGES - REPAIR OPS", layout="wide", page_icon="🎨")
ORANGE_COLORS = ["#FF8C00", "#FFA500", "#FF4500", "#E67E22", "#D35400"]

# Thông tin kết nối
SUPABASE_URL = "https://cigbnbaanpebwrufzxfg.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_NQzqwJ4YhKC4sQGLxyLAyw_mwRFhkRf")

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Lỗi kết nối Supabase: {e}")

# --- 2. HÀM LOAD DỮ LIỆU (PHÒNG THỦ TẦNG TẦNG LỚP LỚP) ---
@st.cache_data(ttl=60)
def load_data_from_db():
    try:
        # Lấy dữ liệu JOIN từ 3 bảng chính
        res = supabase.table("repair_cases").select(
            "*, machines(machine_code, region), repair_costs(estimated_cost, actual_cost, confirmed_by)"
        ).execute()
        
        if not res.data:
            return pd.DataFrame()
            
        df = pd.json_normalize(res.data)
        
        # Mapping cột để thống nhất logic hiển thị
        mapping = {
            "machines.machine_code": "MÃ_MÁY",
            "repair_costs.actual_cost": "CHI_PHÍ_THỰC",
            "repair_costs.estimated_cost": "CHI_PHÍ_DỰ_KIẾN",
            "branch": "VÙNG"
        }
        df = df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})

        # BIỆN PHÁP MẠNH: Tự tạo cột nếu thiếu để tránh lỗi KeyError
        REQUIRED = ['CHI_PHÍ_THỰC', 'CHI_PHÍ_DỰ_KIẾN', 'MÃ_MÁY', 'VÙNG', 'confirmed_date', 'customer_name', 'issue_reason', 'is_unrepairable']
        for col in REQUIRED:
            if col not in df.columns:
                df[col] = 0 if 'CHI_PHÍ' in col or 'is_unrepairable' in col else "N/A"

        # Xử lý ngày tháng chuyên sâu (Dứt điểm lỗi 00:00:00)
        if 'confirmed_date' in df.columns:
            df['confirmed_date'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
            df = df.dropna(subset=['confirmed_date'])
            df['NĂM'] = df['confirmed_date'].dt.year.astype(int)
            df['THÁNG'] = df['confirmed_date'].dt.month.astype(int)
            df['NGÀY_HIỂN_THỊ'] = df['confirmed_date'].dt.strftime('%d/%m/%Y')

        # Ép kiểu số cho tiền bạc
        df['CHI_PHÍ_THỰC'] = pd.to_numeric(df['CHI_PHÍ_THỰC'], errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Lỗi Load Data: {e}")
        return pd.DataFrame()

# --- 3. HÀM IMPORT DỮ LIỆU (ALL-IN-ONE) ---
def import_to_enterprise_schema(df):
    success_count = 0
    progress_bar = st.progress(0)
    
    def clean_price(val):
        try:
            if not val or pd.isna(val): return 0
            return float(str(val).replace(',', ''))
        except: return 0

    for i, r in df.iterrows():
        m_code = str(r.get("Mã số máy", "")).strip()
        if not m_code: continue
        
        try:
            # 1. UPSERT Machine
            m_res = supabase.table("machines").upsert({
                "machine_code": m_code,
                "region": str(r.get("Chi Nhánh", "Miền Bắc"))
            }, on_conflict="machine_code").execute()
            machine_id = m_res.data[0]["id"]

            # 2. Case
            c_val = str(r.get("Ngày Xác nhận", "")).strip()
            f_date = pd.to_datetime(c_val, dayfirst=True).strftime('%Y-%m-%d') if c_val else None

            case_payload = {
                "machine_id": machine_id,
                "branch": str(r.get("Chi Nhánh", "Miền Bắc")),
                "customer_name": str(r.get("Tên KH", "")),
                "issue_reason": str(r.get("Lý Do", "")),
                "confirmed_date": f_date
            }
            c_res = supabase.table("repair_cases").insert(case_payload).execute()
            case_id = c_res.data[0]["id"]

            # 3. Cost
            actual = clean_price(r.get("Chi Phí Thực Tế", 0))
            supabase.table("repair_costs").insert({
                "repair_case_id": case_id,
                "estimated_cost": clean_price(r.get("Chi Phí Dự Kiến", 0)),
                "actual_cost": actual,
                "confirmed_by": str(r.get("Người Kiểm Tra", ""))
            }).execute()

            # 4. Process
            supabase.table("repair_process").insert({
                "repair_case_id": case_id,
                "state": "DONE" if actual > 0 else "PENDING",
                "handled_by": str(r.get("Người Kiểm Tra", ""))
            }).execute()

            success_count += 1
        except Exception as e:
            st.error(f"Lỗi mã {m_code}: {e}")
        progress_bar.progress((i + 1) / len(df))
    return success_count

# --- 4. GIAO DIỆN CHÍNH ---
def main():
    # SIDEBAR
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/d/d0/Logo_4Oranges.png", width=150)
        st.title("🎨 4ORANGES OPS")
        if st.button('🔄 REFRESH DATABASE', type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        df_db = load_data_from_db()
        current_year = datetime.datetime.now().year
        
        list_years = sorted(df_db['NĂM'].unique().tolist(), reverse=True) if not df_db.empty else [current_year]
        sel_year = st.selectbox("📅 Chọn Năm", list_years)
        
        list_months = ["Tất cả"] + sorted(df_db[df_db['NĂM'] == sel_year]['THÁNG'].unique().tolist()) if not df_db.empty else ["Tất cả"]
        sel_month = st.selectbox("📆 Chọn Tháng", list_months)

    tabs = st.tabs(["📊 XU HƯỚNG", "💰 CHI PHÍ", "📥 NHẬP DỮ LIỆU"])

    with tabs[0]:
        if df_db.empty:
            st.info("Chưa có dữ liệu.")
        else:
            df_view = df_db[df_db['NĂM'] == sel_year]
            if sel_month != "Tất cả":
                df_view = df_view[df_view['THÁNG'] == sel_month]
            
            if not df_view.empty:
                k1, k2, k3 = st.columns(3)
                k1.metric("TỔNG CHI PHÍ", f"{df_view['CHI_PHÍ_THỰC'].sum():,.0f} đ")
                k2.metric("TỔNG SỰ VỤ", f"{len(df_view)} ca")
                k3.metric("TB CHI PHÍ", f"{df_view['CHI_PHÍ_THỰC'].mean():,.0f} đ")

                # Biểu đồ
                c1, c2 = st.columns(2)
                with c1:
                    fig_issue = px.bar(df_view['issue_reason'].value_counts().reset_index().head(10), 
                                      x='count', y='issue_reason', orientation='h', title="LÝ DO PHỔ BIẾN",
                                      color_discrete_sequence=[ORANGE_COLORS[0]])
                    st.plotly_chart(fig_issue, use_container_width=True)
                with c2:
                    fig_pie = px.pie(df_view, names='VÙNG', values='CHI_PHÍ_THỰC', title="CHI PHÍ THEO VÙNG", hole=0.4)
                    st.plotly_chart(fig_pie, use_container_width=True)

                st.subheader("📋 DANH SÁCH CHI TIẾT")
                display_cols = ['MÃ_MÁY', 'customer_name', 'issue_reason', 'VÙNG', 'NGÀY_HIỂN_THỊ', 'CHI_PHÍ_THỰC']
                st.dataframe(df_view[display_cols].sort_values('confirmed_date', ascending=False), 
                             use_container_width=True, hide_index=True)

    with tabs[2]:
        st.subheader("📥 NHẬP DỮ LIỆU GOOGLE SHEET")
        up = st.file_uploader("Chọn file CSV", type="csv")
        if up:
            df_up = pd.read_csv(up).fillna("")
            if st.button("🚀 ĐỒNG BỘ NGAY"):
                with st.spinner("Đang xử lý..."):
                    count = import_to_enterprise_schema(df_up)
                    if count > 0:
                        st.balloons()
                        st.success(f"Thành công {count} ca!")
                        st.cache_data.clear()

if __name__ == "__main__":
    main()
