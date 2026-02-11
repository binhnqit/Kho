import pandas as pd
import streamlit as st
from core.database import supabase

# --- CẤU HÌNH HẰNG SỐ ---
STATUS_OPTIONS = [
    "1. Chờ nhận", 
    "2. Đã nhận kho tổng", 
    "3. Đang sửa nội bộ", 
    "4. Gửi nhà cung cấp", 
    "5. Đã sửa xong", 
    "6. Đã trả chi nhánh"
]

def get_repair_data():
    """
    Lấy dữ liệu từ bảng repair_cases, mapping với bảng machines.
    Đảm bảo cột 'id' của ca sửa chữa luôn tồn tại để đối soát.
    """
    try:
        # 1. Lấy dữ liệu sửa chữa
        res_repair = supabase.table("repair_cases").select("*").order("created_at", desc=True).execute()
        df_repair = pd.DataFrame(res_repair.data)

        # 2. Lấy danh mục máy để mapping
        res_machines = supabase.table("machines").select("id, machine_code").execute()
        df_machines = pd.DataFrame(res_machines.data)

        # XỬ LÝ KHI DỮ LIỆU TRỐNG: Trả về DF có sẵn cấu trúc cột để tránh lỗi KeyError: 'id'
        if df_repair.empty:
            return pd.DataFrame(columns=[
                'id', 'machine_id', 'machine_display', 'NĂM', 'THÁNG', 
                'CHI_PHÍ', 'branch', 'status', 'origin_branch', 
                'receiver_name', 'returner_name', 'confirmed_dt'
            ])

        # 3. MAPPING & BẢO VỆ CỘT ID
        # Chúng ta dùng suffixes để tránh việc cột id của repair_cases bị đổi tên thành id_x
        df = df_repair.merge(
            df_machines, 
            left_on='machine_id', 
            right_on='id', 
            how='left', 
            suffixes=('', '_machine') 
        )

        # 4. TẠO CỘT HIỂN THỊ
        df['machine_display'] = df['machine_code'].fillna('N/A')

        # 5. XỬ LÝ THỜI GIAN
        df['confirmed_dt'] = pd.to_datetime(df['confirmed_date'], errors='coerce')
        df['confirmed_dt'] = df['confirmed_dt'].fillna(pd.to_datetime(df['created_at'], errors='coerce'))
        
        # Chỉ giữ lại các dòng có thời gian hợp lệ
        df = df.dropna(subset=['confirmed_dt'])

        # Trích xuất Năm/Tháng
        df['NĂM'] = df['confirmed_dt'].dt.year.astype(int)
        df['THÁNG'] = df['confirmed_dt'].dt.month.astype(int)
        
        # 6. CHI PHÍ
        # compensation có thể là None hoặc chuỗi, chuyển về numeric an toàn
        df['CHI_PHÍ'] = pd.to_numeric(df.get('compensation', 0), errors='coerce').fillna(0)

        return df
    except Exception as e:
        st.error(f"❌ Lỗi truy xuất dữ liệu: {e}")
        return pd.DataFrame()

def insert_new_repair(data_dict):
    """ Thêm mới ca sửa chữa """
    try:
        # Làm sạch dữ liệu trước khi gửi lên Supabase
        clean_data = data_dict.copy()
        keys_to_remove = ['machine_display', 'confirmed_dt', 'NĂM', 'THÁNG', 'CHI_PHÍ']
        for key in keys_to_remove:
            clean_data.pop(key, None)
        
        if 'status' not in clean_data:
            clean_data['status'] = "1. Chờ nhận"
            
        response = supabase.table("repair_cases").insert(clean_data).execute()
        st.cache_data.clear()
        return response
    except Exception as e:
        st.error(f"❌ Lỗi lưu dữ liệu: {str(e)}")
        return None

def update_repair_tracking(case_id, new_status, staff_name, note=""):
    """ Cập nhật trạng thái và nhân viên đối soát """
    if not case_id:
        st.error("❌ Không tìm thấy ID của ca sửa chữa để cập nhật!")
        return None

    update_data = {
        "status": new_status,
        "note": note,
        "updated_at": "now()"
    }
    
    # Logic xác nhận theo từ khóa trạng thái
    if "Đã nhận" in new_status or "2." in new_status:
        update_data["receiver_name"] = staff_name
        update_data["received_at_warehouse"] = "now()" # Khớp với cột trong SQL mới của bạn
        
    elif "Đã trả" in new_status or "6." in new_status:
        update_data["returner_name"] = staff_name
        update_data["returned_at_branch"] = "now()" # Khớp với cột trong SQL mới của bạn

    try:
        response = supabase.table("repair_cases").update(update_data).eq("id", case_id).execute()
        st.cache_data.clear()
        return response
    except Exception as e:
        st.error(f"❌ Lỗi cập nhật đối soát: {str(e)}")
        return None
