import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client

# --- 1. KẾT NỐI (Giữ nguyên cấu trúc Secrets) ---
url = "https://cigbnbaanpebwrufzxfg.supabase.co"
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. HÀM LOAD & CHUẨN HÓA DỮ LIỆU ---
@st.cache_data(ttl=60)
def load_repair_data_final():
    try:
        # Truy vấn toàn bộ để xử lý logic nội bộ
        res = supabase.table("repair_cases").select("*").execute()
        if not res.data:
            return pd.DataFrame()
        
        df = pd.DataFrame(res.data)

        # A. Ép kiểu số cho tiền (Xử lý chuỗi 'false' hoặc 'None')
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)
        
        # B. Xử lý ngày tháng & Thứ
        df['date_dt'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        # Loại bỏ dòng không có ngày để tránh lỗi biểu đồ thời gian
        df = df.dropna(subset=['date_dt'])
        
        df['NĂM'] = df['date_dt'].dt.year.astype(int)
        df['THÁNG'] = df['date_dt'].dt.month.astype(int)
        
        day_map = {
            'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
            'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ Nhật'
        }
        df['THỨ'] = df['date_dt'].dt.day_name().map(day_map)

        # C. Sửa lỗi Encoding Tiếng Việt
        encoding_fix = {
            "Miá» n Trung": "Miền Trung",
            "Miá» n Báº¯c": "Miền Bắc",
            "Miá» n Nam": "Miền Nam",
            "VÅ© Há»“ng Yáº¿n": "Vũ Hồng Yến"
        }
        df['branch'] = df['branch'].replace(encoding_fix).fillna("Chưa xác định")
        df['customer_name'] = df['customer_name'].replace(encoding_fix).fillna("Khách vãng lai")
        df['issue_reason'] = df['issue_reason'].fillna("Chưa rõ lý do")

        return df
    except Exception as e:
        st.error(f"Lỗi Load Data: {e}")
        return pd.DataFrame()

# --- 3. GIAO DIỆN CHÍNH ---
def main():
    st.set_page_config(page_title="4ORANGES - REPAIR OPS", layout="wide")
    st.title("🎨 4ORANGES - HỆ THỐNG QUẢN TRỊ VẬN HÀNH")
    
    df = load_repair_data_final()
    
    if df.empty:
        st.warning("⚠️ Không có dữ liệu hoặc lỗi phân quyền RLS. Hãy kiểm tra Checkpoint 1 & 2.")
        return

    # --- BỘ LỌC SIDEBAR ---
    with st.sidebar:
        st.header("🔍 BỘ LỌC")
        years = sorted(df['NĂM'].unique(), reverse=True)
        sel_year = st.selectbox("Chọn Năm", years)
        
        branches = ["Tất cả"] + sorted(df['branch'].unique().tolist())
        sel_branch = st.selectbox("Chọn Chi Nhánh", branches)

    # Lọc dữ liệu theo lựa chọn
    df_view = df[df['NĂM'] == sel_year]
    if sel_branch != "Tất cả":
        df_view = df_view[df_view['branch'] == sel_branch]

    # --- HIỂN THỊ KPI ---
    st.subheader(f"📊 Chỉ số vận hành năm {sel_year} ({sel_branch})")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 TỔNG BỒI THƯỜNG", f"{df_view['CHI_PHÍ'].sum():,.0f} đ")
    c2.metric("📋 TỔNG SỰ VỤ", f"{len(df_view)} ca")
    c3.metric("🚫 KHÔNG THỂ SỬA", f"{int(df_view['is_unrepairable'].sum())} máy")
    c4.metric("🏢 CHI NHÁNH", f"{df_view['branch'].nunique()}")

    st.divider()

    # --- BIỂU ĐỒ PHÂN TÍCH ---
    col1, col2 = st.columns([6, 4])
    
    with col1:
        st.write("📈 **XU HƯỚNG SỰ VỤ THEO THỨ**")
        order = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ Nhật']
        day_stats = df_view['THỨ'].value_counts().reindex(order).reset_index()
        day_stats.columns = ['THỨ', 'SỐ CA']
        fig_line = px.line(day_stats, x='THỨ', y='SỐ CA', markers=True, 
                          color_discrete_sequence=['#FF4500'])
        st.plotly_chart(fig_line, use_container_width=True)

    with col2:
        st.write("🧩 **TỶ TRỌNG LÝ DO HỎNG**")
        reason_df = df_view['issue_reason'].value_counts().reset_index().head(10)
        reason_df.columns = ['LÝ_DO', 'SỐ_LƯỢNG']
        fig_pie = px.pie(reason_df, names='LÝ_DO', values='SỐ_LƯỢNG', hole=0.4,
                        color_discrete_sequence=px.colors.sequential.Oranges_r)
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- BẢNG DỮ LIỆU CHI TIẾT ---
    st.subheader("📋 NHẬT KÝ VẬN HÀNH CHI TIẾT")
    # Định dạng lại ngày để hiển thị bảng cho đẹp
    df_display = df_view.copy()
    df_display['NGÀY'] = df_display['date_dt'].dt.strftime('%d/%m/%Y')
    
    cols_to_show = ['NGÀY', 'THỨ', 'branch', 'customer_name', 'issue_reason', 'CHI_PHÍ', 'note']
    st.dataframe(
        df_display[cols_to_show].sort_values('date_dt', ascending=False), 
        use_container_width=True, 
        hide_index=True
    )

if __name__ == "__main__":
    main()
