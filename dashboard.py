import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import time
from supabase import create_client

# --- 1. CẤU HÌNH & KẾT NỐI ---
st.set_page_config(page_title="4ORANGES - REPAIR OPS", layout="wide", page_icon="🎨")
ORANGE_COLORS = ["#FF8C00", "#FFA500", "#FF4500", "#E67E22", "#D35400"]

# Kết nối Supabase
SUPABASE_URL = "https://cigbnbaanpebwrufzxfg.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_NQzqwJ4YhKC4sQGLxyLAyw_mwRFhkRf")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. HÀM XỬ LÝ DỮ LIỆU BỔ SUNG ---
def clean_excel_data(df):
    """Xử lý làm sạch dữ liệu từ CSV trước khi nạp"""
    # Điền dữ liệu cho các ô trống do gộp dòng (ffill)
    for col in ['Ngày Xác nhận', 'Chi Nhánh', 'Mã số máy']:
        if col in df.columns:
            df[col] = df[col].replace("", None).ffill()
    return df

@st.cache_data(ttl=120)
def fetch_repair_cases():
    try:
        res = supabase.table("repair_cases") \
            .select("id, machine_id, branch, confirmed_date, issue_reason, customer_name") \
            .order("confirmed_date", desc=True) \
            .limit(3000) \
            .execute()
        return res.data
    except Exception as e:
        st.error(f"Lỗi lấy dữ liệu: {e}")
        return None

def load_data_from_db():
    data = fetch_repair_cases()
    if not data:
        return pd.DataFrame()
    
    df = pd.DataFrame(data)
    
    if 'confirmed_date' in df.columns:
        df['confirmed_date'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        df = df.dropna(subset=['confirmed_date'])
        df['NĂM'] = df['confirmed_date'].dt.year.astype(int)
        df['THÁNG'] = df['confirmed_date'].dt.month.astype(int)
        df['NGÀY_HIỂN_THỊ'] = df['confirmed_date'].dt.strftime('%d/%m/%Y')
    
    if 'branch' in df.columns:
        df = df.rename(columns={'branch': 'VÙNG'})
    
    if 'CHI_PHÍ_THỰC' not in df.columns:
        df['CHI_PHÍ_THỰC'] = 0 

    return df

def import_to_enterprise_schema(df_chunk):
    success_count = 0
    for _, r in df_chunk.iterrows():
        try:
            # Lấy Mã số máy
            m_code = str(r.get("Mã số máy", "")).strip()
            if not m_code or m_code.lower() == "nan": continue

            # 1. Upsert bảng machines
            m_res = supabase.table("machines").upsert({
                "machine_code": m_code,
                "region": str(r.get("Chi Nhánh", "Chưa xác định"))
            }, on_conflict="machine_code").execute()
            
            if not m_res.data: continue
            machine_id = m_res.data[0]["id"]

            # 2. Xử lý ngày xác nhận
            confirmed_val = str(r.get("Ngày Xác nhận", "")).strip()
            formatted_date = None
            if confirmed_val and confirmed_val != "None":
                formatted_date = pd.to_datetime(confirmed_val, dayfirst=True).strftime('%Y-%m-%d')

            # 3. Lấy chi phí thực tế
            # Loại bỏ dấu phẩy để DB hiểu là số
            cost_val = str(r.get("Chi Phí Thực Tế", "0")).replace(",", "")
            try:
                actual_cost = float(cost_val)
            except:
                actual_cost = 0

            # 4. Insert bảng repair_cases
            res = supabase.table("repair_cases").insert({
                "machine_id": machine_id,
                "branch": str(r.get("Chi Nhánh", "Chưa xác định")),
                "issue_reason": str(r.get("Lý Do", "")),
                "customer_name": str(r.get("Tên KH", "")),
                "confirmed_date": formatted_date,
                "actual_cost": actual_cost  # Sếp kiểm tra cột này trong DB tên là gì nhé
            }).execute()
            
            if res.data:
                success_count += 1
        except Exception as e:
            st.error(f"Dòng lỗi: {m_code} - Lỗi: {str(e)}") # Hiện lỗi để sếp chụp ảnh cho tôi xem
            continue
    return success_count

# --- 3. MAIN APP ---
def main():
    # --- SIDEBAR ---
    with st.sidebar:
        st.title("🎨 4ORANGES OPS")
        if st.button('🔄 LÀM MỚI DỮ LIỆU', type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
            
        df_db = load_data_from_db()

        if not df_db.empty:
            st.success(f"📡 Đã tải {len(df_db)} dòng!")
            list_years = sorted(df_db['NĂM'].unique().tolist(), reverse=True)
            sel_year = st.selectbox("📅 Chọn Năm", list_years)
            
            year_data = df_db[df_db['NĂM'] == sel_year]
            list_months = ["Tất cả"] + sorted(year_data['THÁNG'].unique().tolist())
            sel_month = st.selectbox("📆 Chọn Tháng", list_months)
        else:
            st.warning("⚠️ Chưa có dữ liệu")
            sel_year, sel_month = datetime.datetime.now().year, "Tất cả"

    # --- TABS ---
    tabs = st.tabs(["📊 XU HƯỚNG", "💰 CHI PHÍ", "📥 NHẬP DỮ LIỆU"])

    # --- TAB 0: XU HƯỚNG ---
    with tabs[0]:
        if df_db.empty:
            st.info("👋 Sếp hãy nạp dữ liệu ở tab NHẬP DỮ LIỆU nhé.")
        else:
            df_view = df_db[df_db['NĂM'] == sel_year].copy()
            if sel_month != "Tất cả":
                df_view = df_view[df_view['THÁNG'] == sel_month]
            
            if df_view.empty:
                st.warning(f"⚠️ Không có dữ liệu năm {sel_year} tháng {sel_month}")
            else:
                k1, k2, k3 = st.columns(3)
                k1.metric("💰 TỔNG CHI PHÍ", f"{df_view['CHI_PHÍ_THỰC'].sum():,.0f} đ")
                k2.metric("📋 TỔNG SỰ VỤ", f"{len(df_view)} ca")
                k3.metric("🏗️ CHI NHÁNH ĐANG CHẠY", f"{df_view['VÙNG'].nunique()}")

                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    fig_issue = px.bar(df_view['issue_reason'].value_counts().head(10), 
                                      orientation='h', title="TOP 10 LÝ DO HỎNG", 
                                      color_discrete_sequence=['#FF4B2B'])
                    st.plotly_chart(fig_issue, use_container_width=True)
                with c2:
                    fig_pie = px.pie(df_view, names='VÙNG', values='id', title="TỶ LỆ SỰ VỤ THEO VÙNG",
                                    color_discrete_sequence=ORANGE_COLORS)
                    st.plotly_chart(fig_pie, use_container_width=True)

                st.subheader("📋 DANH SÁCH CHI TIẾT")
                df_display = df_view.sort_values(by='confirmed_date', ascending=False)
                actual_cols = ['machine_id', 'customer_name', 'VÙNG', 'NGÀY_HIỂN_THỊ']
                st.dataframe(
                    df_display[actual_cols].rename(columns={
                        'machine_id': 'ID MÁY',
                        'customer_name': 'TÊN KHÁCH HÀNG',
                        'NGÀY_HIỂN_THỊ': 'NGÀY XÁC NHẬN'
                    }),
                    use_container_width=True, hide_index=True
                )

    # --- TAB 2: NHẬP DỮ LIỆU ---
    with tabs[2]:
        st.subheader("📥 NHẬP DỮ LIỆU TỪ CSV")
        up = st.file_uploader("Chọn file CSV", type="csv")
        if up:
            df_raw = pd.read_csv(up, encoding='utf-8-sig').fillna("")
            df_up = clean_excel_data(df_raw)
            
            st.write("🔍 Xem trước dữ liệu (10 dòng đầu):")
            st.dataframe(df_up.head(10), use_container_width=True)
            
            if st.button("🚀 BẮT ĐẦU ĐỒNG BỘ"):
                chunk_size = 30 # Giảm xuống 30 để chắc chắn không treo
                total_rows = len(df_up)
                success_total = 0
                
                prog = st.progress(0)
                status = st.empty()
                
                for i in range(0, total_rows, chunk_size):
                    chunk = df_up.iloc[i : i + chunk_size]
                    count = import_to_enterprise_schema(chunk)
                    success_total += count
                    
                    percent = min((i + chunk_size) / total_rows, 1.0)
                    prog.progress(percent)
                    status.text(f"⏳ Đang xử lý: {success_total}/{total_rows} dòng...")
                
                st.success(f"✅ Đã nạp thành công {success_total} dòng!")
                st.cache_data.clear()
                st.balloons()

if __name__ == "__main__":
    main()
