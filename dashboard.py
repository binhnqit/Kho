import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from datetime import datetime

# --- 1. KẾT NỐI ---
url = "https://cigbnbaanpebwrufzxfg.supabase.co"
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- 2. HÀM XỬ LÝ (TRÁI TIM CỦA APP) ---
@st.cache_data(ttl=60)
def load_repair_data_final():
    try:
        res = supabase.table("repair_cases").select("*").execute()
        if not res.data: return pd.DataFrame()
        df = pd.DataFrame(res.data)

        # 1. TRỌNG TÂM: Lấy ngày từ cột confirmed_date
        df['date_dt'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        
        # Loại bỏ các dòng không có ngày xác nhận hợp lệ
        df = df.dropna(subset=['date_dt'])

        # 2. TRÍCH XUẤT THÔNG TIN THỜI GIAN ĐỂ LỌC
        df['NĂM'] = df['date_dt'].dt.year.astype(int)
        df['THÁNG'] = df['date_dt'].dt.month.astype(int)
        
        # Chuyển tên thứ sang tiếng Việt để vẽ biểu đồ
        day_map = {'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
                   'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ Nhật'}
        df['THỨ'] = df['date_dt'].dt.day_name().map(day_map)

        # 3. CHUẨN HÓA SỐ TIỀN & CHI NHÁNH
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)
        
        # Gộp các miền bị lỗi font (ví dụ: Miá» n Nam -> Miền Nam)
        encoding_dict = {"Miá» n Trung": "Miền Trung", "Miá» n Báº¯c": "Miền Bắc", "Miá» n Nam": "Miền Nam"}
        df['branch'] = df['branch'].replace(encoding_dict)

        return df
    except Exception as e:
        st.error(f"Lỗi tải dữ liệu: {e}")
        return pd.DataFrame()

# --- 3. GIAO DIỆN ---
def main():
    st.set_page_config(page_title="4ORANGES OPS 2026", layout="wide", page_icon="🎨")
    
    # 1. LOAD DỮ LIỆU CHUNG (Dùng chung cho cả 2 Tab)
    df_db = load_repair_data_final()
    
    # 2. KHỞI TẠO TABS
    tab_dash, tab_admin = st.tabs(["📊 BÁO CÁO VẬN HÀNH", "📥 QUẢN TRỊ"])

    # --- TAB 1: BÁO CÁO VẬN HÀNH ---
    with tab_dash:
        if df_db.empty:
            st.info("Chưa có dữ liệu hợp lệ. Vui lòng kiểm tra lại Database hoặc nạp dữ liệu ở Tab Quản trị.")
        else:
            # --- A. SIDEBAR (Chỉ hiện khi ở Tab Báo cáo) ---
            with st.sidebar:
                st.header("⚙️ BỘ LỌC")
                if st.button("🔄 LÀM MỚI DỮ LIỆU", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()
                st.divider()
                
                # Logic chọn Năm/Tháng
                available_years = sorted(df_db['NĂM'].unique(), reverse=True)
                sel_year = st.selectbox("📅 Chọn năm", options=available_years, key="year_filter")
                
                available_months = sorted(df_db[df_db['NĂM'] == sel_year]['THÁNG'].unique().tolist())
                sel_month = st.selectbox("📆 Chọn tháng", options=["Tất cả"] + available_months, key="month_filter")

            # --- B. LỌC DỮ LIỆU VIEW ---
            df_view = df_db[df_db['NĂM'] == sel_year].copy()
            if sel_month != "Tất cả":
                df_view = df_view[df_view['THÁNG'] == sel_month]

            # --- C. HIỂN THỊ KPI ---
            month_label = f"Tháng {sel_month}" if sel_month != "Tất cả" else "Cả năm"
            st.title(f"📈 Báo cáo vận hành {month_label} / {sel_year}")
            
            c1, c2, c3 = st.columns(3)
            # Dữ liệu CHI_PHÍ đã được ép kiểu numeric trong SQL nên sum() sẽ ra kết quả chuẩn
            c1.metric("💰 TỔNG CHI PHÍ", f"{df_view['CHI_PHÍ'].sum():,.0f} đ")
            c2.metric("🛠️ SỐ CA SỬA CHỮA", f"{len(df_view)} ca")
            top_branch = df_view['branch'].value_counts().idxmax() if not df_view.empty else "N/A"
            c3.metric("🏢 CHI NHÁNH NHIỀU CA NHẤT", top_branch)

            st.divider()

            # --- D. BIỂU ĐỒ & BẢNG ---
            col_chart, col_table = st.columns([6, 4])
            with col_chart:
                st.subheader("📅 Xu hướng sự vụ theo thứ")
                order = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ Nhật']
                day_stats = df_view['THỨ'].value_counts().reindex(order).fillna(0).reset_index()
                day_stats.columns = ['THỨ', 'SỐ_CA']
                fig = px.line(day_stats, x='THỨ', y='SỐ_CA', markers=True, color_discrete_sequence=['#00CC96'])
                fig.update_layout(height=350, margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)

            with col_table:
                st.subheader("📋 10 ca mới cập nhật")
                # Hiển thị mã máy vừa nạp (ví dụ 1366) ở ngay đây
                st.dataframe(
                    df_view.sort_values('date_dt', ascending=False).head(10)[['date_dt', 'branch', 'machine_id', 'CHI_PHÍ']],
                    use_container_width=True, hide_index=True
                )

            with st.expander("🔎 Xem toàn bộ dữ liệu chi tiết đã lọc"):
                st.dataframe(df_view.sort_values('date_dt', ascending=False), use_container_width=True)

    # --- TAB 2: QUẢN TRỊ (Phần sếp vừa yêu cầu) ---
    
    with tab_admin:
        st.title("📥 HỆ THỐNG QUẢN TRỊ DỮ LIỆU")
        
        # Chia 2 cột: Một bên nạp file, một bên nhập tay
        col_import, col_manual = st.columns([1, 1])

        # --- PHẦN 1: IMPORT FILE CSV ---
        with col_import:
            st.subheader("📂 Import từ File CSV")
            st.info("💡 Mẹo: File CSV nên có cột `machine_id`, `branch`, `compensation`...")
            uploaded_file = st.file_uploader("Chọn file CSV", type=["csv"], key="csv_upload")
            
            if uploaded_file:
                df_up = pd.read_csv(uploaded_file)
                
                # Tiền xử lý dữ liệu trước khi đẩy lên Cloud
                if 'compensation' in df_up.columns:
                    df_up['compensation'] = pd.to_numeric(df_up['compensation'], errors='coerce').fillna(0).astype(float)
                
                # Đảm bảo machine_id là dạng chữ (tránh lỗi UUID cũ)
                if 'machine_id' in df_up.columns:
                    df_up['machine_id'] = df_up['machine_id'].astype(str)
                
                st.write("👀 Xem trước 3 dòng:")
                st.dataframe(df_up.head(3), use_container_width=True)
                
                if st.button("🚀 Xác nhận Upload", use_container_width=True, type="primary"):
                    try:
                        data_to_upsert = df_up.to_dict(orient='records')
                        res = supabase.table("repair_cases").upsert(data_to_upsert).execute()
                        if res.data:
                            st.success(f"✅ Đã nạp {len(res.data)} dòng thành công!")
                            st.cache_data.clear() # Xóa cache để dashboard cập nhật
                            st.balloons()
                    except Exception as e:
                        st.error(f"❌ Lỗi nạp dữ liệu: {e}")

        # --- PHẦN 2: NHẬP LIỆU THỦ CÔNG (ĐÃ FIX UUID & BOOLEAN) ---
        with col_manual:
            st.subheader("✍️ Thêm ca sửa chữa mới")
            # Sử dụng key duy nhất để tránh xung đột Form
            with st.form(key="form_nhap_lieu_chuan_2026", clear_on_submit=True):
                m_c1, m_c2 = st.columns(2)
                with m_c1:
                    # Ngày này sẽ là trục chính để lọc Dashboard
                    f_date = st.date_input("Ngày xác nhận", value=datetime.now())
                    f_branch = st.selectbox("Chi nhánh", ["Miền Bắc", "Miền Trung", "Miền Nam"])
                with m_c2:
                    # Đã ép kiểu String để tránh lỗi UUID cũ
                    f_machine = st.text_input("Mã số máy (Machine ID)") 
                    f_cost = st.number_input("Chi phí thực tế (đ)", min_value=0, step=10000)

                f_customer = st.text_input("Tên khách hàng")
                # Để trống nếu không có lý do để tránh lệch dòng hiển thị
                f_reason = st.text_area("Lý do hư hỏng", height=68, placeholder="Nhập chi tiết lỗi tại đây...")
                
                submit_manual = st.form_submit_button("💾 Lưu vào hệ thống", use_container_width=True, type="primary")

                if submit_manual:
                    if not f_machine or not f_customer:
                        st.warning("⚠️ Sếp ơi, Mã máy và Tên khách là bắt buộc!")
                    else:
                        try:
                            # 🛠️ ĐỒNG BỘ DỮ LIỆU ĐỂ KHÔNG LỆCH DÒNG
                            new_record = {
                                "confirmed_date": f_date.isoformat(), # Trục lọc chính
                                "branch": f_branch,                   # Phân loại vùng miền
                                "machine_id": str(f_machine).strip(), # Fix lỗi UUID
                                "compensation": float(f_cost),        # Fix lỗi 0đ (Numeric)
                                "customer_name": f_customer.strip(),
                                "issue_reason": f_reason.strip() if f_reason else "N/A",
                                "created_at": datetime.now().isoformat() # Ngày hệ thống
                            }
                            
                            # Gửi lên Supabase
                            res = supabase.table("repair_cases").insert(new_record).execute()
                            
                            if res.data:
                                st.success(f"✅ Đã lưu thành công ca máy: {f_machine}")
                                # ⚡ Xóa cache để Tab Dashboard cập nhật ngay con số mới
                                st.cache_data.clear()
                                st.balloons()
                        except Exception as e:
                            # Cảnh báo nếu RLS hoặc kiểu dữ liệu vẫn chưa khớp hoàn toàn
                            st.error(f"❌ Lỗi ghi dữ liệu: {e}")

        # --- PHẦN 3: BỘ CÔNG CỤ DỌN DẸP DỮ LIỆU ---
        st.divider()
        with st.expander("🛠️ CÔNG CỤ DỌN DẸP HỆ THỐNG (ADMIN ONLY)"):
            st.warning("Cẩn thận: Các thao tác này sẽ thay đổi dữ liệu trực tiếp trên Cloud.")
            c_clean1, c_clean2, c_clean3 = st.columns(3)
            
            with c_clean1:
                if st.button("🧹 Xóa dòng 'Trống chi nhánh'"):
                    # Xóa các ca mà branch là null do sếp thấy trong SQL trước đó
                    supabase.table("repair_cases").delete().is_("branch", "null").execute()
                    st.info("Đã quét sạch dòng trống!")
                    st.cache_data.clear()
            
            with c_clean2:
                if st.button("🔠 Sửa lỗi Font 3 Miền"):
                    # Tự động gộp các miền lỗi font về tên chuẩn để Dashboard hiện đúng số 3
                    maps = {"Miá» n Nam": "Miền Nam", "Miá» n Trung": "Miền Trung", "Miá» n Báº¯c": "Miền Bắc"}
                    for old, new in maps.items():
                        supabase.table("repair_cases").update({"branch": new}).eq("branch", old).execute()
                    st.success("Đã chuẩn hóa tên miền!")
                    st.cache_data.clear()

            with c_clean3:
                if st.button("♻️ Làm mới toàn bộ App"):
                    st.cache_data.clear()
                    st.rerun()
        # --- PHẦN 2: NHẬP THỦ CÔNG (ĐÃ FIX LỖI 22P02) ---
        with col_manual:
            st.subheader("✍️ Thêm ca sửa chữa mới")
            # Đổi key thành 'form_quan_tri_2026' để không bao giờ trùng
            with st.form(key="form_quan_tri_2026", clear_on_submit=True):
                m_c1, m_c2 = st.columns(2)
                with m_c1:
                    f_date = st.date_input("Ngày xác nhận", value=datetime.now())
                    f_branch = st.selectbox("Chi nhánh", ["Miền Bắc", "Miền Trung", "Miền Nam"])
                with m_c2:
                    f_machine = st.text_input("Mã số máy (Machine ID)") 
                    f_cost = st.number_input("Chi phí thực tế (đ)", min_value=0, step=10000)

                f_customer = st.text_input("Tên khách hàng")
                f_reason = st.text_area("Lý do hư hỏng", height=68)
                
                # Nút bấm cũng nên có style primary cho chuyên nghiệp
                submit_manual = st.form_submit_button("💾 Lưu vào hệ thống", use_container_width=True, type="primary")

                if submit_manual:
                    if not f_machine or not f_customer:
                        st.warning("⚠️ Sếp điền thiếu thông tin rồi!")
                    else:
                        try:
                            new_record = {
                                "confirmed_date": f_date.isoformat(),
                                "branch": f_branch,
                                "machine_id": str(f_machine).strip(),
                                "compensation": float(f_cost),
                                "customer_name": f_customer,
                                "issue_reason": f_reason,
                                "created_at": datetime.now().isoformat()
                            }
                            res = supabase.table("repair_cases").insert(new_record).execute()
                            if res.data:
                                st.success(f"✅ Đã lưu thành công ca máy: {f_machine}")
                                st.cache_data.clear()
                        except Exception as e:
                            st.error(f"❌ Vẫn còn lỗi: {e}")

        # --- PHẦN 3: CÔNG CỤ DỌN RÁC SIÊU MẠNH ---
        st.divider()
        with st.expander("🛠️ CÔNG CỤ QUẢN TRỊ NÂNG CAO"):
            st.warning("Cẩn thận: Các thao tác này sẽ thay đổi dữ liệu trực tiếp trên Cloud.")
            
            c_clean1, c_clean2 = st.columns(2)
            
            with c_clean1:
                if st.button("🧹 Xóa ca 'Chi nhánh trống'"):
                    res = supabase.table("repair_cases").delete().is_("branch", "null").execute()
                    st.info(f"Đã dọn dẹp các dòng lỗi!")
                    st.cache_data.clear()
            
            with c_clean2:
                # Công cụ này giúp sếp fix lỗi font hàng loạt bằng SQL ẩn
                if st.button("🔠 Sửa lỗi Font hàng loạt"):
                    st.write("Đang quét và sửa lỗi font...")
                    # Sửa lỗi font trực tiếp cho 3 miền
                    for old, new in {"Miá» n Nam": "Miền Nam", "Miá» n Trung": "Miền Trung", "Miá» n Báº¯c": "Miền Bắc"}.items():
                        supabase.table("repair_cases").update({"branch": new}).eq("branch", old).execute()
                    st.success("Đã chuẩn hóa tên chi nhánh!")
                    st.cache_data.clear()

if __name__ == "__main__":
    main()
