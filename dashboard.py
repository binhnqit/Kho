import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import time
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

# --- 2. HÀM TẢI DỮ LIỆU TỪ DATABASE (QUAN TRỌNG NHẤT) ---
@st.cache_data(ttl=60)
def load_data_from_db():
    try:
        # Lấy dữ liệu JOIN từ các bảng
        res = supabase.table("repair_cases").select(
            "*, machines(machine_code, region), repair_costs(actual_cost)"
        ).execute()
        
        if not res.data:
            return pd.DataFrame()
            
        df = pd.json_normalize(res.data)
        
        # Mapping tên cột từ Database về UI
        mapping = {
            "machines.machine_code": "MÃ_MÁY",
            "repair_costs.actual_cost": "CHI_PHÍ_THỰC",
            "branch": "VÙNG"
        }
        df = df.rename(columns=mapping)

        # Đảm bảo các cột số liệu không bị rỗng (NaN)
        if 'CHI_PHÍ_THỰC' in df.columns:
            df['CHI_PHÍ_THỰC'] = pd.to_numeric(df['CHI_PHÍ_THỰC'], errors='coerce').fillna(0)

        # Xử lý thời gian chuẩn xác
        if 'confirmed_date' in df.columns:
            df['confirmed_date'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
            # Lọc bỏ dòng không có ngày hợp lệ
            df = df.dropna(subset=['confirmed_date'])
            df['NĂM'] = df['confirmed_date'].dt.year.astype(int)
            df['THÁNG'] = df['confirmed_date'].dt.month.astype(int)
            df['NGÀY_HIỂN_THỊ'] = df['confirmed_date'].dt.strftime('%d/%m/%Y')
        
        return df
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu từ DB: {e}")
        return pd.DataFrame()
    # Thêm đoạn này vào cuối hàm load_data_from_db trước khi return df
        if not df.empty:
            if 'CHI_PHÍ_THỰC' not in df.columns:
                df['CHI_PHÍ_THỰC'] = 0
            else:
                df['CHI_PHÍ_THỰC'] = pd.to_numeric(df['CHI_PHÍ_THỰC'], errors='coerce').fillna(0)
# --- 3. HÀM IMPORT DỮ LIỆU (BẢN CHỐNG NGHẼN & ĐIỀN TRỐNG) ---
def import_to_enterprise_schema(df):
    success_count = 0
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 1. Forward Fill: Điền ngày trống bằng ngày của dòng phía trên
    if 'Ngày Xác nhận' in df.columns:
        df['Ngày Xác nhận'] = df['Ngày Xác nhận'].replace(r'^\s*$', pd.NA, regex=True).ffill()
    
    def clean_price(val):
        try:
            if not val or pd.isna(val): return 0
            return float(str(val).replace(',', ''))
        except: return 0

    total_rows = len(df)
    
    for i, r in df.iterrows():
        m_code = str(r.get("Mã số máy", "")).strip()
        if not m_code or m_code.lower() == "nan": continue
        
        try:
            # Bước 1: Upsert Machine
            m_res = supabase.table("machines").upsert({
                "machine_code": m_code,
                "region": str(r.get("Chi Nhánh", "Chưa xác định"))
            }, on_conflict="machine_code").execute()
            
            if not m_res.data: continue
            machine_id = m_res.data[0]["id"]

            # Bước 2: Chuẩn hóa ngày
            confirmed_val = str(r.get("Ngày Xác nhận", "")).strip()
            formatted_date = None
            if confirmed_val and confirmed_val.lower() != "nan":
                try:
                    formatted_date = pd.to_datetime(confirmed_val, dayfirst=True).strftime('%Y-%m-%d')
                except: formatted_date = None

            # Bước 3: Insert Case
            c_res = supabase.table("repair_cases").insert({
                "machine_id": machine_id,
                "branch": str(r.get("Chi Nhánh", "Chưa xác định")),
                "customer_name": str(r.get("Tên KH", "")),
                "issue_reason": str(r.get("Lý Do", "")),
                "confirmed_date": formatted_date
            }).execute()
            
            if c_res.data:
                case_id = c_res.data[0]["id"]
                actual_cost = clean_price(r.get("Chi Phí Thực Tế", 0))

                # Bước 4: Insert Cost & Process
                supabase.table("repair_costs").insert({
                    "repair_case_id": case_id,
                    "estimated_cost": clean_price(r.get("Chi Phí Dự Kiến", 0)),
                    "actual_cost": actual_cost,
                    "confirmed_by": str(r.get("Người Kiểm Tra", ""))
                }).execute()

                supabase.table("repair_process").insert({
                    "repair_case_id": case_id,
                    "state": "DONE" if actual_cost > 0 else "PENDING",
                    "handled_by": str(r.get("Người Kiểm Tra", ""))
                }).execute()

                success_count += 1
            
        except Exception as e:
            status_text.warning(f"⚠️ Dòng {i+1} lỗi: {str(e)}")
        
        # Chống nghẽn Session (Cập nhật 5 dòng/lần)
        if i % 5 == 0 or i == total_rows - 1:
            progress_bar.progress((i + 1) / total_rows)
            status_text.text(f"⏳ Đang xử lý: {i+1}/{total_rows}...")
            
    status_text.success(f"✅ Đã đồng bộ thành công {success_count} sự vụ!")
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

        # Load dữ liệu để lấy danh sách Năm/Tháng
        df_db = load_data_from_db()
        current_year = datetime.datetime.now().year
        
        if not df_db.empty:
            list_years = sorted(df_db['NĂM'].unique().tolist(), reverse=True)
            sel_year = st.selectbox("📅 Chọn Năm", list_years)
            
            list_months = ["Tất cả"] + sorted(df_db[df_db['NĂM'] == sel_year]['THÁNG'].unique().tolist())
            sel_month = st.selectbox("📆 Chọn Tháng", list_months)
        else:
            sel_year = current_year
            sel_month = "Tất cả"
            st.info("Chưa có dữ liệu để lọc.")

    tabs = st.tabs(["📊 XU HƯỚNG", "💰 CHI PHÍ", "📥 NHẬP DỮ LIỆU"])

    with tabs[0]:
        if df_db.empty:
            st.info("👋 Chào sếp! Hiện tại hệ thống chưa có dữ liệu. Sếp hãy nhập dữ liệu ở tab **NHẬP DỮ LIỆU** nhé.")
        else:
            df_view = df_db[df_db['NĂM'] == sel_year].copy()
            if sel_month != "Tất cả":
                df_view = df_view[df_view['THÁNG'] == sel_month]
            
            if df_view.empty:
                st.warning(f"⚠️ Không có dữ liệu trong tháng {sel_month} năm {sel_year}.")
            else:
                # --- 2. KPI CHIẾN LƯỢC (BẢN CHỐNG LỖI KEYERROR) ---
                k1, k2, k3 = st.columns(3)
                
                # Kiểm tra xem cột có tồn tại và có dữ liệu không
                if 'CHI_PHÍ_THỰC' in df_view.columns:
                    total_cost = df_view['CHI_PHÍ_THỰC'].sum()
                    avg_cost = df_view['CHI_PHÍ_THỰC'].mean()
                else:
                    total_cost = 0
                    avg_cost = 0
                
                k1.metric("💰 TỔNG CHI PHÍ", f"{total_cost:,.0f} đ")
                k2.metric("📋 TỔNG SỰ VỤ", f"{len(df_view)} ca")
                k3.metric("📈 TRUNG BÌNH/CA", f"{avg_cost:,.0f} đ")

                st.divider()

                # Biểu đồ
                # --- 3. BIỂU ĐỒ TRỰC QUAN (BẢN CHỐNG CRASH) ---
                c1, c2 = st.columns(2)
                
                with c1:
                    # Top 10 lý do hỏng
                    if 'issue_reason' in df_view.columns and not df_view['issue_reason'].empty:
                        issue_counts = df_view['issue_reason'].value_counts().reset_index().head(10)
                        issue_counts.columns = ['Lý do', 'Số lượng']
                        fig_issue = px.bar(issue_counts, x='Số lượng', y='Lý do', orientation='h', 
                                          title="TOP 10 LÝ DO HỎNG PHỔ BIẾN",
                                          color_discrete_sequence=[ORANGE_COLORS[0]])
                        st.plotly_chart(fig_issue, use_container_width=True)
                    else:
                        st.info("Chưa có dữ liệu lý do hỏng.")
                
                with c2:
                    # Chi phí theo vùng - KIỂM TRA ĐIỀU KIỆN VẼ
                    can_plot_pie = (
                        'VÙNG' in df_view.columns and 
                        'CHI_PHÍ_THỰC' in df_view.columns and 
                        df_view['CHI_PHÍ_THỰC'].sum() > 0
                    )
                    
                    if can_plot_pie:
                        fig_pie = px.pie(df_view, names='VÙNG', values='CHI_PHÍ_THỰC', 
                                        title="CƠ CẤU CHI PHÍ THEO VÙNG", hole=0.4,
                                        color_discrete_sequence=ORANGE_COLORS)
                        st.plotly_chart(fig_pie, use_container_width=True)
                    else:
                        # Thay vì báo lỗi đỏ, ta hiện thông báo nhẹ nhàng
                        st.info("💡 Không có dữ liệu chi phí để hiển thị biểu đồ tròn.")

                # Bảng chi tiết
                st.subheader("📋 DANH SÁCH CHI TIẾT")
                actual_cols = ['MÃ_MÁY', 'customer_name', 'issue_reason', 'VÙNG', 'NGÀY_HIỂN_THỊ', 'CHI_PHÍ_THỰC']
                safe_cols = [c for c in actual_cols if c in df_view.columns]
                
                if safe_cols:
                    sort_col = 'confirmed_date' if 'confirmed_date' in df_view.columns else safe_cols[0]
                    df_display = df_view.sort_values(by=sort_col, ascending=False)[safe_cols]
                    st.dataframe(df_display, use_container_width=True, hide_index=True)

    with tabs[2]:
        st.subheader("📥 NHẬP DỮ LIỆU GOOGLE SHEET (CSV)")
        up = st.file_uploader("Chọn file CSV đã xuất từ Google Sheet", type="csv")
        if up:
            df_up = pd.read_csv(up).fillna("")
            st.write("🔍 Xem trước dữ liệu:", df_up.head(3))
            if st.button("🚀 ĐỒNG BỘ NGAY"):
                with st.status("Đang đẩy dữ liệu lên hệ thống...", expanded=True) as status:
                    count = import_to_enterprise_schema(df_up)
                    status.update(label=f"Đã đồng bộ xong {count} ca!", state="complete", expanded=False)
                st.balloons()
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()

if __name__ == "__main__":
    main()
