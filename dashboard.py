import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import time
from supabase import create_client

# --- 1. CẤU HÌNH & KẾT NỐI ---
st.set_page_config(page_title="4ORANGES - REPAIR OPS", layout="wide", page_icon="🎨")
ORANGE_COLORS = ["#FF8C00", "#FFA500", "#FF4500", "#E67E22", "#D35400"]

SUPABASE_URL = "https://cigbnbaanpebwrufzxfg.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_NQzqwJ4YhKC4sQGLxyLAyw_mwRFhkRf")

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Lỗi kết nối Supabase: {e}")

# --- 2. HÀM TẢI DỮ LIỆU (FIX LỖI TREO & MẤT NĂM 2025) ---
@st.cache_data(ttl=300) # Chỉ để 1 cái cache duy nhất
def load_data_from_db():
    try:
        # Lấy giới hạn lớn để bao phủ 800+ dòng
        res = supabase.table("repair_cases").select(
            "*, machines(machine_code, region), repair_costs(actual_cost)"
        ).limit(5000).execute()
        
        if not res.data:
            return pd.DataFrame()
            
        df = pd.json_normalize(res.data)
        
        mapping = {
            "machines.machine_code": "MÃ_MÁY",
            "repair_costs.actual_cost": "CHI_PHÍ_THỰC",
            "branch": "VÙNG"
        }
        df = df.rename(columns=mapping)

        if 'confirmed_date' in df.columns:
            # Ép kiểu ngày tháng, lỗi thì ra NaT
            df['confirmed_date'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
            # Điền ngày hiện tại cho các ô lỗi để tránh mất dữ liệu khi lọc Năm
            df['confirmed_date'] = df['confirmed_date'].fillna(pd.Timestamp.now())
            
            df['NĂM'] = df['confirmed_date'].dt.year.astype(int)
            df['THÁNG'] = df['confirmed_date'].dt.month.astype(int)
            df['NGÀY_HIỂN_THỊ'] = df['confirmed_date'].dt.strftime('%d/%m/%Y')
            
        return df
    except Exception as e:
        return pd.DataFrame()

# --- 3. HÀM IMPORT (DỌN DẸP SẠCH LỖI VÒNG LẶP) ---
def import_to_enterprise_schema(df_chunk):
    success_count = 0
    # Phải dọn dẹp giá tiền trước
    def clean_price(val):
        try:
            if not val or pd.isna(val): return 0
            return float(str(val).replace(',', ''))
        except: return 0

    for i, r in df_chunk.iterrows():
        m_code = str(r.get("Mã số máy", "")).strip()
        if not m_code or m_code.lower() in ["nan", "mã số máy"]: continue
        
        try:
            # 1. Upsert Machine
            m_res = supabase.table("machines").upsert({
                "machine_code": m_code,
                "region": str(r.get("Chi Nhánh", "Chưa xác định"))
            }, on_conflict="machine_code").execute()
            
            if not m_res.data: continue
            machine_id = m_res.data[0]["id"]

            # 2. Xử lý ngày (đã được ffill từ hàm clean_excel_data)
            confirmed_val = str(r.get("Ngày Xác nhận", "")).strip()
            formatted_date = None
            if confirmed_val and confirmed_val != "None":
                try:
                    formatted_date = pd.to_datetime(confirmed_val, dayfirst=True).strftime('%Y-%m-%d')
                except: formatted_date = None

            # 3. Insert Case
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
                
                # Insert Cost
                supabase.table("repair_costs").insert({
                    "repair_case_id": case_id,
                    "estimated_cost": clean_price(r.get("Chi Phí Dự Kiến", 0)),
                    "actual_cost": actual_cost
                }).execute()
                success_count += 1
        except:
            continue
    return success_count

# --- 4. GIAO DIỆN & LOGIC HIỂN THỊ ---
def clean_excel_data(df):
    standard_names = {
        'Ngày Xác nhận': ['NgÃ y XÃ¡c nhÃ¢n', 'Ngay Xac nhan', 'Ngày xác nhận'],
        'Tên KH': ['TÃªn KH', 'Ten KH'],
        'Lý Do': ['LÃ½ Do', 'Ly Do'],
        'Chi Nhánh': ['Chi NhÃ¡nh', 'Chi nhanh'],
        'Chi Phí Thực Tế': ['Chi PhÃ­ Thá»±c Táº¿', 'Chi phi thuc te'],
        'Chi Phí Dự Kiến': ['Chi PhÃ­ Dá»± Kiáº¿n'],
        'Mã số máy': ['MÃ£ sá»‘ mÃ¡y', 'Ma so may', 'Mã số máy']
    }
    for real_name, aliases in standard_names.items():
        for alias in aliases:
            if alias in df.columns:
                df = df.rename(columns={alias: real_name})

    if 'Ngày Xác nhận' in df.columns:
        df['Ngày Xác nhận'] = df['Ngày Xác nhận'].astype(str).str.strip()
        df['Ngày Xác nhận'] = df['Ngày Xác nhận'].replace(['', 'nan', 'NaN', 'None'], pd.NA)
        # Sửa lỗi: Chỉ ffill nếu có dữ liệu ngày để tránh treo
        df['Ngày Xác nhận'] = df['Ngày Xác nhận'].ffill()
    return df

def main():
    # Load dữ liệu ngay đầu để dùng chung
    df_db = load_data_from_db()

    with st.sidebar:
        st.title("🎨 4ORANGES OPS")
        if st.button('🔄 REFRESH DATABASE', type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        if not df_db.empty:
            list_years = sorted(df_db['NĂM'].unique().tolist(), reverse=True)
            sel_year = st.selectbox("📅 Chọn Năm", list_years)
            
            year_data = df_db[df_db['NĂM'] == sel_year]
            list_months = ["Tất cả"] + sorted(year_data['THÁNG'].unique().tolist())
            sel_month = st.selectbox("📆 Chọn Tháng", list_months)
        else:
            sel_year = datetime.datetime.now().year
            sel_month = "Tất cả"

    tabs = st.tabs(["📊 XU HƯỚNG", "💰 CHI PHÍ", "📥 NHẬP DỮ LIỆU"])

    with tabs[0]:
        if df_db.empty:
            st.info("👋 Đang kết nối dữ liệu... Sếp đợi tí hoặc nạp dữ liệu mới nhé.")
        else:
            df_view = df_db[df_db['NĂM'] == sel_year].copy()
            if sel_month != "Tất cả":
                df_view = df_view[df_view['THÁNG'] == sel_month]
            
            if df_view.empty:
                st.warning(f"⚠️ Không có dữ liệu năm {sel_year}")
            else:
                # KPI
                k1, k2, k3 = st.columns(3)
                total_cost = df_view['CHI_PHÍ_THỰC'].sum()
                k1.metric("💰 TỔNG CHI PHÍ", f"{total_cost:,.0f} đ")
                k2.metric("📋 TỔNG SỰ VỤ", f"{len(df_view)} ca")
                k3.metric("📈 TRUNG BÌNH/CA", f"{total_cost/len(df_view):,.0f} đ" if len(df_view)>0 else "0")

                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    if 'issue_reason' in df_view.columns:
                        fig = px.bar(df_view['issue_reason'].value_counts().head(10), orientation='h', title="TOP 10 LÝ DO HỎNG", color_discrete_sequence=['#FF8C00'])
                        st.plotly_chart(fig, use_container_width=True)
                with c2:
                    if 'VÙNG' in df_view.columns:
                        fig_pie = px.pie(df_view, names='VÙNG', values='CHI_PHÍ_THỰC', title="CHI PHÍ THEO VÙNG", hole=0.4, color_discrete_sequence=ORANGE_COLORS)
                        st.plotly_chart(fig_pie, use_container_width=True)

                st.subheader("📋 DANH SÁCH CHI TIẾT")
                st.dataframe(df_view[['MÃ_MÁY', 'VÙNG', 'NGÀY_HIỂN_THỊ', 'CHI_PHÍ_THỰC']].sort_values('confirmed_date', ascending=False), use_container_width=True, hide_index=True)

    # --- Phần tab[2] giữ nguyên logic chunking nhưng dùng hàm import_to_enterprise_schema mới ---
