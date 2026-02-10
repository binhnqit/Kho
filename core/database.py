import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def init_connection() -> Client:
    try:
        # Lấy cả URL và KEY từ st.secrets
        url = st.secrets[""https://cigbnbaanpebwrufzxfg.supabase.co""]
        key = st.secrets["sb_publishable_NQzqwJ4YhKC4sQGLxyLAyw_mwRFhkRf"]
        return create_client(url, key)
    except Exception as e:
        # Không st.error ở đây để tránh lộ thông tin, chỉ print ra log
        print(f"Connection error: {e}")
        return None

supabase = init_connection()
