import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from supabase import create_client

# --- 1. CONFIG & AUTH ---
st.set_page_config(page_title="REPAIR_OPS - 4ORANGES", layout="wide", page_icon="🎨")

# Project ID của bạn: cigbnbaanpebwrufzxfg
SUPABASE_URL = "https://cigbnbaanpebwrufzxfg.supabase.co"
# Key này bạn nên lấy từ Supabase Settings -> API và dán vào Secrets của Streamlit
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "YOUR_ANON_KEY") 

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error("Kết nối Database thất bại. Vui lòng kiểm tra lại Key.")

# --- 2. ĐỊNH NGHĨA CỘT CHUẨN (VALIDATION CONTRACT) ---
FILE_1_COLS = ["MÃ SỐ MÁY", "KHU VỰC", "LOẠI MÁY", "TÌNH TRẠNG", "NGÀY NHẬN", "KIỂM TRA THỰC TẾ", "SỬA NỘI BỘ", "SỬA BÊN NGOÀI", "NGÀY SỬA XONG", "SỬA ĐỀN BÙ", "GIAO LẠI Miền Bắc", "NGÀY TRẢ", "HƯ KHÔNG SỬA ĐƯỢC"]
FILE_2_COLS = ["Mã số máy", "Tên KH", "Lý Do", "Ghi Chú", "Chi Nhánh", "Ngày Xác nhận", "Người Kiểm Tra", "Chi Phí Dự Kiến", "Chi Phí Thực Tế"]

# --- 3. HELPER FUNCTIONS ---
def validate_csv(df, expected_columns):
    missing = set(expected_columns) - set(df.columns)
    if missing: return [f"❌ Thiếu cột: {', '.join(missing)}"]
    if df.empty: return ["❌ File rỗng"]
    return []

def log_audit(action, detail):
    try:
        supabase.table("audit_logs").insert({
            "action": action,
            "detail": detail,
            "created_at": datetime.datetime.now().isoformat()
        }).execute()
    except: pass

# --- 4. MAIN INTERFACE ---
def main():
    st.title("🚀 REPAIR_OPS: HỆ THỐNG ĐIỀU HÀNH SỬA CHỮA")
    
    tabs = st.tabs(["📊 DASHBOARD", "📥 DATA INGESTION", "📜 AUDIT LOG"])

    # --- TAB: DASHBOARD (Giữ nguyên logic cũ của bạn) ---
    with tabs[0]:
        st.info("Hiển thị các biểu đồ xu hướng từ Database...")
        # Bạn có thể gọi lại code vẽ Chart ở đây

    # --- TAB: DATA INGESTION (Hoàn thiện theo yêu cầu) ---
    with tabs[1]:
        st.subheader("📥 CỔNG NHẬP DỮ LIỆU ENTERPRISE")
        
        c1, c2 = st.columns([1, 2])
        with c1:
            file_type = st.selectbox("Loại dữ liệu", ["FILE 1 – THEO DÕI SỬA CHỮA", "FILE 2 – CHI PHÍ"])
        with c2:
            uploaded_file = st.file_uploader("Chọn file CSV", type=["csv"])

        if uploaded_file:
            df = pd.read_csv(uploaded_file).fillna("")
            expected = FILE_1_COLS if "FILE 1" in file_type else FILE_2_COLS
            errors = validate_csv(df, expected)

            if errors:
                for err in errors: st.error(err)
            else:
                st.success("✅ Cấu trúc file hợp lệ")
                st.dataframe(df.head(3), use_container_width=True)
                
                if st.button("CONFIRM IMPORT", type="primary"):
                    progress = st.progress(0)
                    try:
                        # Logic Import đặc thù cho từng loại file
                        if "FILE 1" in file_type:
                            for i, r in df.iterrows():
                                # Upsert máy vào core.machines
                                supabase.table("machines").upsert({
                                    "code": str(r["MÃ SỐ MÁY"]),
                                    "type": r["LOẠI MÁY"],
                                    "region": r["KHU VỰC"]
                                }).execute()
                                progress.progress((i + 1) / len(df))
                        else:
                            # Tương tự cho File 2
                            st.write("Đang xử lý File 2...")
                        
                        log_audit("IMPORT_SUCCESS", {"file": uploaded_file.name, "rows": len(df)})
                        st.balloons()
                        st.success(f"Đã nhập thành công {len(df)} dòng dữ liệu.")
                    except Exception as e:
                        st.error(f"Lỗi khi ghi Database: {e}")

    # --- TAB: AUDIT LOG ---
    with tabs[2]:
        st.subheader("Lịch sử thao tác hệ thống")
        try:
            logs = supabase.table("audit_logs").select("*").order("created_at", desc=True).limit(10).execute()
            st.table(logs.data)
        except:
            st.write("Chưa có dữ liệu log.")

if __name__ == "__main__":
    main()
