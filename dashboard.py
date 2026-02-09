import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client

# --- 1. KẾT NỐI ---
SUPABASE_URL = "https://cigbnbaanpebwrufzxfg.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_NQzqwJ4YhKC4sQGLxyLAyw_mwRFhkRf")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. HÀM TRUY VẤN DỮ LIỆU (THEO FILE MACHINE INVENTORY) ---
@st.cache_data(ttl=60)
def load_repair_data():
    try:
        # Truy vấn chính xác theo các cột sếp gửi trong file
        # Lưu ý: Tôi lấy cả compensation, branch, customer_name, issue_reason
        res = supabase.table("repair_cases").select("""
            id, 
            machine_id, 
            received_date, 
            confirmed_date, 
            is_unrepairable, 
            compensation, 
            branch, 
            customer_name, 
            issue_reason, 
            note
        """).order("confirmed_date", desc=True).execute()
        
        if not res.data:
            return pd.DataFrame()
        
        df = pd.DataFrame(res.data)

        # 🟢 FIX 1: CHUẨN HÓA CHI PHÍ (Từ cột compensation)
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)

        # 🟢 FIX 3: ANTI-CRASH (Bảo vệ theo cột thực tế)
        # Kiểm tra xem các cột sếp gửi có tồn tại trong DataFrame không
        required_cols = ['id', 'confirmed_date', 'compensation', 'branch', 'issue_reason']
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            st.error(f"❌ Database thiếu cột so với Schema sếp gửi: {missing}")
            st.stop()

        # 🟢 FIX 4: CHUẨN HÓA THỜI GIAN & THỨ (VIỆT HÓA)
        df['confirmed_date'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        df = df.dropna(subset=['confirmed_date'])
        
        day_map = {
            'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
            'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ Nhật'
        }
        df['THỨ'] = df['confirmed_date'].dt.day_name().map(day_map)
        df['NĂM'] = df['confirmed_date'].dt.year
        df['THÁNG'] = df['confirmed_date'].dt.month
        
        return df
    except Exception as e:
        st.error(f"📡 Lỗi truy vấn Schema: {e}")
        return pd.DataFrame()

# --- 3. GIAO DIỆN HIỂN THỊ ---
def main():
    st.title("🎨 4ORANGES - HỆ THỐNG QUẢN TRỊ THEO SCHEMA")
    
    df = load_repair_data()
    
    if df.empty:
        st.warning("⚠️ Không có dữ liệu trong bảng repair_cases.")
        return

    # Bộ lọc
    with st.sidebar:
        st.header("🔍 BỘ LỌC")
        years = sorted(df['NĂM'].unique(), reverse=True)
        sel_year = st.selectbox("Chọn Năm", years)
        
        branches = ["Tất cả"] + sorted(df['branch'].unique().tolist())
        sel_branch = st.selectbox("Chọn Chi Nhánh", branches)

    # Lọc dữ liệu
    df_view = df[df['NĂM'] == sel_year]
    if sel_branch != "Tất cả":
        df_view = df_view[df_view['branch'] == sel_branch]

    # --- HIỂN THỊ KPI ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 TỔNG BỒI THƯỜNG", f"{df_view['CHI_PHÍ'].sum():,.0f} đ")
    c2.metric("📋 TỔNG SỰ VỤ", f"{len(df_view)} ca")
    c3.metric("🚫 KHÔNG THỂ SỬA", f"{df_view['is_unrepairable'].sum()} máy")
    c4.metric("🏢 CHI NHÁNH", f"{df_view['branch'].nunique()}")

    st.divider()

    # --- BIỂU ĐỒ ---
    col1, col2 = st.columns([6, 4])
    
    with col1:
        st.write("📈 **XU HƯỚNG SỰ VỤ THEO THỨ**")
        order = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ Nhật']
        day_stats = df_view['THỨ'].value_counts().reindex(order).reset_index()
        day_stats.columns = ['THỨ', 'SỐ CA']
        st.plotly_chart(px.line(day_stats, x='THỨ', y='SỐ CA', markers=True, color_discrete_sequence=['#FF4500']), use_container_width=True)

    with col2:
        # 🟢 FIX 2: PIE CHART LÝ DO HỎNG
        st.write("🧩 **TỶ TRỌNG LÝ DO HỎNG**")
        reason_df = df_view['issue_reason'].value_counts().reset_index()
        reason_df.columns = ['LÝ_DO', 'SỐ_LƯỢNG']
        st.plotly_chart(px.pie(reason_df, names='LÝ_DO', values='SỐ_LƯỢNG', hole=0.4), use_container_width=True)

    # BẢNG DỮ LIỆU GỐC
    st.subheader("📋 CHI TIẾT NHẬT KÝ VẬN HÀNH")
    st.dataframe(df_view[['confirmed_date', 'THỨ', 'branch', 'customer_name', 'issue_reason', 'CHI_PHÍ', 'note']], use_container_width=True)

if __name__ == "__main__":
    main()
