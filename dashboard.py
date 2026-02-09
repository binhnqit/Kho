import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- NÂNG CẤP HÀM XỬ LÝ DỮ LIỆU ---
def load_data_from_db():
    data = fetch_repair_cases()
    if not data: return pd.DataFrame()
    
    df = pd.DataFrame(data)
    
    # 1. Chuẩn hóa thời gian
    if 'confirmed_date' in df.columns:
        df['confirmed_date'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        df = df.dropna(subset=['confirmed_date'])
        df['NĂM'] = df['confirmed_date'].dt.year
        df['THÁNG'] = df['confirmed_date'].dt.month
        df['TUẦN'] = df['confirmed_date'].dt.isocalendar().week
        df['THỨ'] = df['confirmed_date'].dt.day_name()
    
    # 2. Chuẩn hóa số liệu & Tên cột
    df = df.rename(columns={
        'branch': 'VÙNG', 
        'compensation': 'CHI_PHÍ',
        'customer_name': 'KHÁCH_HÀNG',
        'issue_reason': 'LÝ_DO'
    })
    df['CHI_PHÍ'] = pd.to_numeric(df['CHI_PHÍ'], errors='coerce').fillna(0)
    
    return df

# --- GIAO DIỆN PHÂN TÍCH (THAY THẾ TAB 0) ---
def render_analytics(df_view):
    # --- ROW 1: THỐNG KÊ NHANH ---
    st.subheader("🎯 CHỈ SỐ VẬN HÀNH CỐT YẾU")
    c1, c2, c3, c4 = st.columns(4)
    
    total_cost = df_view['CHI_PHÍ'].sum()
    total_cases = len(df_view)
    avg_cost = total_cost / total_cases if total_cases > 0 else 0
    
    c1.metric("💰 TỔNG CHI PHÍ", f"{total_cost:,.0f} đ")
    c2.metric("📋 TỔNG SỰ VỤ", f"{total_cases} ca")
    c3.metric("💸 CHI PHÍ TB/CA", f"{avg_cost:,.0f} đ")
    
    # Tính phần trăm thay đổi (giả định so với trung bình nếu sếp muốn)
    c4.metric("🏢 VÙNG TRỌNG ĐIỂM", df_view['VÙNG'].mode()[0] if not df_view.empty else "N/A")

    st.divider()

    # --- ROW 2: BIỂU ĐỒ CHIẾN LƯỢC ---
    col_l, col_r = st.columns([6, 4])
    
    with col_l:
        # Biểu đồ xu hướng nhiệt theo tuần/tháng
        st.write("📊 **XU HƯỚNG CHI PHÍ & TẦN SUẤT HỎNG**")
        trend_df = df_view.groupby('confirmed_date').agg({'CHI_PHÍ': 'sum', 'id': 'count'}).reset_index()
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(x=trend_df['confirmed_date'], y=trend_df['CHI_PHÍ'], 
                                     name='Chi phí', line=dict(color='#FF4500', width=3), fill='tozeroy'))
        fig_trend.update_layout(margin=dict(l=20, r=20, t=30, b=20), height=350)
        st.plotly_chart(fig_trend, use_container_width=True)

    with col_r:
        st.write("🧩 **PHÂN TÍCH TỶ TRỌNG LÝ DO**")
        reason_count = df_view['LÝ_DO'].value_counts().reset_index()
        fig_donut = px.pie(reason_count, names='LÝ_DO', values='count', hole=0.5,
                          color_discrete_sequence=px.colors.sequential.Oranges_r)
        fig_donut.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig_donut, use_container_width=True)

    # --- ROW 3: PHÂN TÍCH SÂU ĐỐI TƯỢNG ---
    st.divider()
    row3_c1, row3_c2 = st.columns(2)
    
    with row3_c1:
        st.write("🚛 **CHI PHÍ THEO CHI NHÁNH**")
        branch_cost = df_view.groupby('VÙNG')['CHI_PHÍ'].sum().sort_values(ascending=True).reset_index()
        fig_branch = px.bar(branch_cost, x='CHI_PHÍ', y='VÙNG', orientation='h',
                           color='CHI_PHÍ', color_continuous_scale='Oranges')
        st.plotly_chart(fig_branch, use_container_width=True)

    with row3_c2:
        st.write("🛠️ **TOP 10 MÁY CẦN BẢO TRÌ GẤP (HỎNG NHIỀU)**")
        top_machines = df_view.groupby('machine_id').size().reset_index(name='Số lần hỏng')
        top_machines = top_machines.sort_values('Số lần hỏng', ascending=False).head(10)
        st.dataframe(top_machines, use_container_width=True, hide_index=True)

    # --- ROW 4: DATA TABLE CÓ BỘ LỌC ---
    st.divider()
    with st.expander("🔍 TRUY XUẤT DỮ LIỆU CHI TIẾT"):
        search = st.text_input("🔎 Tìm kiếm nhanh (Mã máy, Tên KH, Lý do...):")
        if search:
            mask = df_view.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
            df_display = df_view[mask]
        else:
            df_display = df_view
        st.dataframe(df_display, use_container_width=True)
