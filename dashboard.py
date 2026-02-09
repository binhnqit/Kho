import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from supabase import create_client

# --- 1. KẾT NỐI ---
SUPABASE_URL = "https://cigbnbaanpebwrufzxfg.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_NQzqwJ4YhKC4sQGLxyLAyw_mwRFhkRf")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. HÀM FETCH (DÙNG ĐÚNG TÊN CỘT COMPENSATION) ---
@st.cache_data(ttl=60)
def fetch_repair_cases():
    try:
        res = supabase.table("repair_cases") \
            .select("id, machine_id, branch, confirmed_date, issue_reason, customer_name, compensation") \
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
    
    # Map compensation thành CHI_PHÍ_THỰC để hiển thị UI
    df = df.rename(columns={'branch': 'VÙNG', 'compensation': 'CHI_PHÍ_THỰC'})
    if 'CHI_PHÍ_THỰC' not in df.columns: df['CHI_PHÍ_THỰC'] = 0
    return df

# --- 3. HÀM IMPORT (SỬA LỖI COLUMN DOES NOT EXIST) ---
def import_to_enterprise_schema(df_chunk):
    success_count = 0
    for _, r in df_chunk.iterrows():
        try:
            m_code = str(r.get("Mã số máy", "")).strip()
            if not m_code or m_code.lower() == "nan": continue

            # 1. Upsert Machines (Giữ nguyên)
            m_res = supabase.table("machines").upsert({
                "machine_code": m_code,
                "region": str(r.get("Chi Nhánh", "Chưa xác định"))
            }, on_conflict="machine_code").execute()
            
            if not m_res.data: continue
            machine_id = m_res.data[0]["id"]

            # 2. Định dạng ngày
            confirmed_val = str(r.get("Ngày Xác nhận", "")).strip()
            formatted_date = None
            if confirmed_val and confirmed_val != "None":
                try:
                    formatted_date = pd.to_datetime(confirmed_val, dayfirst=True).strftime('%Y-%m-%d')
                except: pass

            # 3. Xử lý Chi phí (Đưa vào cột compensation)
            cost_raw = str(r.get("Chi Phí Thực Tế", "0")).replace(",", "")
            try:
                val_compensation = float(cost_raw)
            except:
                val_compensation = 0

            # 4. Insert (Dùng chuẩn tên cột branch, customer_name, compensation)
            supabase.table("repair_cases").insert({
                "machine_id": machine_id,
                "branch": str(r.get("Chi Nhánh", "Chưa xác định")),
                "issue_reason": str(r.get("Lý Do", "")),
                "customer_name": str(r.get("Tên KH", "")),
                "confirmed_date": formatted_date,
                "compensation": val_compensation  # ĐÃ ĐỔI TÊN Ở ĐÂY ✅
            }).execute()
            success_count += 1
        except Exception as e:
            st.error(f"Lỗi dòng {m_code}: {e}")
            continue
    return success_count

# --- 4. PHẦN GIAO DIỆN (Giữ nguyên logic của sếp) ---
def main():
    st.sidebar.title("🎨 4ORANGES OPS")
    if st.sidebar.button('🔄 LÀM MỚI DATABASE'):
        st.cache_data.clear()
        st.rerun()
        
    df_db = load_data_from_db()
    
    tabs = st.tabs(["📊 XU HƯỚNG", "📥 NHẬP DỮ LIỆU"])
    
    with tabs[0]:
        if df_db.empty:
            st.warning("Database trống hoặc lỗi kết nối.")
        else:
            # Lấy list năm từ dữ liệu thực tế
            years = sorted(df_db['NĂM'].unique(), reverse=True)
            sel_year = st.sidebar.selectbox("Chọn năm", years)
            df_view = df_db[df_db['NĂM'] == sel_year]
            
            st.metric("TỔNG CHI PHÍ (COMPENSATION)", f"{df_view['CHI_PHÍ_THỰC'].sum():,.0f} đ")
            st.dataframe(df_view[['NGÀY_HIỂN_THỊ', 'VÙNG', 'customer_name', 'issue_reason', 'CHI_PHÍ_THỰC']], use_container_width=True)

    with tabs[1]:
        up = st.file_uploader("Nạp CSV", type="csv")
        if up and st.button("🚀 ĐỒNG BỘ"):
            df_up = pd.read_csv(up, encoding='utf-8-sig').fillna("").ffill()
            # Làm sạch tên cột nếu có khoảng trắng
            df_up.columns = [c.strip() for c in df_up.columns]
            
            success = import_to_enterprise_schema(df_up)
            st.success(f"Nạp thành công {success} dòng!")
            st.cache_data.clear()

if __name__ == "__main__":
    main()
