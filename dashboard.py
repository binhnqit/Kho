import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from supabase import create_client

# --- 1. CẤU HÌNH & KẾT NỐI ---
st.set_page_config(page_title="4ORANGES - REPAIR OPS", layout="wide", page_icon="🎨")
ORANGE_COLORS = ["#FF8C00", "#FFA500", "#FF4500", "#E67E22", "#D35400"]

# Thông tin kết nối (Sử dụng Key pro cung cấp)
SUPABASE_URL = "https://cigbnbaanpebwrufzxfg.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_NQzqwJ4YhKC4sQGLxyLAyw_mwRFhkRf")

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Lỗi kết nối Supabase: {e}")

# --- 2. HÀM XỬ LÝ DỮ LIỆU (DATABASE SIDE) ---

@st.cache_data(ttl=60) # Cache trong 1 phút để tối ưu tốc độ
def load_data_from_db():
    try:
        # Truy vấn JOIN 3 bảng: Cases -> Machines -> Costs
        # Lưu ý: Syntax select() này giúp lấy dữ liệu từ các bảng quan hệ
        res = supabase.table("repair_cases").select(
            "*, machines(machine_code, machine_type), repair_costs(estimated_cost, actual_cost, confirmed_by)"
        ).execute()
        
        if not res.data:
            return pd.DataFrame()
            
        # Làm phẳng dữ liệu JSON (Nested JSON to Flat DataFrame)
        df = pd.json_normalize(res.data)
        
        # Đổi tên cột để dễ làm việc và khớp với code cũ
        df = df.rename(columns={
            "machines.machine_code": "MÃ_MÁY",
            "machines.machine_type": "LOẠI_MÁY",
            "repair_costs.actual_cost": "CHI_PHÍ_THỰC",
            "repair_costs.estimated_cost": "CHI_PHÍ_DỰ_KIẾN",
            "repair_costs.confirmed_by": "NGƯỜI_KIỂM_TRA",
            "branch": "VÙNG" # Khớp với biểu đồ cũ của pro
        })
        
        # Xử lý ngày tháng từ cột confirmed_date (Ngày xác nhận)
        if 'confirmed_date' in df.columns:
            df['confirmed_date'] = pd.to_datetime(df['confirmed_date'])
            df['NĂM'] = df['confirmed_date'].dt.year
            df['THÁNG'] = df['confirmed_date'].dt.month
        return df
    except Exception as e:
        st.error(f"Lỗi Database: {e}")
        return pd.DataFrame()

def smart_import_repair_data(df):
    """Hàm import thông minh chấp nhận cả mẫu MB và ĐN"""
    success_count = 0
    progress_bar = st.progress(0)
    
    for i, r in df.iterrows():
        try:
            # Lấy thông tin lõi
            payload = {
                "machine_code": str(r["MÃ SỐ MÁY"]).strip(),
                "machine_type": str(r["LOẠI MÁY"]).strip(),
                "region": str(r["KHU VỰC"]).strip(),
                # Bạn có thể lưu thêm các cột khác vào trường 'metadata' nếu DB có cột JSONB
            }
            # Upsert: Có rồi thì cập nhật, chưa có thì thêm mới
            supabase.table("machines").upsert(payload, on_conflict="machine_code").execute()
            success_count += 1
            progress_bar.progress((i + 1) / len(df))
        except Exception as e:
            st.error(f"Lỗi tại dòng {i+2}: {e}")
    return success_count
def load_enterprise_data(sel_year, sel_month):
    # Lấy dữ liệu kết hợp trạng thái sửa chữa
    res = supabase.table("machines").select("*").execute()
    df = pd.DataFrame(res.data)
    
    if df.empty: return df

    # Xử lý thời gian
    df['NGÀY_NHẬP'] = pd.to_datetime(df['created_at'])
    df['NĂM'] = df['NGÀY_NHẬP'].dt.year
    df['THÁNG'] = df['NGÀY_NHẬP'].dt.month
    
    # Filter theo thời gian
    df_filtered = df[df['NĂM'] == sel_year]
    if sel_month != "Tất cả":
        df_filtered = df_filtered[df_filtered['THÁNG'] == sel_month]
        
    return df_filtered
# --- 3. GIAO DIỆN CHÍNH ---

def main():
    # Sidebar: Lọc dữ liệu từ DB
    with st.sidebar:
        st.title("🎨 4ORANGES OPS")
        if st.button('🔄 REFRESH DATABASE', type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        df_db = load_data_from_db()
        
        sel_year = datetime.datetime.now().year
        sel_month = "Tất cả"

        if not df_db.empty:
            years = sorted(df_db['NĂM'].unique(), reverse=True)
            sel_year = st.selectbox("Chọn Năm", years)
            
            months = sorted(df_db[df_db['NĂM'] == sel_year]['THÁNG'].unique().tolist())
            sel_month = st.selectbox("Chọn Tháng", ["Tất cả"] + months)

    # Tabs chức năng
    # --- TABS DEFINITION ---
    # --- TABS DEFINITION ---
    tabs = st.tabs(["📊 XU HƯỚNG", "💰 CHI PHÍ", "🩺 SỨC KHỎE", "📦 KHO", "🧠 AI", "📥 NHẬP DỮ LIỆU"])

    # --- Tab Xu hướng ---
    with tabs[0]:
        # Gọi hàm đã sửa tên ở trên
        df_db = load_data_from_db()
        
        if df_db.empty:
            st.info("👋 Chào sếp! Hiện tại chưa có dữ liệu sự vụ sửa chữa nào.")
        else:
            # Bộ lọc theo Năm/Tháng từ Sidebar
            df_view = df_db[df_db['NĂM'] == sel_year]
            if sel_month != "Tất cả":
                df_view = df_view[df_view['THÁNG'] == sel_month]

            if df_view.empty:
                st.warning(f"Không có dữ liệu trong tháng {sel_month}/{sel_year}")
            else:
                st.subheader(f"📊 PHÂN TÍCH XU HƯỚNG {sel_month}/{sel_year}")

                # --- 4 KPI CHIẾN LƯỢC ---
                k1, k2, k3, k4 = st.columns(4)
                total_actual = df_view['CHI_PHÍ_THỰC'].sum()
                avg_cost = df_view['CHI_PHÍ_THỰC'].mean()
                unrepairable = df_view['is_unrepairable'].sum()
                
                k1.metric("TỔNG CHI PHÍ THỰC", f"{total_actual:,.0f} đ")
                k2.metric("TRUNG BÌNH/CA", f"{avg_cost:,.0f} đ")
                k3.metric("KHÔNG SỬA ĐƯỢC", f"{unrepairable} ca", delta_color="inverse")
                k4.metric("TỔNG SỰ VỤ", f"{len(df_view)} ca")

                st.divider()

                # --- BIỂU ĐỒ NÓI CHUYỆN ---
                c1, c2 = st.columns(2)
                with c1:
                    # Xu hướng lỗi (Lấy từ cột issue_reason)
                    issue_counts = df_view['issue_reason'].value_counts().reset_index()
                    issue_counts.columns = ['Lý do', 'Số lượng']
                    fig_issue = px.bar(issue_counts.head(10), x='Số lượng', y='Lý do', 
                                       orientation='h', title="TOP 10 LÝ DO HỎNG PHỔ BIẾN",
                                       color_discrete_sequence=[ORANGE_COLORS[0]])
                    st.plotly_chart(fig_issue, use_container_width=True)

                with c2:
                    # Cơ cấu chi phí theo chi nhánh
                    branch_stats = df_view.groupby('VÙNG')['CHI_PHÍ_THỰC'].sum().reset_index()
                    fig_pie = px.pie(branch_stats, names='VÙNG', values='CHI_PHÍ_THỰC', 
                                     title="CƠ CẤU CHI PHÍ THEO VÙNG", hole=0.4,
                                     color_discrete_sequence=ORANGE_COLORS)
                    st.plotly_chart(fig_pie, use_container_width=True)

                # --- BẢNG CHI TIẾT (GIỐNG GOOGLE SHEET) ---
                st.subheader("📋 DANH SÁCH CHI TIẾT")
                cols_to_show = ['MÃ_MÁY', 'customer_name', 'issue_reason', 'VÙNG', 'confirmed_date', 'CHI_PHÍ_THỰC']
                st.dataframe(df_view[cols_to_show].sort_values('confirmed_date', ascending=False), use_container_width=True)
    with tabs[5]:
        st.subheader("📥 CỔNG NHẬP DỮ LIỆU ĐA PHÂN CÔNG")
        st.write("Hệ thống tự động nhận diện mẫu file Miền Bắc và Đà Nẵng qua các cột chung.")
        
        uploaded_file = st.file_uploader("Chọn file CSV sửa chữa (MB hoặc ĐN)", type=["csv"])
        
        if uploaded_file:
            df_upload = pd.read_csv(uploaded_file).fillna("")
            
            # Kiểm tra các cột bắt buộc phải có để định danh máy
            required = ["MÃ SỐ MÁY", "KHU VỰC", "LOẠI MÁY"]
            missing = [c for c in required if c not in df_upload.columns]
            
            if missing:
                st.error(f"File thiếu các cột bắt buộc: {missing}")
            else:
                st.success("✅ File hợp lệ! Hệ thống đã sẵn sàng đồng bộ.")
                st.dataframe(df_upload.head(5), use_container_width=True)
                
                if st.button("🚀 XÁC NHẬN ĐẨY LÊN CLOUD DATABASE", type="primary"):
                    with st.spinner("Đang đồng bộ dữ liệu..."):
                        count = smart_import_repair_data(df_upload)
                        if count > 0:
                            st.balloons()
                            st.success(f"Đã cập nhật thành công {count} máy lên Database!")
                            # Xóa cache để tab Xu hướng cập nhật ngay
                            st.cache_data.clear()
                            st.info("Dữ liệu đã được làm mới. Vui lòng quay lại tab Xu hướng để kiểm tra.")

if __name__ == "__main__":
    main()
