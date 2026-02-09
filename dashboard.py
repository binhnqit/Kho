import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client

# --- 1. KẾT NỐI ---
SUPABASE_URL = "https://cigbnbaanpebwrufzxfg.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. HÀM LOAD DATA (BẢN VÁ LỖI DỮ LIỆU THỰC) ---
@st.cache_data(ttl=60)
def load_data_final_v2():
    try:
        res = supabase.table("repair_cases").select("*").execute()
        if not res.data: return pd.DataFrame()
        
        df = pd.DataFrame(res.data)

        # Xử lý cột CHI PHÍ (Vì thực tế DB đang lưu là 'false' nên ta ép về 0)
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)
        
        # Xử lý NGÀY THÁNG (Nếu trống thì gán đại diện để không bị mất dòng)
        df['confirmed_date_clean'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        
        # Tạo thông tin thời gian (Xử lý dòng có ngày và không có ngày)
        df['NĂM'] = df['confirmed_date_clean'].dt.year.fillna(0).astype(int)
        df['THÁNG'] = df['confirmed_date_clean'].dt.month.fillna(0).astype(int)
        
        # Sửa lỗi hiển thị Tiếng Việt cho Chi Nhánh (Nếu có)
        branch_map = {"Miá» n Trung": "Miền Trung", "Miá» n Nam": "Miền Nam", "Miá» n Báº¯c": "Miền Bắc"}
        df['branch'] = df['branch'].replace(branch_map)

        return df
    except Exception as e:
        st.error(f"📡 Lỗi DB: {e}")
        return pd.DataFrame()

# --- 3. GIAO DIỆN ---
def main():
    st.set_page_config(page_title="4ORANGES - OPS V2", layout="wide")
    st.title("🎨 4ORANGES - QUẢN TRỊ SỰ VỤ BẢO TRÌ")

    df = load_data_final_v2()

    if df.empty:
        st.warning("⚠️ Không tìm thấy dòng nào trong bảng repair_cases!")
        return

    # Sidebar
    with st.sidebar:
        st.header("⚙️ BỘ LỌC")
        # Lọc Năm (Thêm tùy chọn 0 cho các ca chưa rõ ngày)
        years = sorted(df['NĂM'].unique(), reverse=True)
        year_labels = {y: str(y) if y != 0 else "Chưa xác nhận" for y in years}
        sel_year = st.selectbox("Chọn Năm", years, format_func=lambda x: year_labels[x])
        
        branches = ["Tất cả"] + sorted(df['branch'].dropna().unique().tolist())
        sel_branch = st.selectbox("Chi Nhánh", branches)

    # Filter Data
    df_view = df[df['NĂM'] == sel_year]
    if sel_branch != "Tất cả":
        df_view = df_view[df_view['branch'] == sel_branch]

    # --- KPI ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📋 TỔNG SỰ VỤ", f"{len(df_view)} ca")
    c2.metric("💰 TỔNG CHI PHÍ", f"{df_view['CHI_PHÍ'].sum():,.0f} đ")
    c3.metric("🏢 CHI NHÁNH", f"{df_view['branch'].nunique()}")
    c4.metric("🚫 HỎNG HẲN", f"{df_view['is_unrepairable'].sum()} máy")

    st.divider()

    # --- BIỂU ĐỒ ---
    col_l, col_r = st.columns(2)
    
    with col_l:
        st.write("📊 **TOP LÝ DO HỎNG**")
        reason_df = df_view['issue_reason'].value_counts().reset_index().head(10)
        reason_df.columns = ['LÝ_DO', 'SỐ_CA']
        st.plotly_chart(px.bar(reason_df, x='SỐ_CA', y='LÝ_DO', orientation='h', 
                               color_discrete_sequence=['#FF8C00']), use_container_width=True)

    with col_r:
        st.write("🧩 **TỶ TRỌNG SỰ VỤ THEO VÙNG**")
        branch_df = df_view['branch'].value_counts().reset_index()
        st.plotly_chart(px.pie(branch_df, names='branch', values='count', hole=0.4,
                               color_discrete_sequence=px.colors.sequential.Oranges_r), use_container_width=True)

    # --- CHI TIẾT ---
    st.subheader("📋 DANH SÁCH SỰ VỤ CHI TIẾT")
    show_cols = ['confirmed_date', 'branch', 'customer_name', 'issue_reason', 'CHI_PHÍ', 'is_unrepairable']
    st.dataframe(df_view[show_cols].sort_values('confirmed_date', ascending=False), use_container_width=True)

if __name__ == "__main__":
    main()
