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

        # 1. FIX CHI NHÁNH & BỎ DÒNG TRỐNG (Như sếp yêu cầu)
        # Loại bỏ các dòng mà cột branch bị trống hoặc null
        df = df.dropna(subset=['branch'])
        df = df[df['branch'].str.strip() != ""] 

        # Sửa lỗi font để gộp về đúng 3 miền
        encoding_dict = {
            "Miá» n Trung": "Miền Trung", "Miá» n Báº¯c": "Miền Bắc", "Miá» n Nam": "Miền Nam",
            "Miá» n Báº°c": "Miền Bắc" # Dự phòng thêm ký tự lạ khác
        }
        df['branch'] = df['branch'].replace(encoding_dict)

        # 2. FIX NGÀY THÁNG: ƯU TIÊN CỘT 5 (created_at) VÌ CỘT 2 ĐANG SAI (2223)
        # Chúng ta dùng created_at để lấy đúng mốc năm 2026
        df['date_dt'] = pd.to_datetime(df['created_at'], errors='coerce')
        
        # Bỏ qua các dòng không có ngày hợp lệ
        df = df.dropna(subset=['date_dt'])

        # Trích xuất Năm/Tháng/Thứ từ cột chuẩn
        df['NĂM'] = df['date_dt'].dt.year.astype(int)
        df['THÁNG'] = df['date_dt'].dt.month.astype(int)
        day_map = {'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
                   'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ Nhật'}
        df['THỨ'] = df['date_dt'].dt.day_name().map(day_map)

        # 3. FIX CHI PHÍ: ÉP KIỂU SỐ (Để không bị ra 0đ)
        df['compensation'] = df['compensation'].apply(lambda x: 0 if str(x).lower() == 'false' else x)
        df['CHI_PHÍ'] = pd.to_numeric(df['compensation'], errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Lỗi xử lý: {e}")
        return pd.DataFrame()

# --- 3. GIAO DIỆN ---
def main():
    st.set_page_config(page_title="4ORANGES OPS 2026", layout="wide", page_icon="🎨")
    tab_dash, tab_admin = st.tabs(["📊 BÁO CÁO VẬN HÀNH", "📥 QUẢN TRỊ"])

    with tab_dash:
        df_db = load_repair_data_final()
        
        if df_db.empty:
            st.info("Chưa có dữ liệu hợp lệ. Vui lòng kiểm tra lại Database.")
        else:
            # --- A. KHỞI TẠO SESSION STATE (CHỐNG GIẬT UX) ---
            available_years = sorted(df_db['NĂM'].unique(), reverse=True)
            
            if 'sel_year' not in st.session_state:
                st.session_state.sel_year = available_years[0]
            if 'sel_month' not in st.session_state:
                st.session_state.sel_month = "Tất cả"

            # --- B. SIDEBAR CẤU HÌNH ---
            with st.sidebar:
                st.header("⚙️ BỘ LỌC")
                if st.button("🔄 LÀM MỚI DỮ LIỆU", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()
                
                st.divider()
                
                # Chọn Năm
                sel_year = st.selectbox(
                    "📅 Chọn năm",
                    options=available_years,
                    index=available_years.index(st.session_state.sel_year),
                    key="sel_year_widget" # Tránh trùng key với session_state
                )
                st.session_state.sel_year = sel_year

                # Lọc danh sách tháng dựa trên năm đã chọn
                available_months = sorted(df_db[df_db['NĂM'] == sel_year]['THÁNG'].unique().tolist())
                
                # Chọn Tháng
                sel_month = st.selectbox(
                    "📆 Chọn tháng",
                    options=["Tất cả"] + available_months,
                    index=0 if st.session_state.sel_month == "Tất cả" else (available_months.index(st.session_state.sel_month) + 1 if st.session_state.sel_month in available_months else 0),
                    key="sel_month_widget"
                )
                st.session_state.sel_month = sel_month

            # --- C. LOGIC LỌC DỮ LIỆU ---
            df_view = df_db[df_db['NĂM'] == st.session_state.sel_year].copy()
            if st.session_state.sel_month != "Tất cả":
                df_view = df_view[df_view['THÁNG'] == st.session_state.sel_month]

            # --- D. HIỂN THỊ TIÊU ĐỀ ĐỘNG ---
            month_label = f"Tháng {st.session_state.sel_month}" if st.session_state.sel_month != "Tất cả" else "Cả năm"
            st.title(f"📈 Báo cáo vận hành {month_label} / {st.session_state.sel_year}")

            # --- E. KPI NÂNG CẤP ---
            c1, c2, c3 = st.columns(3)
            c1.metric("💰 TỔNG CHI PHÍ", f"{df_view['CHI_PHÍ'].sum():,.0f} đ")
            c2.metric("🛠️ SỐ CA SỬA CHỮA", f"{len(df_view)} ca")
            
            # KPI Chi nhánh nổi bật (Nhiều ca nhất)
            top_branch = df_view['branch'].value_counts().idxmax() if not df_view.empty else "N/A"
            c3.metric("🏢 CHI NHÁNH NHIỀU CA NHẤT", top_branch)

            st.divider()

            # --- F. BIỂU ĐỒ & BẢNG DỮ LIỆU ---
            col_chart, col_table = st.columns([6, 4])
            
            with col_chart:
                st.subheader("📅 Xu hướng sự vụ theo thứ")
                if not df_view.empty:
                    order = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ Nhật']
                    day_stats = df_view['THỨ'].value_counts().reindex(order).fillna(0).reset_index()
                    day_stats.columns = ['THỨ', 'SỐ_CA']
                    
                    fig = px.line(day_stats, x='THỨ', y='SỐ_CA', markers=True, color_discrete_sequence=['#00CC96'])
                    
                    # Tinh chỉnh biểu đồ theo yêu cầu sếp
                    fig.update_layout(
                        height=350,
                        xaxis_title=None,
                        yaxis_title="Số lượng ca",
                        yaxis_gridcolor="rgba(0,0,0,0.05)",
                        margin=dict(l=20, r=20, t=20, b=20)
                    )
                    st.plotly_chart(fig, use_container_width=True)

            with col_table:
                st.subheader("📋 10 ca mới cập nhật")
                # Sort rõ ràng theo thời gian mới nhất
                df_latest = df_view.sort_values('date_dt', ascending=False).head(10)
                st.dataframe(
                    df_latest[['date_dt', 'branch', 'machine_id', 'CHI_PHÍ']],
                    use_container_width=True,
                    hide_index=True
                )

            # --- G. CHI TIẾT DƯỚI CÙNG ---
            with st.expander("🔎 Xem toàn bộ dữ liệu chi tiết đã lọc"):
                st.dataframe(df_view.sort_values('date_dt', ascending=False), use_container_width=True)

    with tab_admin:
        st.title("📥 HỆ THỐNG QUẢN TRỊ DỮ LIỆU")
        
        # 2 Cột chức năng
        col_import, col_manual = st.columns([1, 1])

        # --- PHẦN 1: IMPORT FILE CSV ---
        with col_import:
            st.subheader("📂 Import từ File CSV")
            uploaded_file = st.file_uploader("Chọn file CSV", type=["csv"], key="csv_upload")
            
            if uploaded_file:
                df_up = pd.read_csv(uploaded_file)
                
                # FIX NHANH: Ép kiểu compensation về số trước khi upload để tránh lỗi Boolean
                if 'compensation' in df_up.columns:
                    df_up['compensation'] = pd.to_numeric(df_up['compensation'], errors='coerce').fillna(0).astype(float)
                
                st.write("👀 Xem trước dữ liệu:")
                st.dataframe(df_up.head(3), use_container_width=True)
                
                if st.button("🚀 Xác nhận Upload", use_container_width=True, type="primary"):
                    try:
                        data_to_upsert = df_up.to_dict(orient='records')
                        res = supabase.table("repair_cases").upsert(data_to_upsert).execute()
                        if res.data:
                            st.success(f"✅ Đã nạp {len(res.data)} dòng thành công!")
                            st.cache_data.clear()
                    except Exception as e:
                        st.error(f"❌ Lỗi: {e}. Hãy đảm bảo cột 'compensation' trong Supabase đã đổi sang kiểu numeric!")

        # --- PHẦN 2: NHẬP THỦ CÔNG (ĐÃ FIX LỖI 22P02) ---
        with col_manual:
            st.subheader("✍️ Nhập liệu mới")
            with st.form("manual_entry_form", clear_on_submit=True):
                m_c1, m_c2 = st.columns(2)
                with m_c1:
                    f_date = st.date_input("Ngày xác nhận", value=datetime.now())
                    f_branch = st.selectbox("Chi nhánh", ["Miền Bắc", "Miền Trung", "Miền Nam"])
                with m_c2:
                    f_machine = st.text_input("Mã số máy")
                    f_cost = st.number_input("Chi phí (đ)", min_value=0, step=1000)

                f_customer = st.text_input("Tên khách hàng")
                f_reason = st.text_area("Lý do hư hỏng", height=68)
                
                submit_manual = st.form_submit_button("💾 Lưu vào hệ thống", use_container_width=True)

                if submit_manual:
                    if not f_machine or not f_customer:
                        st.warning("⚠️ Thiếu thông tin bắt buộc!")
                    else:
                        try:
                            # CHỐT HẠ: Gửi dữ liệu dưới dạng Number, không gửi String hay Boolean
                            new_record = {
                                "confirmed_date": f_date.isoformat(),
                                "branch": f_branch,
                                "machine_id": f_machine,
                                "compensation": float(f_cost), # Ép về số thực (Float)
                                "customer_name": f_customer,
                                "issue_reason": f_reason,
                                "created_at": datetime.now().isoformat()
                            }
                            res = supabase.table("repair_cases").insert(new_record).execute()
                            if res.data:
                                st.success("✅ Đã lưu thành công!")
                                st.cache_data.clear()
                        except Exception as e:
                            st.error(f"❌ Lỗi: {e}")

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
