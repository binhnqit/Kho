import streamlit as st
import hashlib
from datetime import datetime
from core.database import supabase

# Hàm băm mật khẩu bảo mật hơn
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def render_auth_interface():
    # CSS Custom theo phong cách Apple (Glassmorphism)
    st.markdown("""
        <style>
        .auth-container {
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.1);
        }
        .stButton>button {
            border-radius: 12px;
            transition: all 0.3s;
        }
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.image("https://cdn-icons-png.flaticon.com/512/508/508757.png", width=80) # Icon tùy chọn
        st.title("🔧 OPS Portal")
        
        # Apple-style Segmented Control
        mode = st.radio("Chọn hình thức", ["Đăng nhập", "Tạo tài khoản"], horizontal=True, label_visibility="collapsed")
        
        st.markdown("<div class='auth-container'>", unsafe_allow_html=True)
        
        if mode == "Đăng nhập":
            login_form()
        else:
            registration_form()
            
        st.markdown("</div>", unsafe_allow_html=True)

def registration_form():
    st.subheader("📝 Đăng ký")
    with st.form("reg_form", clear_on_submit=True):
        new_user = st.text_input("Username", placeholder="ví dụ: nva_01")
        new_name = st.text_input("Full Name", placeholder="Nguyễn Văn A")
        new_pass = st.text_input("Password", type="password")
        confirm_pass = st.text_input("Confirm Password", type="password")
        role = st.selectbox("Vai trò", ["Nhân viên", "Quản lý", "Admin"])
        
        submit_btn = st.form_submit_button("Tạo tài khoản", use_container_width=True)

        if submit_btn:
            if not new_user or not new_pass or not new_name:
                st.error("Vui lòng không để trống thông tin quan trọng.")
            elif new_pass != confirm_pass:
                st.error("Mật khẩu xác nhận không khớp.")
            else:
                try:
                    exists = supabase.table("users").select("*").eq("username", new_user).execute()
                    if exists.data:
                        st.error("Tên đăng nhập này đã có người sử dụng.")
                    else:
                        user_data = {
                            "username": new_user,
                            "full_name": new_name,
                            "password": hash_password(new_pass),
                            "role": role
                            # Không cần created_at vì DB tự sinh
                        }
                        supabase.table("users").insert(user_data).execute()
                        st.success("Tạo tài khoản thành công! Mời bạn đăng nhập.")
                except Exception as e:
                    st.error(f"Lỗi hệ thống: {str(e)}")

def login_form():
    st.subheader("🔐 Đăng nhập")
    with st.form("login_form"):
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        submit_btn = st.form_submit_button("Truy cập hệ thống", type="primary", use_container_width=True)

        if submit_btn:
            try:
                res = supabase.table("users").select("*").eq("username", user).execute()
                if res.data and hash_password(pw) == res.data[0]['password']:
                    st.session_state["is_logged_in"] = True
                    st.session_state["user_info"] = res.data[0]
                    st.toast(f"Chào mừng trở lại, {res.data[0]['full_name']}!", icon="👋")
                    st.rerun()
                else:
                    st.error("Thông tin đăng nhập không chính xác.")
            except Exception as e:
                st.error("Kết nối Database thất bại.")
