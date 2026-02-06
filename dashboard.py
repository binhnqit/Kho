import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from supabase import create_client

# --- 1. CẤU HÌNH & KẾT NỐI ---
st.set_page_config(page_title="4ORANGES - REPAIR OPS", layout="wide", page_icon="🎨")
ORANGE_COLORS = ["#FF8C00", "#FFA500", "#FF4500", "#E67E22", "#D35400"]

# Thông tin kết nối
SUPABASE_URL = "https://cigbnbaanpebwrufzxfg.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_NQzqwJ4YhKC4sQGLxyLAyw_mwRFhkRf")

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Lỗi kết nối Supabase: {e}")

# --- 2. HÀM LOAD DỮ LIỆU (PHÒNG THỦ TẦNG TẦNG LỚP LỚP) ---
@st.cache_data(ttl=60)
def load_data_from_db():
    try:
        # Lấy dữ liệu JOIN từ 3 bảng chính
        res = supabase.table("repair_cases").select(
            "*, machines(machine_code, region), repair_costs(estimated_cost, actual_cost, confirmed_by)"
        ).execute()
        
        if not res.data:
            return pd.DataFrame()
            
        df = pd.json_normalize(res.data)
        
        # Mapping cột để thống nhất logic hiển thị
        mapping = {
            "machines.machine_code": "MÃ_MÁY",
            "repair_costs.actual_cost": "CHI_PHÍ_THỰC",
            "repair_costs.estimated_cost": "CHI_PHÍ_DỰ_KIẾN",
            "branch": "VÙNG"
        }
        df = df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})

        # BIỆN PHÁP MẠNH: Tự tạo cột nếu thiếu để tránh lỗi KeyError
        REQUIRED = ['CHI_PHÍ_THỰC', 'CHI_PHÍ_DỰ_KIẾN', 'MÃ_MÁY', 'VÙNG', 'confirmed_date', 'customer_name', 'issue_reason', 'is_unrepairable']
        for col in REQUIRED:
            if col not in df.columns:
                df[col] = 0 if 'CHI_PHÍ' in col or 'is_unrepairable' in col else "N/A"

        # Xử lý ngày tháng chuyên sâu (Dứt điểm lỗi 00:00:00)
        if 'confirmed_date' in df.columns:
            df['confirmed_date'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
            df = df.dropna(subset=['confirmed_date'])
            df['NĂM'] = df['confirmed_date'].dt.year.astype(int)
            df['THÁNG'] = df['confirmed_date'].dt.month.astype(int)
            df['NGÀY_HIỂN_THỊ'] = df['confirmed_date'].dt.strftime('%d/%m/%Y')

        # Ép kiểu số cho tiền bạc
        df['CHI_PHÍ_THỰC'] = pd.to_numeric(df['CHI_PHÍ_THỰC'], errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Lỗi Load Data: {e}")
        return pd.DataFrame()

# --- 3. HÀM IMPORT DỮ LIỆU (ALL-IN-ONE) ---
def import_to_enterprise_schema(df):
    success_count = 0
    progress_bar = st.progress(0)
    
    # --- BIỆN PHÁP MẠNH 1: TỰ ĐIỀN NGÀY CÒN THIẾU (FORWARD FILL) ---
    # Thay thế khoảng trắng hoặc NaN bằng giá trị của dòng phía trên
    if 'Ngày Xác nhận' in df.columns:
        df['Ngày Xác nhận'] = df['Ngày Xác nhận'].replace(r'^\s*$', pd.NA, regex=True).ffill()
    
    # Hàm hỗ trợ làm sạch giá tiền
    def clean_price(val):
        try:
            if not val or pd.isna(val): return 0
            return float(str(val).replace(',', ''))
        except: return 0

    for i, r in df.iterrows():
        # Khởi tạo giá trị rỗng để tránh lỗi "not defined"
        machine_id = None 
        case_id = None
        m_code = str(r.get("Mã số máy", "")).strip()
        
        if not m_code or m_code.lower() == "nan":
            continue
        
        try:
            # --- BƯỚC 1: UPSERT MACHINE ---
            m_res = supabase.table("machines").upsert({
                "machine_code": m_code,
                "region": str(r.get("Chi Nhánh", "Chưa xác định"))
            }, on_conflict="machine_code").execute()
            
            if m_res.data:
                machine_id = m_res.data[0]["id"]
            else:
                continue # Nếu không lấy được machine_id thì bỏ qua dòng này

            # --- BƯỚC 2: CHUẨN HÓA NGÀY THÁNG & TẠO CASE ---
            confirmed_val = str(r.get("Ngày Xác nhận", "")).strip()
            formatted_date = None
            if confirmed_val and confirmed_val.lower() != "nan":
                try:
                    formatted_date = pd.to_datetime(confirmed_val, dayfirst=True).strftime('%Y-%m-%d')
                except:
                    formatted_date = None

            case_payload = {
                "machine_id": machine_id, # Đảm bảo biến đã được định nghĩa ở trên
                "branch": str(r.get("Chi Nhánh", "Chưa xác định")),
                "customer_name": str(r.get("Tên KH", "")),
                "issue_reason": str(r.get("Lý Do", "")),
                "confirmed_date": formatted_date
            }
            c_res = supabase.table("repair_cases").insert(case_payload).execute()
            
            if c_res.data:
                case_id = c_res.data[0]["id"]

                # --- BƯỚC 3: ĐẨY CHI PHÍ ---
                actual_cost = clean_price(r.get("Chi Phí Thực Tế", 0))
                supabase.table("repair_costs").insert({
                    "repair_case_id": case_id,
                    "estimated_cost": clean_price(r.get("Chi Phí Dự Kiến", 0)),
                    "actual_cost": actual_cost,
                    "confirmed_by": str(r.get("Người Kiểm Tra", ""))
                }).execute()

                # --- BƯỚC 4: QUY TRÌNH ---
                supabase.table("repair_process").insert({
                    "repair_case_id": case_id,
                    "state": "DONE" if actual_cost > 0 else "PENDING",
                    "handled_by": str(r.get("Người Kiểm Tra", ""))
                }).execute()

                success_count += 1
            
        except Exception as e:
            st.error(f"❌ Lỗi tại dòng {i+1} (Mã máy {m_code}): {str(e)}")
        
        progress_bar.progress((i + 1) / len(df))
            
    return success_count

# --- 4. GIAO DIỆN CHÍNH ---
def main():
    # SIDEBAR
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/d/d0/Logo_4Oranges.png", width=150)
        st.title("🎨 4ORANGES OPS")
        if st.button('🔄 REFRESH DATABASE', type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        df_db = load_data_from_db()
        current_year = datetime.datetime.now().year
        
        list_years = sorted(df_db['NĂM'].unique().tolist(), reverse=True) if not df_db.empty else [current_year]
        sel_year = st.selectbox("📅 Chọn Năm", list_years)
        
        list_months = ["Tất cả"] + sorted(df_db[df_db['NĂM'] == sel_year]['THÁNG'].unique().tolist()) if not df_db.empty else ["Tất cả"]
        sel_month = st.selectbox("📆 Chọn Tháng", list_months)

    tabs = st.tabs(["📊 XU HƯỚNG", "💰 CHI PHÍ", "📥 NHẬP DỮ LIỆU"])

    with tabs[0]:
        df_db = load_data_from_db()
        
        if df_db.empty:
            st.info("👋 Chào sếp! Hiện tại hệ thống chưa có dữ liệu. Sếp hãy nhập dữ liệu ở tab **NHẬP DỮ LIỆU** nhé.")
        else:
            # 1. Lọc dữ liệu theo Sidebar (Năm/Tháng)
            df_view = df_db[df_db['NĂM'] == sel_year].copy()
            if sel_month != "Tất cả":
                df_view = df_view[df_view['THÁNG'] == sel_month]
            
            if df_view.empty:
                st.warning(f"⚠️ Không có dữ liệu sự vụ nào trong tháng {sel_month} năm {sel_year}.")
            else:
                # --- 2. KPI CHIẾN LƯỢC ---
                k1, k2, k3 = st.columns(3)
                # Tính toán an toàn với .sum() và .mean()
                total_cost = df_view['CHI_PHÍ_THỰC'].sum()
                avg_cost = df_view['CHI_PHÍ_THỰC'].mean()
                
                k1.metric("💰 TỔNG CHI PHÍ", f"{total_cost:,.0f} đ")
                k2.metric("📋 TỔNG SỰ VỤ", f"{len(df_view)} ca")
                k3.metric("📈 TRUNG BÌNH/CA", f"{avg_cost:,.0f} đ")

                st.divider()

                # --- 3. BIỂU ĐỒ TRỰC QUAN ---
                c1, c2 = st.columns(2)
                with c1:
                    # Top 10 lý do hỏng
                    if 'issue_reason' in df_view.columns:
                        issue_counts = df_view['issue_reason'].value_counts().reset_index().head(10)
                        issue_counts.columns = ['Lý do', 'Số lượng']
                        fig_issue = px.bar(issue_counts, x='Số lượng', y='Lý do', orientation='h', 
                                          title="TOP 10 LÝ DO HỎNG PHỔ BIẾN",
                                          color_discrete_sequence=[ORANGE_COLORS[0]])
                        st.plotly_chart(fig_issue, use_container_width=True)
                
                with c2:
                    # Chi phí theo vùng
                    if 'VÙNG' in df_view.columns:
                        fig_pie = px.pie(df_view, names='VÙNG', values='CHI_PHÍ_THỰC', 
                                        title="CƠ CẤU CHI PHÍ THEO VÙNG", hole=0.4,
                                        color_discrete_sequence=ORANGE_COLORS)
                        st.plotly_chart(fig_pie, use_container_width=True)

                # --- 4. BẢNG CHI TIẾT (BIỆN PHÁP MẠNH - KHÔNG LỖI) ---
                st.subheader("📋 DANH SÁCH CHI TIẾT")
                
                # Danh sách cột sếp muốn thấy trên màn hình
                actual_cols = ['MÃ_MÁY', 'customer_name', 'issue_reason', 'VÙNG', 'NGÀY_HIỂN_THỊ', 'CHI_PHÍ_THỰC']
                
                # Lọc ra những cột thực sự đang tồn tại trong dữ liệu
                safe_cols = [c for c in actual_cols if c in df_view.columns]
                
                if not safe_cols:
                    st.error("❌ Không tìm thấy các cột dữ liệu cần thiết để hiển thị bảng.")
                else:
                    # Xác định cột dùng để sắp xếp (Ưu tiên cột gốc confirmed_date)
                    sort_col = 'confirmed_date' if 'confirmed_date' in df_view.columns else safe_cols[0]
                    
                    # LOGIC THEN CHỐT: Sắp xếp trên bảng lớn trước, sau đó mới cắt lấy safe_cols để hiện
                    df_display = df_view.sort_values(by=sort_col, ascending=False)[safe_cols]
                    
                    st.dataframe(
                        df_display, 
                        use_container_width=True, 
                        hide_index=True
                    )
                
                st.caption(f"💡 Dữ liệu đã được đồng bộ từ Supabase. Đang hiển thị {len(df_display)} dòng.")

    with tabs[2]:
        st.subheader("📥 NHẬP DỮ LIỆU GOOGLE SHEET")
        up = st.file_uploader("Chọn file CSV", type="csv")
        if up:
            df_up = pd.read_csv(up).fillna("")
            if st.button("🚀 ĐỒNG BỘ NGAY"):
                with st.spinner("Đang xử lý..."):
                    count = import_to_enterprise_schema(df_up)
                    if count > 0:
                        st.balloons()
                        st.success(f"Thành công {count} ca!")
                        st.cache_data.clear()

if __name__ == "__main__":
    main()
