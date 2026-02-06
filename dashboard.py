import streamlit as st
import pandas as pd
# Giả sử bạn cài đặt: pip install supabase
from supabase import create_client 

# --- CONFIG SUPABASE (Thay bằng thông tin của bạn) ---
# Thường các thông tin này nên để trong st.secrets để bảo mật
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://your-project.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "your-anon-key")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- III. ĐỊNH NGHĨA SCHEMA CHUẨN ---
FILE_1_COLUMNS = [
    "MÃ SỐ MÁY", "KHU VỰC", "LOẠI MÁY", "TÌNH TRẠNG",
    "NGÀY NHẬN", "KIỂM TRA THỰC TẾ", "SỬA NỘI BỘ",
    "SỬA BÊN NGOÀI", "NGÀY SỬA XONG", "SỬA ĐỀN BÙ",
    "GIAO LẠI Miền Bắc", "NGÀY TRẢ", "HƯ KHÔNG SỬA ĐƯỢC"
]

FILE_2_COLUMNS = [
    "Mã số máy", "Tên KH", "Lý Do", "Ghi Chú",
    "Chi Nhánh", "Ngày Xác nhận",
    "Người Kiểm Tra", "Chi Phí Dự Kiến", "Chi Phí Thực Tế"
]

# --- IV. HÀM VALIDATION & LOGGING ---
def validate_csv(df, expected_columns):
    errors = []
    missing = set(expected_columns) - set(df.columns)
    if missing:
        errors.append(f"❌ Thiếu cột: {', '.join(missing)}")
    if df.empty:
        errors.append("❌ File không có dữ liệu")
    return errors

def log_audit(action, detail):
    try:
        supabase.table("audit_logs").insert({
            "actor": "admin_user", # Có thể thay bằng st.experimental_user nếu có login
            "action": action,
            "target": "csv_import",
            "diff": detail,
            "created_at": datetime.datetime.now().isoformat()
        }).execute()
    except Exception as e:
        st.warning(f"⚠️ Không thể ghi log: {e}")

# --- V. HÀM INSERT DỮ LIỆU ---
def import_file_1(df):
    progress_bar = st.progress(0)
    for i, r in df.iterrows():
        # 1. UPSERT MACHINE (Nếu có mã máy rồi thì cập nhật, chưa thì thêm mới)
        machine_res = supabase.table("machines").upsert({
            "machine_code": str(r["MÃ SỐ MÁY"]),
            "machine_type": r["LOẠI MÁY"],
            "region": r["KHU VỰC"]
        }).execute()
        
        # 2. CREATE REPAIR CASE
        case_data = {
            "machine_code": str(r["MÃ SỐ MÁY"]),
            "received_date": str(r["NGÀY NHẬN"]),
            "is_unrepairable": "HƯ" in str(r["HƯ KHÔNG SỬA ĐƯỢC"]).upper(),
            "compensation": "ĐỀN BÙ" in str(r["SỬA ĐỀN BÙ"]).upper()
        }
        supabase.table("repair_cases").insert(case_data).execute()
        
        progress_bar.progress((i + 1) / len(df))
    st.success(f"✅ Đã đồng bộ {len(df)} dòng vào Core Data.")

def import_file_2(df):
    progress_bar = st.progress(0)
    for i, r in df.iterrows():
        # Insert vào bảng chi phí (Finance)
        finance_data = {
            "machine_code": str(r["Mã số máy"]),
            "customer_name": r["Tên KH"],
            "issue_description": r["Lý Do"],
            "confirmed_date": str(r["Ngày Xác nhận"]),
            "estimated_cost": float(str(r["Chi Phí Dự Kiến"]).replace(',', '') or 0),
            "actual_cost": float(str(r["Chi Phí Thực Tế"]).replace(',', '') or 0),
            "confirmed_by": r["Người Kiểm Tra"]
        }
        supabase.table("finance_records").insert(finance_data).execute()
        progress_bar.progress((i + 1) / len(df))
    st.success(f"✅ Đã cập nhật dữ liệu tài chính cho {len(df)} máy.")

# --- VI. TÍCH HỢP VÀO TAB MỚI ---
# Cập nhật dòng khai báo tabs trong hàm main():
# tabs = st.tabs(["📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🩺 SỨC KHỎE", "📦 LOGISTICS", "🧠 AI", "📥 DATA INGESTION"])

def render_ingestion_tab(tabs):
    with tabs[5]: # Tab DATA INGESTION
        st.subheader("📥 DATA INGESTION – CSV IMPORT")
        
        col_up1, col_up2 = st.columns([1, 2])
        with col_up1:
            file_type = st.selectbox(
                "Chọn loại file dữ liệu",
                ["FILE 1 – THEO DÕI SỬA CHỮA", "FILE 2 – CHI PHÍ & XÁC NHẬN"]
            )
            st.info("💡 Hệ thống yêu cầu đúng 100% định dạng cột để đảm bảo tính toàn vẹn dữ liệu.")

        with col_up2:
            uploaded_file = st.file_uploader("Upload file CSV", type=["csv"])

        if uploaded_file:
            # Đọc file
            df_upload = pd.read_csv(uploaded_file).fillna("")
            
            # Kiểm tra schema
            expected = FILE_1_COLUMNS if "FILE 1" in file_type else FILE_2_COLUMNS
            errors = validate_csv(df_upload, expected)

            if errors:
                for e in errors: st.error(e)
                st.stop()
            
            st.success("✅ File hợp lệ. Xem trước 5 dòng dữ liệu:")
            st.dataframe(df_upload.head(5), use_container_width=True)

            # Nút thực thi Import
            if st.button("🚀 BẮT ĐẦU IMPORT VÀO DATABASE", type="primary"):
                with st.spinner("Đang ghi dữ liệu vào Supabase..."):
                    if "FILE 1" in file_type:
                        import_file_1(df_upload)
                    else:
                        import_file_2(df_upload)
                    
                    # Audit log
                    log_audit("IMPORT_CSV", {
                        "file": uploaded_file.name,
                        "type": file_type,
                        "rows": len(df_upload)
                    })
                    
                    st.balloons()
                    st.info("📜 Audit log đã được ghi nhận hệ thống.")
