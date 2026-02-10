# core/database.py
import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def init_connection() -> Client:
    """Khởi tạo và cache kết nối tới Supabase dự án cigbnbaanpebwrufzxfg"""
    try:
        # Sử dụng URL của bạn và Key từ Secrets
        url = "https://cigbnbaanpebwrufzxfg.supabase.co"
        key = st.secrets["SUPABASE_KEY"]
        
        return create_client(url, key)
    except Exception as e:
        st.error(f"❌ Không thể kết nối Supabase: {e}")
        return None

# Export instance này để tất cả các file khác dùng chung
supabase = init_connection()
