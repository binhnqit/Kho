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
def load_enterprise_dashboard_data():
    # Query kết hợp 3 bảng chính để lấy đầy đủ thông tin xu hướng
    query = """
    SELECT 
        rc.id as case_id,
        m.machine_code,
        m.machine_type,
        rc.branch,
        rc.customer_name,
        rc.issue_reason,
        rc.confirmed_date,
        rc.is_unrepairable,
        costs.estimated_cost,
        costs.actual_cost,
        costs.confirmed_by
    FROM repair_cases rc
    JOIN machines m ON rc.machine_id = m.id
    LEFT JOIN repair_costs costs ON rc.id = costs.repair_case_id
    """
    res = supabase.rpc("get_repair_summary").execute() # Hoặc dùng query select trực tiếp
    # Nếu không dùng RPC, pro dùng syntax của Supabase-py:
    res = supabase.table("repair_cases").select(
        "id, branch, customer_name, issue_reason, confirmed_date, is_unrepairable, "
        "machines(machine_code, machine_type), "
        "repair_costs(estimated_cost, actual_cost, confirmed_by)"
    ).execute()
    
    df = pd.json_normalize(res.data) # Chuyển đổi nested JSON thành bảng phẳng
    return df

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
    tabs = st.tabs(["📊 XU HƯỚNG", "💰 CHI PHÍ", "🩺 SỨC KHỎE", "📦 KHO", "🧠 AI", "📥 NHẬP DỮ LIỆU"])

    # --- TAB 0: XU HƯỚNG (ENTERPRISE DASHBOARD) ---
    with tabs[0]:
    df_main = load_enterprise_dashboard_data()
    
    if df_main.empty:
        st.info("Chưa có dữ liệu sự vụ sửa chữa. Sếp hãy nhập dữ liệu từ Google Sheet vào.")
    else:
        # Chuẩn hóa thời gian từ confirmed_date
        df_main['confirmed_date'] = pd.to_datetime(df_main['confirmed_date'])
        
        # --- KPI TÀI CHÍNH & VẬN HÀNH THỰC TẾ ---
        total_actual = df_main['repair_costs.actual_cost'].sum()
        total_est = df_main['repair_costs.estimated_cost'].sum()
        leakage = total_est - total_actual # Chênh lệch dự kiến vs thực tế
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("TỔNG CHI PHÍ THỰC", f"{total_actual:,.0f} đ")
        c2.metric("CHÊNH LỆCH DỰ KIẾN", f"{leakage:,.0f} đ", delta_color="inverse")
        c3.metric("MÁY KHÔNG SỬA ĐƯỢC", len(df_main[df_main['is_unrepairable'] == True]))
        c4.metric("TỔNG KHÁCH HÀNG", df_main['customer_name'].nunique())

        st.divider()

        # --- BIỂU ĐỒ XU HƯỚNG LỖI (Sếp cần cái này!) ---
        col1, col2 = st.columns(2)
        with col1:
            # Top lý do hỏng
            issue_counts = df_main['issue_reason'].value_counts().reset_index()
            fig_issue = px.bar(issue_counts, x='index', y='issue_reason', 
                               title="PHÂN TÍCH LÝ DO HỎNG (XU HƯỚNG LỖI)",
                               labels={'index': 'Lý do', 'issue_reason': 'Số ca'},
                               color_discrete_sequence=[ORANGE_COLORS[0]])
            st.plotly_chart(fig_issue, use_container_width=True)
            
        with col2:
            # Phân bổ chi phí theo chi nhánh (Miền Bắc vs Đà Nẵng)
            branch_costs = df_main.groupby('branch')['repair_costs.actual_cost'].sum().reset_index()
            fig_branch = px.pie(branch_costs, names='branch', values='repair_costs.actual_cost',
                                title="CƠ CẤU CHI PHÍ THEO CHI NHÁNH",
                                hole=0.4, color_discrete_sequence=ORANGE_COLORS)
            st.plotly_chart(fig_branch, use_container_width=True)

        # --- BẢNG CHI TIẾT SỰ VỤ ---
        st.subheader("📋 DANH SÁCH SỰ VỤ SỬA CHỮA CHI TIẾT")
        st.dataframe(df_main[[
            'machines.machine_code', 'customer_name', 'issue_reason', 
            'branch', 'confirmed_date', 'repair_costs.actual_cost'
        ]].sort_values('confirmed_date', ascending=False), use_container_width=True)

            # 4. INSIGHT DÀNH CHO QUẢN TRỊ
            st.markdown("---")
            st.subheader("📉 INSIGHT & CẢNH BÁO RỦI RO")
            i1, i2 = st.columns(2)
            
            with i1:
                st.warning("⚠️ **Vấn đề tồn đọng:**")
                st.write(f"- Tỷ lệ hoàn thành đang đạt {done_rate:.1f}%.")
                st.write(f"- {pending_cases} máy đang kẹt ở khâu kiểm tra và sửa ngoài.")
                
            with i2:
                st.success("💡 **Đề xuất tối ưu:**")
                top_vung = df_view['VÙNG'].mode()[0] if not df_view.empty else "N/A"
                st.write(f"- Tập trung nhân lực cho vùng **{top_vung}** vì lượng máy nhận cao nhất.")
                st.write("- Rà soát lại danh sách 'Hư - Thanh lý' để thu hồi linh kiện.")
    # --- TAB 5: NHẬP DỮ LIỆU (HỖ TRỢ MB & ĐN) ---
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
