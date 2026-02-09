import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client

# --- 1. KẾT NỐI & CẤU HÌNH ---
st.set_page_config(page_title="4ORANGES - OPS ANALYTICS", layout="wide")

SUPABASE_URL = "https://cigbnbaanpebwrufzxfg.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_NQzqwJ4YhKC4sQGLxyLAyw_mwRFhkRf")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. HÀM LOAD DATA (FIX 1: JOIN REPAIR_COSTS) ---
@st.cache_data(ttl=60)
def load_data_pro():
    try:
        # QUERY JOIN THẲNG SANG BẢNG REPAIR_COSTS
        res = supabase.table("repair_cases").select("""
            id,
            machine_id,
            branch,
            confirmed_date,
            issue_reason,
            customer_name,
            repair_costs(actual_cost)
        """).order("confirmed_date", desc=True).limit(3000).execute()
        
        if not res.data: return pd.DataFrame()
        
        df = pd.DataFrame(res.data)

        # XỬ LÝ DỮ LIỆU SAU JOIN (Bóc tách list/dict từ Supabase)
        df['CHI_PHÍ'] = df['repair_costs'].apply(
            lambda x: x[0]['actual_cost'] if (isinstance(x, list) and len(x) > 0) else 0
        )
        
        # CHUẨN HÓA THỜI GIAN
        df['confirmed_date'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        df = df.dropna(subset=['confirmed_date'])
        
        # RENAME CHO ĐÚNG UI
        df = df.rename(columns={
            'branch': 'VÙNG', 
            'issue_reason': 'LÝ_DO',
            'customer_name': 'TÊN_KH'
        })

        # --- FIX 3: ANTI-CRASH (BẢO VỆ DASHBOARD) ---
        required_cols = ['CHI_PHÍ', 'VÙNG', 'LÝ_DO', 'machine_id']
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            st.error(f"❌ Hệ thống thiếu cột dữ liệu nghiệp vụ: {missing}")
            st.stop()

        # --- FIX 4: CHUẨN HÓA THỨ (TIẾNG VIỆT) ---
        # Chuyển tên thứ sang tiếng Việt
        day_map = {
            'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
            'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ Nhật'
        }
        df['THỨ'] = df['confirmed_date'].dt.day_name().map(day_map)
        df['NĂM'] = df['confirmed_date'].dt.year
        df['THÁNG'] = df['confirmed_date'].dt.month

        return df
    except Exception as e:
        st.error(f"📡 Lỗi kết nối hoặc xử lý Schema: {e}")
        return pd.DataFrame()

# --- 3. GIAO DIỆN CHÍNH ---
def main():
    st.sidebar.title("🎨 4ORANGES ANALYTICS")
    df = load_data_pro()

    if df.empty:
        st.warning("⚠️ Đang chờ dữ liệu từ Cloud...")
        return

    # Filter Sidebar
    years = sorted(df['NĂM'].unique(), reverse=True)
    sel_year = st.sidebar.selectbox("Chọn năm", years)
    df_view = df[df['NĂM'] == sel_year]

    # --- RENDER DASHBOARD ---
    st.title(f"📊 BÁO CÁO VẬN HÀNH NĂM {sel_year}")
    
    # KPI 
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 TỔNG CHI PHÍ THỰC", f"{df_view['CHI_PHÍ'].sum():,.0f} đ")
    c2.metric("📋 TỔNG SỰ VỤ", f"{len(df_view)} ca")
    c3.metric("🏢 CHI NHÁNH HOẠT ĐỘNG", f"{df_view['VÙNG'].nunique()}")

    st.divider()

    col_l, col_r = st.columns([6, 4])
    
    with col_l:
        # Xu hướng theo Thứ (Dùng Fix 4)
        st.write("📅 **TẦN SUẤT HỎNG THEO THỨ TRONG TUẦN**")
        order = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ Nhật']
        day_trend = df_view['THỨ'].value_counts().reindex(order).reset_index()
        fig_line = px.line(day_trend, x='THỨ', y='count', markers=True, 
                          color_discrete_sequence=['#FF4500'], title="Biểu đồ hiệu suất bảo trì")
        st.plotly_chart(fig_line, use_container_width=True)

    with col_r:
        # --- FIX 2: SỬA PIE CHART (SỬA LỖI RESET_INDEX) ---
        st.write("🧩 **TỶ TRỌNG LÝ DO HỎNG**")
        reason_count = df_view['LÝ_DO'].value_counts().reset_index()
        reason_count.columns = ['LÝ_DO', 'count'] # Đảm bảo tên cột chuẩn
        
        fig_pie = px.pie(reason_count, names='LÝ_DO', values='count', 
                        hole=0.4, color_discrete_sequence=px.colors.sequential.Oranges_r)
        fig_pie.update_layout(showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)

    # Chi tiết
    st.subheader("📝 NHẬT KÝ CHI PHÍ THỰC TẾ")
    st.dataframe(df_view[['confirmed_date', 'THỨ', 'VÙNG', 'LÝ_DO', 'CHI_PHÍ']].sort_values('confirmed_date', ascending=False), 
                 use_container_width=True)

if __name__ == "__main__":
    main()
