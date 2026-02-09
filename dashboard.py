import streamlit as st
import pandas as pd
from supabase import create_client

# --- KẾT NỐI ---
SUPABASE_URL = "https://cigbnbaanpebwrufzxfg.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("🛠️ HỆ THỐNG KIỂM TRA DỮ LIỆU CẤP CAO")

# --- HÀM LOAD DỮ LIỆU KHÔNG BỘ LỌC ---
def force_load_data():
    try:
        # Lấy sạch sành sanh mọi thứ, không sắp xếp, không lọc
        res = supabase.table("repair_cases").select("*").execute()
        return res.data
    except Exception as e:
        st.error(f"📡 Lỗi kết nối DB: {e}")
        return None

data = force_load_data()

if data is not None:
    if len(data) == 0:
        st.warning("⚠️ Supabase báo bảng 'repair_cases' ĐANG TRỐNG HOÀN TOÀN.")
        st.info("Sếp hãy kiểm tra lại Policy (RLS) trên Supabase hoặc xem lại bước nạp dữ liệu.")
    else:
        st.success(f"✅ Đã 'túm' được {len(data)} dòng dữ liệu!")
        df_raw = pd.DataFrame(data)
        
        # KIỂM TRA CỘT QUAN TRỌNG
        st.subheader("🔍 Soi dữ liệu thô")
        st.write("Dưới đây là những gì thực sự nằm trong DB của sếp:")
        st.dataframe(df_raw)

        # KIỂM TRA ĐỊNH DẠNG NGÀY
        if 'confirmed_date' in df_raw.columns:
            null_dates = df_raw['confirmed_date'].isnull().sum()
            st.write(f"📅 Số dòng bị trống ngày xác nhận: **{null_dates}**")
            st.write("Định dạng ngày mẫu:", df_raw['confirmed_date'].iloc[0] if len(df_raw)>0 else "N/A")
else:
    st.error("Không thể kết nối tới Supabase. Kiểm tra lại URL và KEY.")
