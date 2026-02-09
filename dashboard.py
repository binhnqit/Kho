import streamlit as st
from supabase import create_client

url = "https://cigbnbaanpebwrufzxfg.supabase.co"
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.write("### 🔍 Checkpoint 1: Kết nối thô")
res = supabase.table("repair_cases").select("id").limit(5).execute()
st.write("Kết quả trả về:", res.data)
