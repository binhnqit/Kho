import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client

# --- 1. CẤU HÌNH & KẾT NỐI ---
st.set_page_config(page_title="4ORANGES - ENTERPRISE OPS", layout="wide", page_icon="🎨")

# Màu sắc thương hiệu 4Oranges
ORANGE_COLORS = ["#FF8C00", "#FFA500", "#FF4500", "#E67E22", "#D35400"]

SUPABASE_URL = "https://cigbnbaanpebwrufzxfg.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_NQzqwJ4YhKC4sQGLxyLAyw_mwRFhkRf")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. HÀM LOAD DATA CHUẨN (FIX 1: JOIN REPAIR_COSTS) ---
@st.cache_data(ttl=60)
def load_data_enterprise():
    try:
        # Query JOIN lấy actual_cost từ bảng liên kết repair_costs
        res = supabase.table("repair_cases").select("""
            id,
            machine_id,
            branch,
            confirmed_date,
            issue_reason,
            customer_name,
            repair_costs(actual_cost)
        """).order("confirmed_date", desc=True).limit(4000).execute()
        
        if not res.data: return pd.DataFrame()
        
        df = pd.DataFrame(res.data)

        # Xử lý bóc tách giá trị từ bảng JOIN
        # 👉 df['CHI_PHÍ'] = lambda x: x[0]['actual_cost'] if x else 0
        df['CHI_PHÍ'] = df['repair_costs'].apply(
            lambda x: x[0]['actual_cost'] if (isinstance(x, list) and len(x) > 0) else 0
        )

        # --- FIX 3: BẢO VỆ DASHBOARD (ANTI-CRASH) ---
        required_cols = ['CHI_PHÍ', 'branch', 'issue_reason', 'machine_id']
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            st.error(f"❌ Hệ thống thiếu cột dữ liệu nghiệp vụ: {missing}")
            st.stop()

        # Chuẩn hóa thời gian
        df['confirmed_date'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        df = df.dropna(subset=['confirmed_date'])
        
        # --- FIX 4: CHUẨN HÓA THỨ (VIỆT HÓA) ---
        day_map = {
            'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
            'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ Nhật'
        }
        df['THỨ'] = df['confirmed_date'].dt.day_name().map(day_map)
        df['NĂM'] = df['confirmed_date'].dt.year.astype(int)
        df['THÁNG'] = df['confirmed_date'].dt.month.astype(int)
        df['NGÀY_HIỂN_THỊ'] = df['confirmed_date'].dt.strftime('%d/%m/%Y')

        # Đổi tên cột hiển thị UI
        df = df.rename(columns={
            'branch': 'VÙNG', 
            'issue_reason': 'LÝ DO HỎNG',
            'customer_name': 'TÊN KHÁCH HÀNG'
        })
        
        return df
    except Exception as e:
        st.error(f"📡 Lỗi Schema hoặc Kết nối: {e}")
        return pd.DataFrame()

# --- 3. HÀM IMPORT (GIỮ NGUYÊN LOGIC CỦA SẾP) ---
def import_data(df_chunk):
    success_count = 0
    for _, r in df_chunk.iterrows():
        try:
            m_code = str(r.get("Mã số máy", "")).strip()
            if not m_code or m_code.lower() == "nan": continue

            # Upsert Machine
            m_res = supabase.table("machines").upsert({
                "machine_code": m_code,
                "region": str(r.get("Chi Nhánh", "Chưa xác định"))
            }, on_conflict="machine_code").execute()
            
            if not m_res.data: continue
            m_id = m_res.data[0]["id"]

            # Format Date
            c_val = str(r.get("Ngày Xác nhận", "")).strip()
            f_date = pd.to_datetime(c_val, dayfirst=True).strftime('%Y-%m-%d') if c_val else None

            # Insert Case
            c_res = supabase.table("repair_cases").insert({
                "machine_id": m_id,
                "branch": str(r.get("Chi Nhánh", "Chưa xác định")),
                "issue_reason": str(r.get("Lý Do", "")),
                "customer_name": str(r.get("Tên KH", "")),
                "confirmed_date": f_date
            }).execute()

            # Insert Cost (Để JOIN ở FIX 1 hoạt động)
            if c_res.data:
                cost_raw = str(r.get("Chi Phí Thực Tế", "0")).replace(",", "")
                supabase.table("repair_costs").insert({
                    "repair_case_id": c_res.data[0]["id"],
                    "actual_cost": float(cost_raw)
                }).execute()
            
            success_count += 1
        except Exception as e:
            st.error(f"⚠️ Lỗi dòng máy {m_code}: {e}")
    return success_count

# --- 4. GIAO DIỆN CHÍNH ---
def main():
    with st.sidebar:
        st.title("🎨 4ORANGES OPS")
        if st.button('🔄 LÀM MỚI DỮ LIỆU'):
            st.cache_data.clear()
            st.rerun()
            
    df_db = load_data_enterprise()
    
    tabs = st.tabs(["📊 PHÂN TÍCH XU HƯỚNG", "📥 NHẬP DỮ LIỆU"])

    with tabs[0]:
        if df_db.empty:
            st.info("💡 Hệ thống chưa có dữ liệu.")
        else:
            # Filters
            years = sorted(df_db['NĂM'].unique(), reverse=True)
            sel_year = st.sidebar.selectbox("📅 Năm", years)
            df_view = df_db[df_db['NĂM'] == sel_year]

            # KPI Header
            c1, c2, c3 = st.columns(3)
            c1.metric("💰 TỔNG CHI PHÍ THỰC", f"{df_view['CHI_PHÍ'].sum():,.0f} đ")
            c2.metric("📋 TỔNG SỰ VỤ", f"{len(df_view)} ca")
            c3.metric("🏢 CHI NHÁNH", f"{df_view['VÙNG'].nunique()}")

            st.divider()

            # Chart Row
            col_l, col_r = st.columns(2)
            with col_l:
                # Biểu đồ Thứ (Sử dụng FIX 4)
                st.write("📅 **TẦN SUẤT THEO THỨ**")
                order = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ Nhật']
                day_data = df_view['THỨ'].value_counts().reindex(order).reset_index()
                day_data.columns = ['THỨ', 'SỐ CA']
                st.plotly_chart(px.line(day_data, x='THỨ', y='SỐ CA', markers=True), use_container_width=True)

            with col_r:
                # --- FIX 2: SỬA PIE CHART ---
                st.write("🧩 **TỶ TRỌNG LÝ DO HỎNG**")
                reason_count = df_view['LÝ DO HỎNG'].value_counts().reset_index()
                reason_count.columns = ['LÝ DO HỎNG', 'count'] # Ép tên cột chuẩn
                st.plotly_chart(px.pie(reason_count, names='LÝ DO HỎNG', values='count', hole=0.4), use_container_width=True)

            st.subheader("📋 CHI TIẾT SỰ VỤ")
            st.dataframe(df_view[['NGÀY_HIỂN_THỊ', 'THỨ', 'VÙNG', 'TÊN KHÁCH HÀNG', 'LÝ DO HỎNG', 'CHI_PHÍ']], use_container_width=True)

    with tabs[1]:
        up = st.file_uploader("Nạp CSV", type="csv")
        if up and st.button("🚀 ĐỒNG BỘ"):
            df_up = pd.read_csv(up, encoding='utf-8-sig').fillna("").ffill()
            df_up.columns = [c.strip() for c in df_up.columns]
            success = import_data(df_up)
            st.success(f"Nạp thành công {success} dòng!")
            st.cache_data.clear()

if __name__ == "__main__":
    main()
