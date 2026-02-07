import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from supabase import create_client

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="4ORANGES - REPAIR OPS", layout="wide", page_icon="🎨")
ORANGE_COLORS = ["#FF8C00", "#FFA500", "#FF4500", "#E67E22", "#D35400"]

SUPABASE_URL = "https://cigbnbaanpebwrufzxfg.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_NQzqwJ4YhKC4sQGLxyLAyw_mwRFhkRf")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. HÀM XỬ LÝ (SỬA LỖI TRỐNG DỮ LIỆU) ---
def clean_excel_data(df):
    """Điền dữ liệu trống do gộp dòng trong Excel"""
    # Sửa lỗi Font và khoảng trắng tên cột
    df.columns = [c.strip() for c in df.columns]
    
    # ffill() giúp điền Ngày và Chi nhánh bị thiếu ở các dòng dưới
    cols_to_fill = ['Ngày Xác nhận', 'Chi Nhánh', 'Mã số máy']
    for col in cols_to_fill:
        if col in df.columns:
            df[col] = df[col].replace("", None).ffill()
    return df

@st.cache_data(ttl=60)
def fetch_repair_cases():
    try:
        # Lấy thêm cột actual_cost (hoặc tên cột chi phí sếp đặt trong DB)
        res = supabase.table("repair_cases") \
            .select("id, machine_id, branch, confirmed_date, issue_reason, customer_name, actual_cost") \
            .order("confirmed_date", desc=True) \
            .limit(4000) \
            .execute()
        return res.data
    except Exception as e:
        st.error(f"Lỗi fetch: {e}")
        return None

def load_data_from_db():
    data = fetch_repair_cases()
    if not data: return pd.DataFrame()
    
    df = pd.DataFrame(data)
    if 'confirmed_date' in df.columns:
        df['confirmed_date'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        df = df.dropna(subset=['confirmed_date'])
        df['NĂM'] = df['confirmed_date'].dt.year.astype(int)
        df['THÁNG'] = df['confirmed_date'].dt.month.astype(int)
        df['NGÀY_HIỂN_THỊ'] = df['confirmed_date'].dt.strftime('%d/%m/%Y')
    
    # Map lại tên cột để UI hiển thị đẹp
    df = df.rename(columns={'branch': 'VÙNG', 'actual_cost': 'CHI_PHÍ_THỰC'})
    if 'CHI_PHÍ_THỰC' not in df.columns: df['CHI_PHÍ_THỰC'] = 0
    return df

def import_to_enterprise_schema(df_chunk):
    success_count = 0
    for _, r in df_chunk.iterrows():
        try:
            m_code = str(r.get("Mã số máy", "")).strip()
            if not m_code or m_code.lower() == "nan": continue

            # 1. Upsert Machines
            m_res = supabase.table("machines").upsert({
                "machine_code": m_code,
                "region": str(r.get("Chi Nhánh", "Chưa xác định"))
            }, on_conflict="machine_code").execute()
            
            if not m_res.data: continue
            machine_id = m_res.data[0]["id"]

            # 2. Xử lý ngày (Ép kiểu chuẩn ISO cho DB)
            confirmed_val = str(r.get("Ngày Xác nhận", "")).strip()
            formatted_date = None
            if confirmed_val and confirmed_val != "None":
                try:
                    formatted_date = pd.to_datetime(confirmed_val, dayfirst=True).strftime('%Y-%m-%d')
                except: pass

            # 3. Xử lý Chi phí (Xóa dấu phẩy của 200,000)
            cost_raw = str(r.get("Chi Phí Thực Tế", "0")).replace(",", "")
            try:
                actual_cost = float(cost_raw)
            except:
                actual_cost = 0

            # 4. Insert Repair Case
            supabase.table("repair_cases").insert({
                "machine_id": machine_id,
                "branch": str(r.get("Chi Nhánh", "Chưa xác định")),
                "issue_reason": str(r.get("Lý Do", "")),
                "customer_name": str(r.get("Tên KH", "")),
                "confirmed_date": formatted_date,
                "actual_cost": actual_cost
            }).execute()
            success_count += 1
        except Exception as e:
            st.error(f"Lỗi dòng {m_code}: {e}")
            continue
    return success_count

# --- 3. GIAO DIỆN CHÍNH ---
def main():
    with st.sidebar:
        st.title("🎨 4ORANGES OPS")
        if st.button('🔄 LÀM MỚI DATABASE', type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        df_db = load_data_from_db()
        
        if not df_db.empty:
            st.success(f"📡 Đã kết nối: {len(df_db)} dòng")
            sel_year = st.selectbox("📅 Năm", sorted(df_db['NĂM'].unique(), reverse=True))
            sel_month = st.selectbox("📆 Tháng", ["Tất cả"] + sorted(df_db[df_db['NĂM']==sel_year]['THÁNG'].unique()))
        else:
            st.warning("⚠️ Database đang trống")
            sel_year, sel_month = 2025, "Tất cả"

    tabs = st.tabs(["📊 XU HƯỚNG", "📥 NHẬP DỮ LIỆU"])

    with tabs[0]:
        if df_db.empty:
            st.info("Sếp hãy qua tab NHẬP DỮ LIỆU để đẩy file CSV lên nhé.")
        else:
            df_view = df_db[df_db['NĂM'] == sel_year].copy()
            if sel_month != "Tất cả":
                df_view = df_view[df_view['THÁNG'] == sel_month]
            
            k1, k2, k3 = st.columns(3)
            k1.metric("💰 TỔNG CHI PHÍ", f"{df_view['CHI_PHÍ_THỰC'].sum():,.0f} đ")
            k2.metric("📋 TỔNG SỰ VỤ", f"{len(df_view)} ca")
            k3.metric("🏗️ CHI NHÁNH", f"{df_view['VÙNG'].nunique()}")

            # Biểu đồ
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(px.bar(df_view['issue_reason'].value_counts().head(10), orientation='h', title="LÝ DO HỎNG"), use_container_width=True)
            with c2:
                st.plotly_chart(px.pie(df_view, names='VÙNG', values='CHI_PHÍ_THỰC', title="CHI PHÍ THEO VÙNG"), use_container_width=True)

            st.subheader("📋 CHI TIẾT DỮ LIỆU")
            st.dataframe(df_view[['NGÀY_HIỂN_THỊ', 'VÙNG', 'customer_name', 'issue_reason', 'CHI_PHÍ_THỰC']], use_container_width=True, hide_index=True)

    with tabs[1]:
        st.subheader("📥 ĐỒNG BỘ GOOGLE SHEET (CSV)")
        up = st.file_uploader("Chọn file CSV đã xuất từ Google Sheet", type="csv")
        if up:
            df_up = clean_excel_data(pd.read_csv(up, encoding='utf-8-sig').fillna(""))
            st.write("🔍 Kiểm tra dữ liệu trước khi nạp:")
            st.dataframe(df_up.head(5), use_container_width=True)
            
            if st.button("🚀 XÁC NHẬN ĐẨY DỮ LIỆU LÊN CLOUD"):
                with st.spinner("Đang nạp dữ liệu..."):
                    chunk_size = 50
                    total = len(df_up)
                    success = 0
                    bar = st.progress(0)
                    for i in range(0, total, chunk_size):
                        success += import_to_enterprise_schema(df_up.iloc[i : i + chunk_size])
                        bar.progress(min((i + chunk_size) / total, 1.0))
                    
                    st.success(f"✅ Đã nạp thành công {success}/{total} dòng!")
                    st.cache_data.clear()
                    st.balloons()

if __name__ == "__main__":
    main()
