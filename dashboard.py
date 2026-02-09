import streamlit as st
from supabase import create_client

# 1. Khởi tạo kết nối
url = "https://cigbnbaanpebwrufzxfg.supabase.co"
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("🔍 Checkpoint 1: Kiểm tra ống dẫn")

# 2. Thử lấy 1 dòng duy nhất từ bảng
try:
    res = supabase.table("repair_cases").select("id").limit(1).execute()
    
    if res.data:
        st.success("✅ THÔNG SUỐT! Supabase đã trả về dữ liệu.")
        st.write("Dữ liệu mẫu nhận được:", res.data)
        st.info("Sếp hãy báo cho tôi để mình sang Bước 2 (Kiểm tra nguyên liệu).")
    else:
        st.warning("⚠️ CỬA ĐÓNG! Kết nối thành công nhưng danh sách trả về rỗng [ ].")
        st.error("Lý do: Có thể sếp chưa cấu hình Policy (RLS) trên Supabase.")
        
except Exception as e:
    st.error(f"❌ GÃY KẾT NỐI: {e}")
