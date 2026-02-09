import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from supabase import create_client

# --- 1. CẤU HÌNH & KẾT NỐI ---
st.set_page_config(page_title="4ORANGES - REPAIR OPS", layout="wide", page_icon="🎨")

# Màu sắc thương hiệu 4Oranges
ORANGE_COLORS = ["#FF8C00", "#FFA500", "#FF4500", "#E67E22", "#D35400"]

# Kết nối Supabase
SUPABASE_URL = "https://cigbnbaanpebwrufzxfg.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_NQzqwJ4YhKC4sQGLxyLAyw_mwRFhkRf")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. HÀM FETCH DỮ LIỆU (CHÍNH XÁC THEO SCHEMA SẾP GỬI) ---
@st.cache_data(ttl=60)
def fetch_repair_cases():
    try:
        # Sử dụng đúng cột compensation đã tồn tại trong DB của sếp
        res = supabase.table("repair_cases") \
            .select("id, machine_id, branch, confirmed_date, issue_reason, customer_name, compensation") \
            .order("confirmed_date", desc=True) \
            .limit(4000) \
            .execute()
        return res.data
    except Exception as e:
        st.error(f"❌ Lỗi Fetch Database: {e}")
        return None

def load_data_from_db():
    data = fetch_repair_cases()
    if not data: 
        return pd.DataFrame()
    
    df = pd.DataFrame(data)
    
    # Xử lý ngày tháng chuyên sâu
    if 'confirmed_date' in df.columns:
        df['confirmed_date'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        # Bỏ dòng lỗi ngày để Dashboard không crash
        df = df.dropna(subset=['confirmed_date'])
        
        df['NĂM'] = df['confirmed_date'].dt.year.astype(int)
        df['THÁNG'] = df['confirmed_date'].dt.month.astype(int)
        df['NGÀY_HIỂN_THỊ'] = df['confirmed_date'].dt.strftime('%d/%m/%Y')
    
    # Đổi tên cột từ Database sang Tiếng Việt hiển thị UI
    # compensation -> CHI_PHÍ_THỰC
    df = df.rename(columns={
        'branch': 'VÙNG', 
        'compensation': 'CHI_PHÍ_THỰC',
        'customer_name': 'TÊN KHÁCH HÀNG',
        'issue_reason': 'LÝ DO HỎNG'
    })
    
    # Đảm bảo CHI_PHÍ_THỰC luôn là số để tính toán
    df['CHI_PHÍ_THỰC'] = pd.to_numeric(df['CHI_PHÍ_THỰC'], errors='coerce').fillna(0)
    
    return df

# --- 3. HÀM IMPORT DỮ LIỆU (CƠ CHẾ PHÒNG THỦ CAO) ---
def import_to_enterprise_schema(df_chunk):
    success_count = 0
    for _, r in df_chunk.iterrows():
        try:
            # Làm sạch dữ liệu đầu vào
            m_code = str(r.get("Mã số máy", "")).strip()
            if not m_code or m_code.lower() in ["nan", "none", ""]: 
                continue

            # BƯỚC 1: Xử lý bảng Machines (Upsert để lấy ID)
            m_res = supabase.table("machines").upsert({
                "machine_code": m_code,
                "region": str(r.get("Chi Nhánh", "Chưa xác định"))
            }, on_conflict="machine_code").execute()
            
            if not m_res.data: continue
            machine_id = m_res.data[0]["id"]

            # BƯỚC 2: Định dạng ngày (Fix lỗi định dạng Excel Việt Nam)
            confirmed_val = str(r.get("Ngày Xác nhận", "")).strip()
            formatted_date = None
            if confirmed_val and confirmed_val.lower() not in ["nan", "none", ""]:
                try:
                    formatted_date = pd.to_datetime(confirmed_val, dayfirst=True).strftime('%Y-%m-%d')
                except: pass

            # BƯỚC 3: Xử lý tiền tệ (Xóa dấu phẩy phân tách nghìn)
            cost_raw = str(r.get("Chi Phí Thực Tế", "0")).replace(",", "").replace(".", "").strip()
            try:
                val_compensation = float(cost_raw)
            except:
                val_compensation = 0

            # BƯỚC 4: Đẩy vào bảng repair_cases (Dùng chuẩn cột compensation)
            supabase.table("repair_cases").insert({
                "machine_id": machine_id,
                "branch": str(r.get("Chi Nhánh", "Chưa xác định")),
                "issue_reason": str(r.get("Lý Do", "")),
                "customer_name": str(r.get("Tên KH", "")),
                "confirmed_date": formatted_date,
                "compensation": val_compensation
            }).execute()
            
            success_count += 1
        except Exception as e:
            st.error(f"⚠️ Lỗi tại máy {m_code}: {e}")
            continue
    return success_count

# --- 4. GIAO DIỆN CHÍNH (ENTERPRISE UI) ---
def main():
    # Sidebar
    with st.sidebar:
        st.image("https://4oranges.com/assets/img/logo.png", width=200) # Thêm logo cho chuyên nghiệp
        st.title("🎨 OPS DASHBOARD")
        st.divider()
        
        if st.button('🔄 LÀM MỚI DỮ LIỆU', type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
            
        df_db = load_data_from_db()
        
        if not df_db.empty:
            st.success(f"📡 Đã tải {len(df_db)} dòng dữ liệu")
            # Bộ lọc Năm/Tháng
            years = sorted(df_db['NĂM'].unique(), reverse=True)
            sel_year = st.selectbox("📅 Chọn Năm", years)
            
            months = ["Tất cả"] + sorted(df_db[df_db['NĂM'] == sel_year]['THÁNG'].unique().tolist())
            sel_month = st.selectbox("📆 Chọn Tháng", months)
        else:
            st.warning("⚠️ Database hiện đang trống")

    # Tabs chính
    tabs = st.tabs(["📊 PHÂN TÍCH XU HƯỚNG", "📥 NẠP DỮ LIỆU HỆ THỐNG"])

    # --- TAB 0: DASHBOARD ---
    # --- TAB 0: DASHBOARD PHÂN TÍCH CHUYÊN SÂU ---
    with tabs[0]:
        if df_db.empty:
            st.info("💡 Chào sếp! Hiện chưa có dữ liệu. Vui lòng qua tab **NẠP DỮ LIỆU** để bắt đầu.")
        else:
            # 1. LỌC DỮ LIỆU THEO BỘ LỌC SIDEBAR
            df_view = df_db[df_db['NĂM'] == sel_year].copy()
            if sel_month != "Tất cả":
                df_view = df_view[df_view['THÁNG'] == sel_month]
            
            # 2. KPI HEADER (Nâng cấp)
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("💰 TỔNG CHI PHÍ", f"{df_view['CHI_PHÍ_THỰC'].sum():,.0f} đ")
            with c2:
                avg_cost = df_view['CHI_PHÍ_THỰC'].mean() if not df_view.empty else 0
                st.metric("💸 TB/SỰ VỤ", f"{avg_cost:,.0f} đ")
            with c3:
                st.metric("📋 TỔNG SỰ VỤ", f"{len(df_view)} ca")
            with c4:
                top_branch = df_view['VÙNG'].mode()[0] if not df_view.empty else "N/A"
                st.metric("🚩 VÙNG NÓNG NHẤT", top_branch)

            st.divider()
            
            # 3. PHÂN TÍCH CHI TIẾT
            row1_col1, row1_col2 = st.columns([6, 4])
            
            with row1_col1:
                # Biểu đồ xu hướng theo thời gian (Nếu xem theo năm)
                if sel_month == "Tất cả":
                    trend_data = df_view.groupby('THÁNG').agg({'CHI_PHÍ_THỰC': 'sum', 'id': 'count'}).reset_index()
                    fig_trend = px.line(trend_data, x='THÁNG', y='CHI_PHÍ_THỰC', 
                                      title="📉 XU HƯỚNG CHI PHÍ THEO THÁNG",
                                      markers=True, line_shape="spline",
                                      color_discrete_sequence=['#FF4500'])
                    st.plotly_chart(fig_trend, use_container_width=True)
                else:
                    # Nếu xem theo tháng, hiện Top máy hỏng nhiều nhất tháng đó
                    machine_fail = df_view.groupby('machine_id').size().reset_index(name='Số lần hỏng')
                    machine_fail = machine_fail.sort_values('Số lần hỏng', ascending=False).head(10)
                    fig_fail = px.bar(machine_fail, x='machine_id', y='Số lần hỏng', 
                                    title="🔧 TOP 10 MÁY HỎNG NHIỀU NHẤT",
                                    color='Số lần hỏng', color_continuous_scale='Oranges')
                    st.plotly_chart(fig_fail, use_container_width=True)

            with row1_col2:
                # Phân tích cơ cấu lý do hỏng (Treemap nhìn cho pro)
                reason_data = df_view['LÝ DO HỎNG'].value_counts().reset_index()
                fig_tree = px.treemap(reason_data, path=['LÝ DO HỎNG'], values='count',
                                    title="🌳 PHÂN TÍCH LÝ DO HỎNG (TỶ TRỌNG)",
                                    color_discrete_sequence=ORANGE_COLORS)
                st.plotly_chart(fig_tree, use_container_width=True)

            # 4. PHÂN TÍCH ĐỊA PHƯƠNG & KHÁCH HÀNG
            st.divider()
            row2_col1, row2_col2 = st.columns(2)
            
            with row2_col1:
                # Top Khách hàng chi đậm nhất
                cust_cost = df_view.groupby('TÊN KHÁCH HÀNG')['CHI_PHÍ_THỰC'].sum().reset_index()
                cust_cost = cust_cost.sort_values('CHI_PHÍ_THỰC', ascending=False).head(5)
                fig_cust = px.bar(cust_cost, x='CHI_PHÍ_THỰC', y='TÊN KHÁCH HÀNG', orientation='h',
                                title="🏆 TOP 5 KHÁCH HÀNG CHI PHÍ CAO NHẤT",
                                color_discrete_sequence=['#E67E22'])
                st.plotly_chart(fig_cust, use_container_width=True)

            with row2_col2:
                # Bảng so sánh hiệu quả giữa các chi nhánh
                branch_perf = df_view.groupby('VÙNG').agg({
                    'id': 'count',
                    'CHI_PHÍ_THỰC': 'sum'
                }).rename(columns={'id': 'Số ca', 'CHI_PHÍ_THỰC': 'Tổng chi'}).reset_index()
                st.write("🏢 **HIỆU SUẤT THEO CHI NHÁNH**")
                st.dataframe(branch_perf.style.background_gradient(cmap='Oranges'), use_container_width=True)

            # 5. DỮ LIỆU GỐC
            with st.expander("🔍 XEM TOÀN BỘ DANH SÁCH CHI TIẾT"):
                st.dataframe(df_view.sort_values('confirmed_date', ascending=False), use_container_width=True)

    # --- TAB 1: NHẬP DỮ LIỆU ---
    with tabs[1]:
        st.subheader("📥 CẬP NHẬT DỮ LIỆU TỪ FILE CSV")
        st.info("Lưu ý: File CSV cần xuất từ Google Sheet với các cột: Mã số máy, Chi Nhánh, Ngày Xác nhận, Lý Do, Tên KH, Chi Phí Thực Tế.")
        
        up = st.file_uploader("Kéo thả file CSV vào đây", type="csv")
        
        if up:
            # Đọc và xử lý ô gộp (ffill) ngay khi load
            df_up = pd.read_csv(up, encoding='utf-8-sig').fillna("")
            df_up.columns = [c.strip() for c in df_up.columns] # Xóa khoảng trắng tên cột
            
            # Tự động điền dữ liệu trống cho các cột quan trọng (ffill)
            for col in ['Ngày Xác nhận', 'Chi Nhánh', 'Mã số máy']:
                if col in df_up.columns:
                    df_up[col] = df_up[col].replace("", None).ffill()
            
            st.write("🔍 **Xem trước dữ liệu sẽ nạp:**")
            st.dataframe(df_up.head(5), use_container_width=True)
            
            if st.button("🚀 XÁC NHẬN ĐỒNG BỘ LÊN CLOUD", type="primary", use_container_width=True):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Chia nhỏ để nạp (Tránh timeout Supabase)
                chunk_size = 50
                total = len(df_up)
                success_total = 0
                
                for i in range(0, total, chunk_size):
                    chunk = df_up.iloc[i : i + chunk_size]
                    count = import_to_enterprise_schema(chunk)
                    success_total += count
                    
                    # Cập nhật tiến độ
                    percent = min((i + chunk_size) / total, 1.0)
                    progress_bar.progress(percent)
                    status_text.text(f"⏳ Đang xử lý: {success_total}/{total} dòng...")
                
                st.success(f"✅ Đã nạp thành công {success_total}/{total} dòng dữ liệu!")
                st.cache_data.clear() # Quan trọng: Xóa cache để dashboard thấy data mới ngay
                st.balloons()

if __name__ == "__main__":
    main()
