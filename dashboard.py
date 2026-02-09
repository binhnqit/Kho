import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. HÀM LOAD DATA (SÁT THỰC TẾ SCHEMA) ---
@st.cache_data(ttl=60)
def load_data_final():
    try:
        # Truy vấn đúng các cột đang tồn tại trong DB của sếp
        res = supabase.table("repair_cases").select("""
            id, machine_id, branch, confirmed_date, 
            issue_reason, customer_name, compensation
        """).order("confirmed_date", desc=True).limit(3000).execute()
        
        if not res.data: return pd.DataFrame()
        
        df = pd.DataFrame(res.data)

        # --- FIX 1: CHUẨN HÓA NGUỒN CHI PHÍ ---
        # Vì Schema hiện tại dùng 'compensation', ta map nó thành 'CHI_PHÍ'
        # Nếu sếp muốn dùng repair_costs sau này, chỉ cần sửa logic ở đây
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)
        
        # --- FIX 3: ANTI-CRASH (KIỂM TRA CỘT CỐT LÕI) ---
        required = ['CHI_PHÍ', 'branch', 'issue_reason', 'machine_id']
        missing = [c for c in required if c not in df.columns]
        if missing:
            st.error(f"❌ DB Thiếu cột: {missing}. Hãy kiểm tra Table Editor trên Supabase.")
            st.stop()

        # CHUẨN HÓA DỮ LIỆU HIỂN THỊ
        df['confirmed_date'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        df = df.dropna(subset=['confirmed_date'])
        
        # FIX 4: VIỆT HÓA THỨ
        day_vn = {
            'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
            'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ Nhật'
        }
        df['THỨ'] = df['confirmed_date'].dt.day_name().map(day_vn)
        df['THÁNG'] = df['confirmed_date'].dt.month
        df['NĂM'] = df['confirmed_date'].dt.year
        
        return df
    except Exception as e:
        st.error(f"📡 Lỗi cấu trúc DB: {e}")
        return pd.DataFrame()

# --- 2. GIAO DIỆN PHÂN TÍCH ---
def main():
    st.title("🎨 4ORANGES - HỆ THỐNG QUẢN TRỊ VẬN HÀNH")
    df = load_data_final()
    
    if df.empty:
        st.info("Chưa có dữ liệu. Sếp hãy kiểm tra bảng 'repair_cases'.")
        return

    # Sidebar Filter
    sel_year = st.sidebar.selectbox("Năm", sorted(df['NĂM'].unique(), reverse=True))
    df_view = df[df['NĂM'] == sel_year]

    # KPI
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 TỔNG CHI PHÍ (COMPENSATION)", f"{df_view['CHI_PHÍ'].sum():,.0f} đ")
    c2.metric("📋 TỔNG SỰ VỤ", f"{len(df_view)} ca")
    c3.metric("🏢 VÙNG HOẠT ĐỘNG", f"{df_view['branch'].nunique()}")

    st.divider()

    # BIỂU ĐỒ
    col_l, col_r = st.columns([6, 4])
    
    with col_l:
        st.write("📅 **TẦN SUẤT THEO THỨ**")
        # Fix logic line chart
        line_data = df_view['THỨ'].value_counts().reindex(['Thứ 2','Thứ 3','Thứ 4','Thứ 5','Thứ 6','Thứ 7','Chủ Nhật']).reset_index()
        line_data.columns = ['THỨ', 'SỐ_CA']
        st.plotly_chart(px.line(line_data, x='THỨ', y='SỐ_CA', markers=True), use_container_width=True)

    with col_r:
        # FIX 2: PIE CHART CHUẨN COLUMNS
        st.write("🧩 **TỶ TRỌNG LÝ DO HỎNG**")
        reason_count = df_view['issue_reason'].value_counts().reset_index()
        reason_count.columns = ['LÝ_DO', 'SỐ_LƯỢNG'] # Đảm bảo tên cột rõ ràng
        fig_pie = px.pie(reason_count, names='LÝ_DO', values='SỐ_LƯỢNG', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

if __name__ == "__main__":
    main()
