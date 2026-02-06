import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. ĐỌC DỮ LIỆU TỪ DATABASE ---
def load_dashboard_data():
    res = supabase.table("machines").select("*").execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        return pd.DataFrame()
    
    # Chuẩn hóa tên cột để dùng cho biểu đồ (tương thích với code cũ của pro)
    df = df.rename(columns={
        "machine_code": "MÃ_MÁY",
        "machine_type": "LOẠI_MÁY",
        "region": "VÙNG"
    })
    # Giả lập cột NĂM/THÁNG từ created_at
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['NĂM'] = df['created_at'].dt.year
    df['THÁNG'] = df['created_at'].dt.month
    return df

# --- 2. LOGIC IMPORT ĐÀ NẴNG + MIỀN BẮC ---
def smart_import_file_1(df):
    success_count = 0
    # Tìm cột "GIAO LẠI..." bất kể là ĐN hay Miền Bắc
    col_giao_lai = [c for c in df.columns if "GIAO LẠI" in c]
    
    for i, r in df.iterrows():
        try:
            payload = {
                "machine_code": str(r["MÃ SỐ MÁY"]).strip(),
                "machine_type": str(r["LOẠI MÁY"]).strip(),
                "region": str(r["KHU VỰC"]).strip(),
            }
            # Ghi đè hoặc thêm mới dựa trên machine_code
            supabase.table("machines").upsert(payload, on_conflict="machine_code").execute()
            success_count += 1
        except Exception as e:
            st.error(f"Lỗi dòng {i+2}: {e}")
    return success_count

# --- 3. CẬP NHẬT GIAO DIỆN CHÍNH ---
def main():
    # ... (giữ phần kết nối Supabase của pro) ...

    # Thay vì đọc Google Sheet, đọc từ DB
    df_db = load_dashboard_data()

    if df_db.empty:
        st.warning("Dữ liệu Database rỗng. Vui lòng vào tab Ingestion để nhập dữ liệu.")
    else:
        # Sử dụng df_db cho các biểu đồ trong Tab Xu hướng
        with tabs[0]: 
            st.subheader("📊 PHÂN TÍCH TỪ DATABASE REAL-TIME")
            c1, c2 = st.columns(2)
            with c1:
                fig = px.pie(df_db, names='VÙNG', title="TỶ LỆ MÁY THEO KHU VỰC", hole=0.4, color_discrete_sequence=ORANGE_COLORS)
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                # Biểu đồ máy mới nhập theo tháng
                df_thang = df_db.groupby('THÁNG').size().reset_index(name='Số lượng')
                fig2 = px.bar(df_thang, x='THÁNG', y='Số lượng', title="LƯỢNG MÁY NHẬP MỚI", color_discrete_sequence=[ORANGE_COLORS[0]])
                st.plotly_chart(fig2, use_container_width=True)

    # Tab Ingestion linh hoạt
    with tabs[5]:
        st.subheader("📥 IMPORT DỮ LIỆU ĐA VÙNG (MB / ĐN / MT)")
        uploaded_file = st.file_uploader("Upload CSV sửa chữa", type=["csv"])
        if uploaded_file:
            df_up = pd.read_csv(uploaded_file).fillna("")
            # Kiểm tra các cột cốt lõi, không bắt bẻ cột "GIAO LẠI"
            core_cols = ["MÃ SỐ MÁY", "KHU VỰC", "LOẠI MÁY"]
            if all(c in df_up.columns for c in core_cols):
                st.success("✅ File hợp lệ (Hỗ trợ cả mẫu Đà Nẵng & Miền Bắc)")
                if st.button("🚀 ĐẨY DỮ LIỆU LÊN DATABASE"):
                    count = smart_import_file_1(df_up)
                    st.success(f"Đã cập nhật {count} máy thành công!")
                    st.cache_data.clear() # Để dashboard load lại dữ liệu mới
