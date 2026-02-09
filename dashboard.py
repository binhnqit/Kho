import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client

# --- 1. KẾT NỐI ---
SUPABASE_URL = "https://cigbnbaanpebwrufzxfg.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. HÀM LOAD & XỬ LÝ DỮ LIỆU (OPTIMIZED) ---
@st.cache_data(ttl=60)
def load_and_clean_data():
    try:
        # Truy vấn đúng các cột trong schema Machine inventory
        res = supabase.table("repair_cases").select(
            "id, machine_id, branch, confirmed_date, issue_reason, customer_name, compensation, is_unrepairable"
        ).order("confirmed_date", desc=True).execute()
        
        if not res.data:
            return pd.DataFrame()
            
        df = pd.DataFrame(res.data)

        # Chuẩn hóa ngày tháng
        df['confirmed_date'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        df = df.dropna(subset=['confirmed_date']) # Loại bỏ dòng lỗi ngày
        
        # Tạo cột thời gian bổ sung
        df['NĂM'] = df['confirmed_date'].dt.year.astype(int)
        df['THÁNG'] = df['confirmed_date'].dt.month.astype(int)
        df['NGÀY_HIỂN_THỊ'] = df['confirmed_date'].dt.strftime('%d/%m/%Y')
        
        # Xử lý số liệu: Bồi thường & Trạng thái hỏng
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)
        df['HỎNG_HẲN'] = df['is_unrepairable'].apply(lambda x: 1 if x is True else 0)

        # Map tên cột cho UI Tiếng Việt
        df = df.rename(columns={
            'branch': 'VÙNG',
            'issue_reason': 'LÝ_DO',
            'customer_name': 'KHÁCH_HÀNG'
        })
        
        return df
    except Exception as e:
        st.error(f"📡 Lỗi dữ liệu: {e}")
        return pd.DataFrame()

# --- 3. GIAO DIỆN CHÍNH ---
def main():
    st.title("🎨 4ORANGES - HỆ THỐNG PHÂN TÍCH VẬN HÀNH")
    
    df = load_and_clean_data()
    
    if df.empty:
        st.warning("⚠️ Đã kết nối nhưng chưa thấy dữ liệu hợp lệ trong bảng repair_cases.")
        return

    # --- SIDEBAR FILTERS ---
    with st.sidebar:
        st.header("🔍 BỘ LỌC DỮ LIỆU")
        years = sorted(df['NĂM'].unique(), reverse=True)
        sel_year = st.selectbox("📅 Chọn Năm", years)
        
        months = ["Tất cả"] + sorted(df[df['NĂM'] == sel_year]['THÁNG'].unique().tolist())
        sel_month = st.selectbox("📆 Chọn Tháng", months)
        
        branches = ["Toàn quốc"] + sorted(df['VÙNG'].unique().tolist())
        sel_branch = st.selectbox("🏢 Chi Nhánh", branches)

    # Lọc DataFrame theo người dùng chọn
    df_view = df[df['NĂM'] == sel_year]
    if sel_month != "Tất cả":
        df_view = df_view[df_view['THÁNG'] == sel_month]
    if sel_branch != "Toàn quốc":
        df_view = df_view[df_view['VÙNG'] == sel_branch]

    # --- KPI CHÍNH ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("💰 TỔNG CHI PHÍ", f"{df_view['CHI_PHÍ'].sum():,.0f} đ")
    with c2:
        st.metric("📋 TỔNG SỰ VỤ", f"{len(df_view)} ca")
    with c3:
        fail_rate = (df_view['HỎNG_HẲN'].sum() / len(df_view) * 100) if len(df_view) > 0 else 0
        st.metric("🚫 TỶ LỆ HỎNG HẲN", f"{fail_rate:.1f}%")
    with c4:
        st.metric("🔧 TRUNG BÌNH/CA", f"{(df_view['CHI_PHÍ'].mean() if len(df_view) > 0 else 0):,.0f} đ")

    st.divider()

    # --- BIỂU ĐỒ PHÂN TÍCH ---
    row1_l, row1_r = st.columns([6, 4])
    
    with row1_l:
        st.write("📊 **DIỄN BIẾN CHI PHÍ THEO THỜI GIAN**")
        daily_cost = df_view.groupby('confirmed_date')['CHI_PHÍ'].sum().reset_index()
        fig_area = px.area(daily_cost, x='confirmed_date', y='CHI_PHÍ', 
                          color_discrete_sequence=['#FF4500'],
                          labels={'confirmed_date': 'Ngày', 'CHI_PHÍ': 'Số tiền'})
        st.plotly_chart(fig_area, use_container_width=True)

    with row1_r:
        st.write("🧩 **CƠ CẤU LÝ DO HỎNG**")
        reason_stats = df_view['LÝ_DO'].value_counts().reset_index()
        reason_stats.columns = ['LÝ_DO', 'SỐ_LƯỢNG']
        fig_pie = px.pie(reason_stats, names='LÝ_DO', values='SỐ_LƯỢNG', hole=0.5,
                        color_discrete_sequence=px.colors.sequential.Oranges_r)
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- DANH SÁCH CHI TIẾT ---
    st.subheader("📋 NHẬT KÝ CHI TIẾT SỰ VỤ")
    cols = ['NGÀY_HIỂN_THỊ', 'VÙNG', 'KHÁCH_HÀNG', 'LÝ_DO', 'CHI_PHÍ', 'machine_id']
    st.dataframe(df_view[cols].sort_values('NGÀY_HIỂN_THỊ', ascending=False), 
                 use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
