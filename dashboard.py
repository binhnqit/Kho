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
        # Truy vấn lấy Case + Machine + Costs
        res = supabase.table("repair_cases").select(
            "*, machines(machine_code, machine_type), repair_costs(estimated_cost, actual_cost, confirmed_by)"
        ).execute()
        
        if not res.data:
            return pd.DataFrame()
            
        df = pd.json_normalize(res.data)
        
        # MAPPING CỘT - Đảm bảo tên cột khớp tuyệt đối với tab Xu hướng
        mapping = {
            "machines.machine_code": "MÃ_MÁY",
            "machines.machine_type": "LOẠI_MÁY",
            "repair_costs.actual_cost": "CHI_PHÍ_THỰC",
            "repair_costs.estimated_cost": "CHI_PHÍ_DỰ_KIẾN",
            "repair_costs.confirmed_by": "NGƯỜI_KIỂM_TRA",
            "branch": "VÙNG"
        }
        
        # Chỉ đổi tên những cột thực sự tồn tại trong dữ liệu trả về
        existing_mapping = {k: v for k, v in mapping.items() if k in df.columns}
        df = df.rename(columns=existing_mapping)
        
        # CỦNG CỐ DỮ LIỆU: Nếu thiếu cột do DB trống, tự tạo cột đó với giá trị 0/Rỗng
        expected_cols = ["CHI_PHÍ_THỰC", "CHI_PHÍ_DỰ_KIẾN", "MÃ_MÁY", "VÙNG", "is_unrepairable", "issue_reason"]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = 0 if "CHI_PHÍ" in col else "Chưa xác định"

        # Xử lý thời gian
        if 'confirmed_date' in df.columns and df['confirmed_date'].notnull().any():
            df['confirmed_date'] = pd.to_datetime(df['confirmed_date'])
            df['NĂM'] = df['confirmed_date'].dt.year
            df['THÁNG'] = df['confirmed_date'].dt.month
        else:
            df['NĂM'] = datetime.datetime.now().year
            df['THÁNG'] = datetime.datetime.now().month

        return df.fillna(0) # Thay thế các giá trị NaN bằng 0 để tránh lỗi tính toán sum()
    except Exception as e:
        st.error(f"Lỗi Load Data: {e}")
        return pd.DataFrame()

def import_to_enterprise_schema(df):
    success_count = 0
    progress_bar = st.progress(0)
    
    # Hàm hỗ trợ làm sạch giá tiền
    def clean_price(val):
        try:
            if not val or pd.isna(val): return 0
            return float(str(val).replace(',', ''))
        except:
            return 0

    for i, r in df.iterrows():
        m_code = str(r.get("Mã số máy", "")).strip()
        if not m_code: continue
        
        try:
            # --- BƯỚC 1: UPSERT MACHINE ---
            m_res = supabase.table("machines").upsert({
                "machine_code": m_code,
                "region": str(r.get("Chi Nhánh", "Miền Bắc"))
            }, on_conflict="machine_code").execute()
            machine_id = m_res.data[0]["id"]

            # --- BƯỚC 2: CHUẨN HÓA NGÀY THÁNG & TẠO CASE ---
            confirmed_val = str(r.get("Ngày Xác nhận", "")).strip()
            formatted_date = None
            
            if confirmed_val and confirmed_val.lower() != "nan":
                try:
                    # Ép định dạng dd/mm/yyyy sang yyyy-mm-dd để Postgres không báo lỗi
                    formatted_date = pd.to_datetime(confirmed_val, dayfirst=True).strftime('%Y-%m-%d')
                except:
                    formatted_date = None

            case_payload = {
                "machine_id": machine_id,
                "branch": str(r.get("Chi Nhánh", "Miền Bắc")),
                "customer_name": str(r.get("Tên KH", "")),
                "issue_reason": str(r.get("Lý Do", "")),
                "note": str(r.get("Ghi Chú", "")),
                "confirmed_date": formatted_date,
                "is_unrepairable": False
            }
            c_res = supabase.table("repair_cases").insert(case_payload).execute()
            case_id = c_res.data[0]["id"]

            # --- BƯỚC 3: ĐẨY CHI PHÍ ---
            actual_cost = clean_price(r.get("Chi Phí Thực Tế", 0))
            cost_payload = {
                "repair_case_id": case_id,
                "estimated_cost": clean_price(r.get("Chi Phí Dự Kiến", 0)),
                "actual_cost": actual_cost,
                "confirmed_by": str(r.get("Người Kiểm Tra", ""))
            }
            supabase.table("repair_costs").insert(cost_payload).execute()

            # --- BƯỚC 4: KHỞI TẠO QUY TRÌNH (FIX LỖI ENUM) ---
            # Lưu ý: Nếu DB báo lỗi Enum, sếp hãy chạy SQL ALTER TABLE đã gửi ở trên
            state_value = "DONE" if actual_cost > 0 else "PENDING"
            
            process_payload = {
                "repair_case_id": case_id,
                "state": state_value,
                "handled_by": str(r.get("Người Kiểm Tra", "")),
                "started_at": formatted_date if formatted_date else None
            }
            supabase.table("repair_process").insert(process_payload).execute()

            success_count += 1
            
        except Exception as e:
            st.error(f"❌ Lỗi tại dòng mã máy {m_code}: {str(e)}")
        
        # Cập nhật thanh tiến trình
        progress_bar.progress((i + 1) / len(df))
            
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
    # --- SIDEBAR LOGIC ---
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/d/d0/Logo_4Oranges.png", width=150) # Tùy chọn logo sếp nhé
        st.title("🎨 4ORANGES OPS")
        
        if st.button('🔄 REFRESH DATABASE', type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.divider()

        # Load dữ liệu để lấy danh sách Năm
        df_db = load_data_from_db()
        
        current_year = datetime.datetime.now().year
        
        if not df_db.empty and 'NĂM' in df_db.columns:
            # Lấy danh sách năm duy nhất, lọc bỏ giá trị 0 hoặc NaN
            list_years = sorted([int(y) for y in df_db['NĂM'].unique() if y > 0], reverse=True)
            if not list_years:
                list_years = [current_year]
        else:
            list_years = [current_year]

        # Fix lỗi "No results": Luôn có ít nhất năm hiện tại
        sel_year = st.selectbox("📅 Chọn Năm", list_years, index=0)
        
        # Logic chọn Tháng tương tự
        if not df_db.empty and 'THÁNG' in df_db.columns:
            list_months = sorted([int(m) for m in df_db[df_db['NĂM'] == sel_year]['THÁNG'].unique() if m > 0])
            sel_month = st.selectbox("📆 Chọn Tháng", ["Tất cả"] + list_months)
        else:
            sel_month = st.selectbox("📆 Chọn Tháng", ["Tất cả"])

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
        st.subheader("📥 CỔNG ĐỒNG BỘ DỮ LIỆU GOOGLE SHEET")
        st.info("Hệ thống sẽ tự động phân bổ dữ liệu vào 4 bảng: Machines, Cases, Costs và Process.")
        
        uploaded_file = st.file_uploader("Upload File CSV từ Google Sheet", type=["csv"])
        
        if uploaded_file:
            df_upload = pd.read_csv(uploaded_file).fillna("")
            st.dataframe(df_upload.head(3), use_container_width=True)
            
            if st.button("🚀 BẮT ĐẦU ĐỒNG BỘ MULTI-TABLE", type="primary"):
                with st.spinner("Đang thực hiện cấu trúc lại dữ liệu..."):
                    count = import_to_enterprise_schema(df_upload)
                    if count > 0:
                        st.balloons()
                        st.success(f"Đã đồng bộ thành công {count} sự vụ vào hệ thống!")
                        st.cache_data.clear() # Xóa cache để tab Xu hướng cập nhật ngay

if __name__ == "__main__":
    main()
