import streamlit as st
import pandas as pd
from supabase import create_client

# 1. Kết nối (Giữ nguyên)
url = "https://cigbnbaanpebwrufzxfg.supabase.co"
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("🔍 Checkpoint 3: Chuẩn hóa nghiệp vụ")

try:
    res = supabase.table("repair_cases").select("*").execute()
    df = pd.DataFrame(res.data)

    # --- THỰC THI CHUẨN HÓA ---
    
    # A. Ép kiểu số cho tiền bạc (Quan trọng nhất)
    df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)
    
    # B. Xử lý ngày tháng (Nới lỏng bộ lọc để không mất dòng)
    df['date_dt'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
    df['NĂM'] = df['date_dt'].dt.year.fillna(0).astype(int) # Năm 0 là hàng chưa xác nhận ngày
    
    # C. Fix lỗi font Tiếng Việt (Dựa trên file CSV sếp gửi)
    encoding_fix = {
        "Miá» n Trung": "Miền Trung",
        "Miá» n Báº¯c": "Miền Bắc",
        "Miá» n Nam": "Miền Nam",
        "VÅ© Há»“ng Yáº¿n": "Vũ Hồng Yến"
    }
    df['branch'] = df['branch'].replace(encoding_fix)
    df['customer_name'] = df['customer_name'].replace(encoding_fix)

    # --- HIỂN THỊ KẾT QUẢ KIỂM TRA ---
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Tổng ngân sách bồi thường", f"{df['CHI_PHÍ'].sum():,.0f} đ")
    c2.metric("📋 Tổng số ca ghi nhận", f"{len(df)} ca")
    c3.metric("🏢 Số chi nhánh", f"{df['branch'].nunique()}")

    st.write("### 📊 Kiểm tra dữ liệu sau khi "Sạch"")
    st.dataframe(df[['confirmed_date', 'branch', 'customer_name', 'CHI_PHÍ']].head(10))

    if df['CHI_PHÍ'].sum() == 0:
        st.info("💡 Lưu ý: Cột bồi thường đang bằng 0, sếp kiểm tra lại xem có phải do trong DB đang để 'false' hết không nhé.")
    
    st.success("Nếu các con số Metric phía trên đã nhảy (không còn là 0), sếp báo tôi để mình sang Bước 4: Lên giao diện Dashboard cuối cùng!")

except Exception as e:
    st.error(f"❌ Lỗi bước 3: {e}")
