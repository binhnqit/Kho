import pandas as pd
from supabase import create_client
import streamlit as st

# Kết nối (Dùng thông tin của sếp)
url = "https://cigbnbaanpebwrufzxfg.supabase.co"
key = st.secrets.get("SUPABASE_KEY", "sb_publishable_NQzqwJ4YhKC4sQGLxyLAyw_mwRFhkRf")
supabase = create_client(url, key)

st.title("🔍 KIỂM TRA DỮ LIỆU THỰC TẾ")

try:
    # 1. Kiểm tra 5 dòng cuối cùng của bảng repair_cases
    res = supabase.table("repair_cases").select("*").limit(5).execute()
    
    if res.data:
        df_check = pd.DataFrame(res.data)
        st.write("✅ 5 dòng dữ liệu thực tế trong DB:")
        st.dataframe(df_check)
        
        st.write("📊 Chi tiết kiểu dữ liệu từng cột:")
        st.write(df_check.dtypes)
    else:
        st.warning("⚠️ Database bảng 'repair_cases' hiện đang hoàn toàn trống!")

    # 2. Kiểm tra bảng machines xem có dữ liệu chưa
    m_res = supabase.table("machines").select("id, machine_code").limit(3).execute()
    st.write("⚙️ Kiểm tra bảng Machines:", m_res.data)

except Exception as e:
    st.error(f"❌ Lỗi khi truy vấn: {e}")
