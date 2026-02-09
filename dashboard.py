import streamlit as st
import pandas as pd
from supabase import create_client

# 1. Kết nối
url = "https://cigbnbaanpebwrufzxfg.supabase.co"
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("🔍 Checkpoint 3: Chuẩn hóa nghiệp vụ (Fixed)")

try:
    # Truy vấn dữ liệu
    res = supabase.table("repair_cases").select("*").execute()
    if not res.data:
        st.warning("⚠️ Bảng trống hoặc lỗi RLS.")
    else:
        df = pd.DataFrame(res.data)

        # --- THỰC THI CHUẨN HÓA ---
        
        # A. Ép kiểu số cho tiền bạc
        # errors='coerce' giúp biến các chữ như "false" thành NaN, sau đó fillna(0) biến nó thành số 0
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)
        
        # B. Xử lý ngày tháng
        df['date_dt'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        df['NĂM'] = df['date_dt'].dt.year.fillna(0).astype(int)
        
        # C. Fix lỗi font Tiếng Việt (Encoding fix)
        # Sửa lỗi font 'Miá» n Trung' -> 'Miền Trung'
        encoding_fix = {
            "Miá» n Trung": "Miền Trung",
            "Miá» n Báº¯c": "Miền Bắc",
            "Miá» n Nam": "Miền Nam",
            "VÅ© Há»“ng Yáº¿n": "Vũ Hồng Yến"
        }
        df['branch'] = df['branch'].replace(encoding_fix)
        df['customer_name'] = df['customer_name'].replace(encoding_fix)

        # --- HIỂN THỊ KẾT QUẢ ---
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Tổng ngân sách", f"{df['CHI_PHÍ'].sum():,.0f} đ")
        c2.metric("📋 Tổng số ca", f"{len(df)} ca")
        c3.metric("🏢 Số chi nhánh", f"{df['branch'].nunique()}")

        st.write("### 📊 Kiểm tra dữ liệu sau khi làm sạch")
        # Chỉ hiển thị các cột quan trọng để sếp soi
        st.dataframe(df[['confirmed_date', 'branch', 'customer_name', 'CHI_PHÍ']].head(10))

        if df['CHI_PHÍ'].sum() == 0:
            st.info("💡 Lưu ý: Cột bồi thường đang bằng 0 (do trong DB là 'false').")
        
        st.success("✅ Đã xử lý xong lỗi Syntax! Sếp thấy Metric nhảy số chưa?")

except Exception as e:
    st.error(f"❌ Lỗi bước 3: {e}")
    
