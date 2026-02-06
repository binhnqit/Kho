import streamlit as st
import pandas as pd
import datetime

# --- IV. HÀM XỬ LÝ IMPORT CHI TIẾT ---

def import_file_1(df):
    """Xử lý FILE 1: Cập nhật danh mục máy móc"""
    st.info("🔄 Đang xử lý FILE 1 – THEO DÕI SỬA CHỮA...")
    progress_bar = st.progress(0)
    success_count = 0
    
    for i, r in df.iterrows():
        try:
            # Chuẩn bị dữ liệu khớp chính xác với ảnh Schema của bạn
            payload = {
                "machine_code": str(r["MÃ SỐ MÁY"]).strip(),
                "machine_type": str(r["LOẠI MÁY"]).strip(),
                "region": str(r["KHU VỰC"]).strip()
            }
            
            # Sử dụng upsert với on_conflict để không tạo trùng máy
            supabase.table("machines").upsert(
                payload, 
                on_conflict="machine_code"
            ).execute()
            
            success_count += 1
        except Exception as e:
            st.error(f"❌ Lỗi dòng {i+2}: {e}")
        
        progress_bar.progress((i + 1) / len(df))
    
    return success_count

def import_file_2(df):
    """Xử lý FILE 2: Chi phí sửa chữa (Cần liên kết với bảng machines)"""
    st.info("💰 Đang xử lý FILE 2 – CHI PHÍ & XÁC NHẬN...")
    progress_bar = st.progress(0)
    success_count = 0

    for i, r in df.iterrows():
        try:
            # 1. Tìm UUID (id) của máy dựa trên machine_code
            m_code = str(r["Mã số máy"]).strip()
            machine_query = supabase.table("machines").select("id").eq("machine_code", m_code).execute()
            
            if not machine_query.data:
                st.warning(f"⚠️ Dòng {i+2}: Mã máy {m_code} không tồn tại trong hệ thống. Bỏ qua.")
                continue
                
            machine_uuid = machine_query.data[0]["id"]

            # 2. Insert vào bảng chi phí (Giả sử bạn đã tạo bảng repair_costs)
            cost_payload = {
                "machine_id": machine_uuid, # Liên kết UUID
                "customer_name": r["Tên KH"],
                "actual_cost": float(str(r["Chi Phí Thực Tế"]).replace(',', '') or 0),
                "confirmed_at": str(r["Ngày Xác nhận"])
            }
            # Thay 'repair_costs' bằng tên bảng thực tế của bạn
            supabase.table("repair_costs").insert(cost_payload).execute()
            
            success_count += 1
        except Exception as e:
            st.error(f"❌ Lỗi dòng {i+2}: {e}")
            
        progress_bar.progress((i + 1) / len(df))
    
    return success_count

# --- V. GIAO DIỆN TAB INGESTION ---

# Giả sử đây là phần trong tabs[5] của bạn
with tabs[5]:
    st.subheader("📥 CỔNG NHẬP DỮ LIỆU TẬP TRUNG")
    
    file_type = st.selectbox(
        "Chọn loại file",
        ["FILE 1 – THEO DÕI SỬA CHỮA", "FILE 2 – CHI PHÍ & XÁC NHẬN"]
    )
    
    uploaded_file = st.file_uploader("Tải lên file CSV", type=["csv"])
    
    if uploaded_file:
        df_upload = pd.read_csv(uploaded_file).fillna("")
        
        # Validation Schema
        expected_cols = FILE_1_COLS if "FILE 1" in file_type else FILE_2_COLS
        errors = validate_csv(df_upload, expected_cols)
        
        if errors:
            for err in errors: st.error(err)
        else:
            st.success("✅ Cấu trúc file hợp lệ")
            st.dataframe(df_upload.head(3), use_container_width=True)
            
            if st.button("🚀 BẮT ĐẦU ĐỒNG BỘ DỮ LIỆU", type="primary"):
                start_time = datetime.datetime.now()
                
                if "FILE 1" in file_type:
                    total = import_file_1(df_upload)
                else:
                    total = import_file_2(df_upload)
                
                if total > 0:
                    st.balloons()
                    st.success(f"🎉 Đã hoàn tất nhập {total}/{len(df_upload)} dòng thành công!")
                    
                    # Audit Log chuyên nghiệp
                    log_audit("CSV_IMPORT", {
                        "type": file_type,
                        "filename": uploaded_file.name,
                        "rows": total,
                        "duration": str(datetime.datetime.now() - start_time)
                    })
