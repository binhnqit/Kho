import streamlit as st
import pandas as pd
from supabase import create_client

# 1. Kết nối
url = "https://cigbnbaanpebwrufzxfg.supabase.co"
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("🔍 Checkpoint 2: Soi nguyên liệu thô")

try:
    # 2. Lấy 5 dòng đầu tiên với tất cả các cột
    res = supabase.table("repair_cases").select("*").limit(5).execute()
    
    if res.data:
        st.success(f"✅ ĐÃ THÔNG! Tìm thấy {len(res.data)} dòng.")
        df = pd.DataFrame(res.data)
        
        st.write("### 📋 Bảng dữ liệu thực tế từ DB:")
        st.dataframe(df)
        
        st.write("### 🧪 Phân tích kỹ thuật:")
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Tên các cột nhận được:**")
            st.write(df.columns.tolist())
        with c2:
            st.write("**Kiểm tra cột Quan trọng:**")
            st.write(f"- Cột 'confirmed_date' có dữ liệu không? {'✅ Có' if 'confirmed_date' in df.columns else '❌ Không'}")
            st.write(f"- Cột 'compensation' có dữ liệu không? {'✅ Có' if 'compensation' in df.columns else '❌ Không'}")
            
        st.info("Sếp hãy kiểm tra xem dữ liệu hiện ra có bị lỗi font Tiếng Việt hay không rồi báo tôi nhé!")
    else:
        st.error("❌ Vẫn chưa thấy dữ liệu. Sếp hãy kiểm tra lại xem đã bấm 'Save' Policy trên Supabase chưa?")

except Exception as e:
    st.error(f"❌ Lỗi: {e}")
