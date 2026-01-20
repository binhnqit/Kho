import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CAU HINH ---
st.set_page_config(page_title="Quan Ly Kho Lien Mien V1.1", layout="wide")

@st.cache_data(ttl=2)
def load_all_data():
    # Link du lieu cua sep
    sources = {
        "MIEN BAC": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv",
        "DA NANG": "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"
    }
    
    final_df = pd.DataFrame()
    
    for region, url in sources.items():
        try:
            # Doc tu dong 2
            df = pd.read_csv(url, skiprows=1, dtype=str).fillna("")
            df.columns = [str(c).strip().upper() for c in df.columns]
            
            # Xu ly tron dong (Forward Fill)
            df = df.replace(r'^\s*$', pd.NA, regex=True)
            if 'MÃ SỐ MÁY' in df.columns:
                df['MÃ SỐ MÁY'] = df['MÃ SỐ MÁY'].ffill()
                # Dien day them cac cot de phan loai trang thai chinh xac
                for c in ['NGÀY NHẬN', 'SỬA NỘI BỘ', 'SỬA BÊN NGOÀI', 'NGÀY TRẢ']:
                    if c in df.columns: df[c] = df[c].ffill()
            
            clean_list = []
            for _, row in df.iterrows():
                ma = str(row.get('MÃ SỐ MÁY', '')).strip()
                if not ma or ma.upper() in ["NAN", "STT", "MÃ SỐ MÁY", "0"]: continue
                
                d_nhan = pd.to_datetime(row.get('NGÀY NHẬN', ''), dayfirst=True, errors='coerce')
                d_tra = pd.to_datetime(row.get('NGÀY TRẢ', ''), dayfirst=True, errors='coerce')
                
                sua_nb = str(row.get('SỬA NỘI BỘ', '')).upper()
                hu_hong = str(row.get('HƯ KHÔNG SỬA ĐƯỢC', '')).strip()
                # Check giao lai theo vung
                giao_lai = str(row.get('GIAO LẠI MIỀN BẮC', '')).upper() if region == "MIEN BAC" else str(row.get('GIAO LẠI ĐN', '')).upper()
                
                status = "TON KHO"
                if "THANH LY" in sua_nb or hu_hong != "":
                    status = "THANH LY"
                elif pd.notnull(d_tra) or any(x in giao_lai for x in ["OK", "XONG"]):
                    status = "DA XONG"

                clean_list.append({
                    "CHI NHANH": region,
                    "MA MAY": ma,
                    "TRANG THAI": status,
                    "NGAY NHAN": d_nhan,
                    "LOAI MAY": row.get('LOẠI MÁY', ''),
                    "KIEM TRA": row.get('KIỂM TRA THỰC TẾ', ''),
                    "NOI BO": row.get('SỬA NỘI BỘ', ''),
                    "NGOAI": row.get('SỬA BÊN NGOÀI', '')
                })
            final_df = pd.concat([final_df, pd.DataFrame(clean_list)], ignore_index=True)
        except Exception as e:
            st.error(f"Loi doc du lieu {region}: {e}")
            
    return final_df

# --- 3. DASHBOARD ---
st.title("🚀 QUẢN LÝ KHO LIÊN MIỀN: ĐÀ NẴNG - MIỀN BẮC")

df = load_all_data()

if not df.empty:
    # Bo loc Sidebar
    with st.sidebar:
        st.header("BO LOC")
        selected_region = st.multiselect("Chon Chi nhanh", df['CHI NHANH'].unique(), default=df['CHI NHANH'].unique())
        selected_status = st.multiselect("Chon Trang thai", df['TRANG THAI'].unique(), default=df['TRANG THAI'].unique())
        
        df_filtered = df[(df['CHI NHANH'].isin(selected_region)) & (df['TRANG THAI'].isin(selected_status))]

    # KPI
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tong thiet bi", len(df_filtered))
    c2.metric("Dang ton kho", len(df_filtered[df_filtered['TRANG THAI'] == "TON KHO"]))
    c3.metric("Da hoan tat", len(df_filtered[df_filtered['TRANG THAI'] == "DA XONG"]))
    c4.metric("Thanh ly", len(df_filtered[df_filtered['TRANG THAI'] == "THANH LY"]))

    # Bieu do so sanh
    st.write("---")
    col_l, col_r = st.columns(2)
    with col_l:
        st.plotly_chart(px.pie(df_filtered, names='TRANG THAI', title="Co cau trang thai tong", hole=0.4), use_container_width=True)
    with col_r:
        fig_bar = px.bar(df_filtered.groupby(['CHI NHANH', 'TRANG THAI']).size().reset_index(name='SL'), 
                         x='CHI NHANH', y='SL', color='TRANG THAI', barmode='group', title="So sanh ton kho 2 mien")
        st.plotly_chart(fig_bar, use_container_width=True)

    # Chi tiet
    st.subheader("📋 Danh sach thiet bi chi tiet")
    st.dataframe(df_filtered.sort_values('NGAY NHAN', ascending=False), use_container_width=True)
else:
    st.info("He thong dang ket noi du lieu...")
