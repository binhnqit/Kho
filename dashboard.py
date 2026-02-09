import streamlit as st
import pandas as pd
from supabase import create_client

# --- 1. KẾT NỐI ---
SUPABASE_URL = "https://cigbnbaanpebwrufzxfg.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") # Đảm bảo đã set trong Secrets
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("🔍 KIỂM TRA DỮ LIỆU REPAIR_CASES")

# --- 2. HÀM TRUY VẤN THỬ NGHIỆM ---
def check_database():
    try:
        # Lấy thử 10 dòng, không lọc bất kỳ cái gì để xem bảng có gì không
        res = supabase.table("repair_cases").select("*").limit(10).execute()
        
        if not res.data:
            st.error("❌ Supabase trả về danh sách TRỐNG []")
            st.info("💡 Sếp kiểm tra lại: Bảng 'repair_cases' trên giao diện Supabase Dashboard có dòng nào không?")
            return None
        
        return res.data
    except Exception as e:
        st.error(f"❌ Lỗi kết nối kỹ thuật: {e}")
        return None

raw_data = check_database()

if raw_data:
    st.success(f"✅ Tìm thấy {len(raw_data)} dòng dữ liệu thô!")
    df_raw = pd.DataFrame(raw_data)
    
    # Hiển thị bảng thô để sếp soi tên cột
    st.write("📊 **Dữ liệu thô từ Database (Sếp soi kỹ tên cột ở đây):**")
    st.dataframe(df_raw)

    # --- 3. KIỂM TRA LOGIC NGÀY THÁNG ---
    # Đây là lý do hay gặp nhất: Dữ liệu có nhưng filter ngày sai nên Dashboard trắng tinh
    if 'confirmed_date' in df_raw.columns:
        st.write("📅 Cột 'confirmed_date' hiện tại đang có giá trị:", df_raw['confirmed_date'].unique())
    else:
        st.warning("⚠️ Cảnh báo: Không tìm thấy cột 'confirmed_date' trong dữ liệu trả về!")
