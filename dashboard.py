import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CAU HINH ---
st.set_page_config(page_title="Quan Ly Kho Logistics V1.3", layout="wide")

@st.cache_data(ttl=2)
def load_and_process_logic():
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
            
            # Xu ly tron dong (Forward Fill) cho Ma may va cac thong tin lien quan
            df = df.replace(r'^\s*$', pd.NA, regex=True)
            if 'MÃ SỐ MÁY' in df.columns:
                cols_to_fill = ['MÃ SỐ MÁY', 'NGÀY NHẬN', 'LOẠI MÁY', 'KIỂM TRA THỰC TẾ', 'SỬA NỘI BỘ', 'SỬA BÊN NGOÀI']
                for c in cols_to_fill:
                    if c in df.columns: df[c] = df[c].ffill()

            clean_list = []
            for _, row in df.iterrows():
                ma = str(row.get('MÃ SỐ MÁY', '')).strip()
                if not ma or ma.upper() in ["NAN", "STT", "0"]: continue
                
                # Lay du lieu cac truong theo dien giai cua sep
                kiem_tra_tt = str(row.get('KIỂM TRA THỰC TẾ', '')).upper().strip()
                sua_ngoai = str(row.get('SỬA BÊN NGOÀI', '')).upper().strip()
                hu_hong = str(row.get('HƯ KHÔNG SỬA ĐƯỢC', '')).upper().strip()
                
                # Xac dinh cot Giao Lai theo tung mien
                col_giao_lai = 'GIAO LẠI MIỀN BẮC' if region == "MIEN BAC" else 'GIAO LẠI ĐN'
                giao_lai = str(row.get(col_giao_lai, '')).upper().strip()

                # --- LOGIC NGHIEP VU MOI ---
                status = ""
                
                # 1. Logic Thanh Ly (Uu tien cao nhat)
                # Neu Kiem tra hoac Sua ngoai co chu "THANH LY" hoac "KHONG SUA DUOC"
                keywords_tl = ["THANH LÝ", "KHÔNG SỬA ĐƯỢC", "HỎNG", "HU KHONG SUA DUOC"]
                if any(x in kiem_tra_tt for x in keywords_tl) or \
                   any(x in sua_ngoai for x in keywords_tl) or \
                   hu_hong != "":
                    status = "🔴 THANH LÝ"
                
                # 2. Logic Da Tra Ve (R)
                # Kiem tra thuc te hoac Sua ngoai la "OK" VA Giao lai la "R"
                elif (("OK" in kiem_tra_tt) or ("OK" in sua_ngoai)) and (giao_lai == "R"):
                    status = "🟢 ĐÃ TRẢ VỀ"
                
                # 3. Logic Kho Nhan (Sua xong nhung chua giao)
                # Sua ngoai la "OK" nhung Giao lai chua phai la "R"
                elif ("OK" in sua_ngoai) and (giao_lai != "R"):
                    status = "🔵 KHO NHẬN (ĐỐI CHIẾU)"
                
                # 4. Cac truong hop con lai
                else:
                    status = "🟡 ĐANG XỬ LÝ"

                clean_list.append({
                    "CHI NHANH": region,
                    "MA MAY": ma,
                    "TRANG THAI": status,
                    "NGAY NHAN": pd.to_datetime(row.get('NGÀY NHẬN', ''), dayfirst=True, errors='coerce'),
                    "LOAI MAY": row.get('LOẠI MÁY', ''),
                    "KIEM TRA": kiem_tra_tt,
                    "SUA NGOAI": sua_ngoai,
                    "GIAO LAI": giao_lai
                })
            final_df = pd.concat([final_df, pd.DataFrame(clean_list)], ignore_index=True)
        except: continue
    return final_df

# --- 2. GIAO DIEN ---
df = load_and_process_logic()
st.title("🏭 HỆ THỐNG QUẢN TRỊ KHO V1.3 - LOGISTICS FLOW")

if not df.empty:
    # KPI Tong hop
    total_received = len(df)
    thanh_ly_count = len(df[df['TRANG THAI'] == "🔴 THANH LÝ"])
    thuc_te_van_hanh = total_received - thanh_ly_count # Tong may nhan tru may thanh ly
    da_tra_count = len(df[df['TRANG THAI'] == "🟢 ĐÃ TRẢ VỀ"])
    kho_nhan_count = len(df[df['TRANG THAI'] == "🔵 KHO NHẬN (ĐỐI CHIẾU)"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng Máy Nhận (Gốc)", total_received)
    c2.metric("Máy Thanh Lý", thanh_ly_count, delta="Trừ khỏi tổng", delta_color="inverse")
    c3.metric("Thực Nhận (Vận hành)", thuc_te_van_hanh)
    c4.metric("Đã Trả Miền", da_tra_count)

    st.write("---")
    
    # Kho Nhan Doi Chieu
    st.info(f"🚩 **Kho Nhận (Đang đối chiếu):** Có **{kho_nhan_count}** máy đã sửa xong (OK) nhưng chưa xác nhận 'R' để trả về miền.")

    # Biểu đồ trạng thái theo sếp diễn giải
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.plotly_chart(px.pie(df, names='TRANG THAI', title="Tỷ lệ phân bổ Kho", 
                               color='TRANG THAI', color_discrete_map={
                                   "🔴 THANH LÝ": "#EF553B", 
                                   "
