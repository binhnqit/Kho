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
@st.cache_data(ttl=60)
@st.cache_data(ttl=300) # Lưu bộ nhớ đệm trong 5 phút
def load_data_from_db():
    try:
        # Lấy tối đa 5000 dòng để bao phủ toàn bộ 800+ dòng mới
        res = supabase.table("repair_cases").select(
            "*, machines(machine_code, region), repair_costs(actual_cost)"
        ).limit(5000).execute()
        
        if not res.data:
            return pd.DataFrame()
            
        df = pd.json_normalize(res.data)
        
        # Đổi tên cột chuẩn để Dashboard nhận diện
        mapping = {
            "machines.machine_code": "MÃ_MÁY",
            "repair_costs.actual_cost": "CHI_PHÍ_THỰC",
            "branch": "VÙNG"
        }
        df = df.rename(columns=mapping)

        # Xử lý ngày tháng - ĐẢM BẢO LẤY ĐƯỢC NĂM 2025
        if 'confirmed_date' in df.columns:
            df['confirmed_date'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
            
            # Nếu ngày bị trống (do file gốc có khoảng trắng), tạm để ngày hiện tại để không mất dòng dữ liệu
            df['confirmed_date'] = df['confirmed_date'].fillna(pd.Timestamp.now())
            
            df['NĂM'] = df['confirmed_date'].dt.year.astype(int)
            df['THÁNG'] = df['confirmed_date'].dt.month.astype(int)
            df['NGÀY_HIỂN_THỊ'] = df['confirmed_date'].dt.strftime('%d/%m/%Y')
            
        return df
    except Exception as e:
        st.error(f"Lỗi kết nối database: {e}")
        return pd.DataFrame()
# --- 3. HÀM IMPORT DỮ LIỆU (BẢN CHỐNG NGHẼN & ĐIỀN TRỐNG) ---
def import_to_enterprise_schema(df):
    success_count = 0
    # --- 💎 ĐIỀN NGÀY TRỐNG TRƯỚC KHI CHẠY VÒNG LẶP ---
    if 'Ngày Xác nhận' in df.columns:
        df['Ngày Xác nhận'] = df['Ngày Xác nhận'].astype(str).str.strip()
        # Biến các ô trông có vẻ trống thành NA thật sự
        df['Ngày Xác nhận'] = df['Ngày Xác nhận'].replace(['', 'nan', 'NaN', 'None'], pd.NA)
        # Điền ngày từ dòng trên xuống cho đến khi gặp ngày mới
        df['Ngày Xác nhận'] = df['Ngày Xác nhận'].ffill()
    
    # ... (Các phần clean_price giữ nguyên) ...

    for i, r in df.iterrows():
        # ... (Phần lấy machine_id giữ nguyên) ...
        
        # Lấy ngày đã được ffill
        confirmed_val = str(r.get("Ngày Xác nhận", "")).strip()
        formatted_date = None
        if confirmed_val and confirmed_val.lower() != "nan":
            try:
                # Ép kiểu d/m/Y về Y-m-d để lưu vào Supabase
                formatted_date = pd.to_datetime(confirmed_val, dayfirst=True).strftime('%Y-%m-%d')
            except: formatted_date = None

        # Insert vào repair_cases
        supabase.table("repair_cases").insert({
            "machine_id": machine_id,
            "branch": str(r.get("Chi Nhánh", "Chưa xác định")),
            "confirmed_date": formatted_date # Lưu ngày đã xử lý
            # ... các trường khác ...
        }).execute()
        # ...
    # Hàm dọn dẹp giá tiền (Xử lý dấu phẩy)
    def clean_price(val):
        try:
            if not val or pd.isna(val): return 0
            return float(str(val).replace(',', ''))
        except: return 0

    total_rows = len(df)
    # Duyệt qua từng dòng đã được lấp đầy ngày tháng
    for i, r in df.iterrows():
        m_code = str(r.get("Mã số máy", "")).strip()
        if not m_code or m_code.lower() in ["nan", "mã số máy"]: continue
        
        try:
            # 1. Upsert Machine (Cần RLS Policy Insert/Update)
            m_res = supabase.table("machines").upsert({
                "machine_code": m_code,
                "region": str(r.get("Chi Nhánh", "Chưa xác định"))
            }, on_conflict="machine_code").execute()
            
            if not m_res.data: continue
            machine_id = m_res.data[0]["id"]

            # 2. Lấy ngày (Bây giờ chắc chắn không còn rỗng nhờ ffill ở trên)
            confirmed_val = str(r.get("Ngày Xác nhận", "")).strip()
            formatted_date = None
            if confirmed_val and confirmed_val != "None":
                try:
                    formatted_date = pd.to_datetime(confirmed_val, dayfirst=True).strftime('%Y-%m-%d')
                except: formatted_date = None

            # 3. Insert Case & Cost (Logic giữ nguyên)
            # ... (Phần code insert repair_cases, repair_costs giống bản trước) ...

            success_count += 1
            if i % 20 == 0:
                status_text.text(f"⏳ Đang xử lý: {i+1}/{total_rows} dòng...")
        
        except Exception as e:
            st.warning(f"Dòng {i} gặp lỗi: {e}")
            continue
            
    return success_count

# --- 4. GIAO DIỆN CHÍNH ---
def clean_excel_data(df):
    # 1. Bộ giải mã lỗi font từ Excel/Google Sheet CSV
    # Quét tất cả các cột hiện có, nếu cột nào chứa ký tự lạ thì đổi tên về chuẩn
    standard_names = {
        'Ngày Xác nhận': ['NgÃ y XÃ¡c nhÃ¢n', 'Ngay Xac nhan', 'Ngày xác nhận'],
        'Tên KH': ['TÃªn KH', 'Ten KH'],
        'Lý Do': ['LÃ½ Do', 'Ly Do'],
        'Chi Nhánh': ['Chi NhÃ¡nh', 'Chi nhanh'],
        'Chi Phí Thực Tế': ['Chi PhÃ­ Thá»±c Táº¿', 'Chi phi thuc te'],
        'Mã số máy': ['MÃ£ sá»‘ mÃ¡y', 'Ma so may']
    }
    
    for real_name, aliases in standard_names.items():
        for alias in aliases:
            if alias in df.columns:
                df = df.rename(columns={alias: real_name})

    # 2. Xử lý "Ngày Xác nhận" và Fill rỗng
    if 'Ngày Xác nhận' in df.columns:
        df['Ngày Xác nhận'] = df['Ngày Xác nhận'].astype(str).str.strip()
        # Thay thế mọi giá trị rỗng hoặc rác thành NA thực sự
        df['Ngày Xác nhận'] = df['Ngày Xác nhận'].replace(['', 'nan', 'NaN', 'None', 'None'], pd.NA)
        # Nếu dòng nào quá ngắn (không phải ngày) thì cũng xóa để fill
        df.loc[df['Ngày Xác nhận'].str.len() < 5, 'Ngày Xác nhận'] = pd.NA
        # Tiến hành điền ngày từ dòng trên xuống
        df['Ngày Xác nhận'] = df['Ngày Xác nhận'].ffill()
        
         
    return df
def main():
    # SIDEBAR
    with st.sidebar:
        
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
        # Kiểm tra nếu dữ liệu trống
        if df_db.empty:
            st.info("👋 Chào sếp! Hiện tại hệ thống chưa có dữ liệu hoặc đang tải. Sếp hãy kiểm tra lại kết nối hoặc nhập dữ liệu nhé.")
        else:
            # 1. Lọc dữ liệu theo Sidebar (Năm/Tháng)
            df_view = df_db[df_db['NĂM'] == sel_year].copy()
            if sel_month != "Tất cả":
                df_view = df_view[df_view['THÁNG'] == sel_month]
            
            if df_view.empty:
                st.warning(f"⚠️ Không có dữ liệu trong tháng {sel_month} năm {sel_year}.")
            else:
                # --- 2. KPI CHIẾN LƯỢC ---
                k1, k2, k3 = st.columns(3)
                
                # Tính toán các chỉ số an toàn
                total_cost = df_view['CHI_PHÍ_THỰC'].sum() if 'CHI_PHÍ_THỰC' in df_view.columns else 0
                total_cases = len(df_view)
                avg_cost = total_cost / total_cases if total_cases > 0 else 0
                
                k1.metric("💰 TỔNG CHI PHÍ", f"{total_cost:,.0f} đ")
                k2.metric("📋 TỔNG SỰ VỤ", f"{total_cases} ca")
                k3.metric("📈 TRUNG BÌNH/CA", f"{avg_cost:,.0f} đ")

                st.divider()

                # --- 3. BIỂU ĐỒ TRỰC QUAN ---
                c1, c2 = st.columns(2)
                
                with c1:
                    # Top 10 lý do hỏng (Lấy từ trường issue_reason)
                    if 'issue_reason' in df_view.columns:
                        issue_counts = df_view['issue_reason'].value_counts().reset_index().head(10)
                        issue_counts.columns = ['Lý do', 'Số lượng']
                        fig_issue = px.bar(issue_counts, x='Số lượng', y='Lý do', orientation='h', 
                                          title="TOP 10 LÝ DO HỎNG PHỔ BIẾN",
                                          color_discrete_sequence=['#FF4B2B'])
                        st.plotly_chart(fig_issue, use_container_width=True)
                
                with c2:
                    # Cơ cấu chi phí theo Vùng (Lấy từ branch/VÙNG)
                    if 'VÙNG' in df_view.columns and total_cost > 0:
                        fig_pie = px.pie(df_view, names='VÙNG', values='CHI_PHÍ_THỰC', 
                                        title="CƠ CẤU CHI PHÍ THEO VÙNG", hole=0.4,
                                        color_discrete_sequence=px.colors.sequential.Oranges_r)
                        st.plotly_chart(fig_pie, use_container_width=True)

                st.divider()

                # --- 4. BẢNG CHI TIẾT (Xử lý mượt 800+ dòng) ---
                st.subheader("📋 DANH SÁCH CHI TIẾT")
                # Chọn các cột quan trọng để hiển thị
                show_cols = ['MÃ_MÁY', 'customer_name', 'issue_reason', 'VÙNG', 'NGÀY_HIỂN_THỊ', 'CHI_PHÍ_THỰC']
                safe_show = [c for c in show_cols if c in df_view.columns]
                
                # Sắp xếp theo ngày mới nhất
                df_display = df_view.sort_values(by='confirmed_date', ascending=False)
                
                st.dataframe(
                    df_display[safe_show], 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "CHI_PHÍ_THỰC": st.column_config.NumberColumn("Chi phí (VNĐ)", format="%d"),
                        "NGÀY_HIỂN_THỊ": "Ngày Xác Nhận"
                    }
                )

    with tabs[2]:
        st.subheader("📥 NHẬP DỮ LIỆU GOOGLE SHEET (CSV)")
        up = st.file_uploader("Chọn file CSV", type="csv")
        if up:
            # Đọc file với utf-8-sig để sửa lỗi font tiếng Việt
            df_raw = pd.read_csv(up, encoding='utf-8-sig').fillna("")
            
            # --- LÀM SẠCH DỮ LIỆU TRƯỚC KHI HIỂN THỊ ---
            df_up = clean_excel_data(df_raw)
            
            st.write("🔍 Xem trước dữ liệu (Đã xử lý ngày & font):")
            st.dataframe(df_up.head(10), use_container_width=True)
            
            if st.button("🚀 ĐỒNG BỘ NGAY"):
                # 1. Làm sạch font và mapping tên cột trước
                df_clean = clean_excel_data(df_up) 
                
                # 2. Chia nhỏ thành từng đợt 100 dòng
                chunk_size = 100
                chunks = [df_clean[i:i + chunk_size] for i in range(0, df_clean.shape[0], chunk_size)]
                num_chunks = len(chunks)
                
                total_synced = 0
                main_progress = st.progress(0)
                
                with st.status("🏗️ Đang nạp dữ liệu lớn (800+ dòng)...", expanded=True) as status:
                    for idx, chunk in enumerate(chunks):
                        # Cập nhật thanh tiến trình (0.0 -> 1.0)
                        main_progress.progress((idx + 1) / num_chunks)
                        status.write(f"📦 Đang nạp đợt {idx + 1}/{num_chunks}...")
                        
                        count = import_to_enterprise_schema(chunk)
                        total_synced += count
                    
                    status.update(label=f"✅ Thành công! Đã nạp {total_synced} dòng.", state="complete", expanded=False)
                
                st.balloons()
                st.cache_data.clear()
                time.sleep(2)
                st.rerun()

if __name__ == "__main__":
    main()
