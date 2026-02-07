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
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. FETCH DỮ LIỆU (FIX 4: CHỈ CACHE RAW DATA) ---
@st.cache_data(ttl=120)
def fetch_repair_cases():
    try:
        # Query tối giản để tránh nghẽn, lấy ID máy thay vì JOIN phức tạp lúc đầu
        res = supabase.table("repair_cases") \
            .select("id, machine_id, branch, confirmed_date, issue_reason, customer_name") \
            .order("confirmed_date", desc=True) \
            .limit(2000) \
            .execute()
        return res.data
    except Exception as e:
        return None

def load_data_from_db():
    data = fetch_repair_cases()
    if not data:
        return pd.DataFrame()
    
    df = pd.DataFrame(data)
    
    # Ép kiểu ngày và xử lý NaT
    if 'confirmed_date' in df.columns:
        df['confirmed_date'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        df = df.dropna(subset=['confirmed_date']) # Bỏ dòng không ngày để Dashboard chuẩn

        df['NĂM'] = df['confirmed_date'].dt.year.astype(int)
        df['THÁNG'] = df['confirmed_date'].dt.month.astype(int)
        df['NGÀY_HIỂN_THỊ'] = df['confirmed_date'].dt.strftime('%d/%m/%Y')
    
    # Khớp cột cho UI (Fix 2)
    if 'branch' in df.columns:
        df = df.rename(columns={'branch': 'VÙNG'})
    
    # Fake cột CHI_PHÍ_THỰC (Vì query raw chưa lấy từ bảng costs)
    if 'CHI_PHÍ_THỰC' not in df.columns:
        df['CHI_PHÍ_THỰC'] = 0 

    return df

# --- 3. MAIN APP ---
def main():
    # --- SIDEBAR (FIX 3 & 4) ---
    with st.sidebar:
        st.title("🎨 4ORANGES OPS")
        
        if st.button('🔄 REFRESH DATABASE', type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
            
        df_db = load_data_from_db()

        # Debug nhanh (Fix 3)
        if not df_db.empty:
            st.success(f"📡 Đã tải {len(df_db)} dòng!")
            if 'NĂM' in df_db.columns:
                list_years = sorted(df_db['NĂM'].unique().tolist(), reverse=True)
                sel_year = st.selectbox("📅 Chọn Năm", list_years)
                
                year_data = df_db[df_db['NĂM'] == sel_year]
                list_months = ["Tất cả"] + sorted(year_data['THÁNG'].unique().tolist())
                sel_month = st.selectbox("📆 Chọn Tháng", list_months)
            
            st.divider()
            st.write(f"🧪 Columns: {list(df_db.columns)}")
        else:
            st.warning("⚠️ Chưa có dữ liệu trong Database")
            sel_year, sel_month = datetime.datetime.now().year, "Tất cả"

    # --- TABS ---
    tabs = st.tabs(["📊 XU HƯỚNG", "💰 CHI PHÍ", "📥 NHẬP DỮ LIỆU"])

    # --- TAB 0: XU HƯỚNG ---
    with tabs[0]:
        if df_db.empty:
            st.info("👋 Sếp hãy nạp dữ liệu ở tab NHẬP DỮ LIỆU nhé.")
        else:
            # Lọc dữ liệu
            df_view = df_db[df_db['NĂM'] == sel_year].copy()
            if sel_month != "Tất cả":
                df_view = df_view[df_view['THÁNG'] == sel_month]
            
            if df_view.empty:
                st.warning(f"⚠️ Không có dữ liệu năm {sel_year} tháng {sel_month}")
            else:
                # KPI
                k1, k2, k3 = st.columns(3)
                total_cost = df_view['CHI_PHÍ_THỰC'].sum()
                k1.metric("💰 TỔNG CHI PHÍ", f"{total_cost:,.0f} đ")
                k2.metric("📋 TỔNG SỰ VỤ", f"{len(df_view)} ca")
                k3.metric("📈 TRUNG BÌNH/CA", f"{total_cost/len(df_view):,.0f} đ" if len(df_view)>0 else "0")

                st.divider()
                
                # Biểu đồ
                c1, c2 = st.columns(2)
                with c1:
                    fig_issue = px.bar(df_view['issue_reason'].value_counts().head(10), 
                                      orientation='h', title="TOP 10 LÝ DO HỎNG", 
                                      color_discrete_sequence=['#FF4B2B'])
                    st.plotly_chart(fig_issue, use_container_width=True)
                with c2:
                    fig_pie = px.pie(df_view, names='VÙNG', values='CHI_PHÍ_THỰC', 
                                    title="CHI PHÍ THEO VÙNG", hole=0.4, 
                                    color_discrete_sequence=ORANGE_COLORS)
                    st.plotly_chart(fig_pie, use_container_width=True)

                # --- BẢNG CHI TIẾT (FIX 1) ---
                st.subheader("📋 DANH SÁCH CHI TIẾT")
                
                # 1. Sort trước khi cắt cột để tránh KeyError 'confirmed_date'
                df_display = df_view.sort_values(by='confirmed_date', ascending=False)
                
                # 2. Định nghĩa các cột an toàn có trong DB
                # machine_id dùng thay cho MÃ_MÁY vì query chưa join bảng machines
                actual_cols = ['machine_id', 'customer_name', 'VÙNG', 'NGÀY_HIỂN_THỊ', 'CHI_PHÍ_THỰC']
                
                # 3. Hiển thị và rename cột ngay tại UI cho chuyên nghiệp
                st.dataframe(
                    df_display[actual_cols].rename(columns={
                        'machine_id': 'MÃ_MÁY',
                        'customer_name': 'TÊN KHÁCH HÀNG',
                        'NGÀY_HIỂN_THỊ': 'NGÀY XÁC NHẬN'
                    }),
                    use_container_width=True,
                    hide_index=True
                )

    # --- TAB 1 & 2 (Giữ nguyên logic của sếp hoặc bổ sung sau) ---

if __name__ == "__main__":
    main()
