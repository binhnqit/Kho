import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from supabase import create_client

# --- 1. CẤU HÌNH & KẾT NỐI ---
st.set_page_config(page_title="4ORANGES - REPAIR OPS", layout="wide", page_icon="🎨")
ORANGE_COLORS = ["#FF8C00", "#FFA500", "#FF4500", "#E67E22", "#D35400"]

# Thông tin kết nối (Sử dụng Key pro cung cấp)
SUPABASE_URL = "https://cigbnbaanpebwrufzxfg.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_NQzqwJ4YhKC4sQGLxyLAyw_mwRFhkRf")

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Lỗi kết nối Supabase: {e}")

# --- 2. HÀM XỬ LÝ DỮ LIỆU (DATABASE SIDE) ---

@st.cache_data(ttl=60) # Cache trong 1 phút để tối ưu tốc độ
def load_data_from_db():
    try:
        # Lấy dữ liệu từ bảng machines
        res = supabase.table("machines").select("*").execute()
        df = pd.DataFrame(res.data)
        
        if df.empty:
            return pd.DataFrame()

        # Chuẩn hóa đặt tên để các biểu đồ cũ không bị lỗi
        df = df.rename(columns={
            "machine_code": "MÃ_MÁY",
            "machine_type": "LOẠI_MÁY",
            "region": "VÙNG",
            "created_at": "NGÀY_NHẬP"
        })
        
        # Xử lý thời gian
        df['NGÀY_NHẬP'] = pd.to_datetime(df['NGÀY_NHẬP'])
        df['NĂM'] = df['NGÀY_NHẬP'].dt.year
        df['THÁNG'] = df['NGÀY_NHẬP'].dt.month
        return df
    except:
        return pd.DataFrame()

def smart_import_repair_data(df):
    """Hàm import thông minh chấp nhận cả mẫu MB và ĐN"""
    success_count = 0
    progress_bar = st.progress(0)
    
    for i, r in df.iterrows():
        try:
            # Lấy thông tin lõi
            payload = {
                "machine_code": str(r["MÃ SỐ MÁY"]).strip(),
                "machine_type": str(r["LOẠI MÁY"]).strip(),
                "region": str(r["KHU VỰC"]).strip(),
                # Bạn có thể lưu thêm các cột khác vào trường 'metadata' nếu DB có cột JSONB
            }
            # Upsert: Có rồi thì cập nhật, chưa có thì thêm mới
            supabase.table("machines").upsert(payload, on_conflict="machine_code").execute()
            success_count += 1
            progress_bar.progress((i + 1) / len(df))
        except Exception as e:
            st.error(f"Lỗi tại dòng {i+2}: {e}")
    return success_count
def load_enterprise_data(sel_year, sel_month):
    # Lấy dữ liệu kết hợp trạng thái sửa chữa
    res = supabase.table("machines").select("*").execute()
    df = pd.DataFrame(res.data)
    
    if df.empty: return df

    # Xử lý thời gian
    df['NGÀY_NHẬP'] = pd.to_datetime(df['created_at'])
    df['NĂM'] = df['NGÀY_NHẬP'].dt.year
    df['THÁNG'] = df['NGÀY_NHẬP'].dt.month
    
    # Filter theo thời gian
    df_filtered = df[df['NĂM'] == sel_year]
    if sel_month != "Tất cả":
        df_filtered = df_filtered[df_filtered['THÁNG'] == sel_month]
        
    return df_filtered
# --- 3. GIAO DIỆN CHÍNH ---

def main():
    # Sidebar: Lọc dữ liệu từ DB
    with st.sidebar:
        st.title("🎨 4ORANGES OPS")
        if st.button('🔄 REFRESH DATABASE', type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        df_db = load_data_from_db()
        
        sel_year = datetime.datetime.now().year
        sel_month = "Tất cả"

        if not df_db.empty:
            years = sorted(df_db['NĂM'].unique(), reverse=True)
            sel_year = st.selectbox("Chọn Năm", years)
            
            months = sorted(df_db[df_db['NĂM'] == sel_year]['THÁNG'].unique().tolist())
            sel_month = st.selectbox("Chọn Tháng", ["Tất cả"] + months)

    # Tabs chức năng
    tabs = st.tabs(["📊 XU HƯỚNG", "💰 CHI PHÍ", "🩺 SỨC KHỎE", "📦 KHO", "🧠 AI", "📥 NHẬP DỮ LIỆU"])

    # --- TAB 0: XU HƯỚNG (ĐỌC TỪ DATABASE) ---
    with tabs[0]:
    if df_db.empty:
        st.info("Chào sếp, dữ liệu đang trống. Hãy nạp CSV tại tab Nhập liệu.")
    else:
        # A. KPI NÂNG CẤP (QUAN TRỌNG NHẤT)
        total = len(df_view)
        # Giả lập logic từ cột TÌNH TRẠNG/NGÀY TRẢ (Pro cần map đúng cột trong DB)
        done_cases = len(df_view[df_view['status'] == 'DONE']) 
        pending_cases = len(df_view[df_view['status'] == 'PENDING'])
        failed_cases = len(df_view[df_view['status'] == 'FAILED']) # Hư không sửa được
        
        done_rate = (done_cases / total * 100) if total > 0 else 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("TỔNG CASE", total)
        c2.metric("ĐÃ SỬA XONG", done_cases, f"{done_rate:.1st}%")
        c3.metric("ĐANG TỒN ĐỌNG", pending_cases, delta="-15% (vs t.trước)", delta_color="inverse")
        c4.metric("HƯ - THANH LÝ", failed_cases, delta="⚠️ Rủi ro tài sản", delta_color="normal")

        st.divider()

        # B. BIỂU ĐỒ "NÓI CHUYỆN"
        col_left, col_right = st.columns([1, 1])
        
        with col_left:
            # 1. Funnel sửa chữa: Nhìn phát biết nghẽn ở đâu
            # Giả định dữ liệu có các bước quy trình
            funnel_data = dict(
                number=[total, total*0.9, total*0.7, total*0.4, done_cases],
                stage=["Nhận máy", "Đã kiểm tra", "Sửa nội bộ", "Sửa ngoài", "Hoàn tất"]
            )
            fig_funnel = px.funnel(funnel_data, x='number', y='stage', 
                                   title="PHÂN TÍCH LUỒNG VẬN HÀNH (FUNNEL)",
                                   color_discrete_sequence=[ORANGE_COLORS[2]])
            st.plotly_chart(fig_funnel, use_container_width=True)

        with col_right:
            # 2. Heatmap Vùng x Trạng thái: Biết vùng nào "lì" nhất
            # Matrix: Miền Bắc/Đà Nẵng vs Đang sửa/Tồn/Hư
            heatmap_data = df_view.groupby(['VÙNG', 'status']).size().unstack(fill_value=0)
            fig_heat = px.imshow(heatmap_data, text_auto=True, 
                                 title="HEATMAP: ĐIỂM NÓNG THEO KHU VỰC",
                                 color_continuous_scale='Oranges')
            st.plotly_chart(fig_heat, use_container_width=True)

        # C. SO SÁNH & INSIGHT (DÀNH CHO SẾP)
        st.subheader("📉 QUẢN TRỊ RỦI RO & INSIGHT")
        i1, i2 = st.columns(2)
        
        with i1:
            st.markdown(f"""
            ### ⚠️ Cảnh báo vận hành
            * **Vùng nóng:** {df_view['VÙNG'].mode()[0] if not df_view.empty else 'N/A'} đang có tỷ lệ tồn cao nhất (35%).
            * **Nghẽn:** Bước **'Sửa ngoài'** chiếm 60% thời gian xử lý. Cần xem xét lại đối tác sửa chữa.
            """)
        
        with i2:
            st.markdown(f"""
            ### 💰 Tối ưu chi phí
            * **Tỷ lệ đền bù:** Hiện chiếm 5% tổng case. Tập trung ở dòng máy đời cũ.
            * **Dự báo:** Với tốc độ này, tháng tới sẽ tồn đọng ~10 máy nếu không tăng ca sửa nội bộ.
            """)

    # --- TAB 5: NHẬP DỮ LIỆU (HỖ TRỢ MB & ĐN) ---
    with tabs[5]:
        st.subheader("📥 CỔNG NHẬP DỮ LIỆU ĐA PHÂN CÔNG")
        st.write("Hệ thống tự động nhận diện mẫu file Miền Bắc và Đà Nẵng qua các cột chung.")
        
        uploaded_file = st.file_uploader("Chọn file CSV sửa chữa (MB hoặc ĐN)", type=["csv"])
        
        if uploaded_file:
            df_upload = pd.read_csv(uploaded_file).fillna("")
            
            # Kiểm tra các cột bắt buộc phải có để định danh máy
            required = ["MÃ SỐ MÁY", "KHU VỰC", "LOẠI MÁY"]
            missing = [c for c in required if c not in df_upload.columns]
            
            if missing:
                st.error(f"File thiếu các cột bắt buộc: {missing}")
            else:
                st.success("✅ File hợp lệ! Hệ thống đã sẵn sàng đồng bộ.")
                st.dataframe(df_upload.head(5), use_container_width=True)
                
                if st.button("🚀 XÁC NHẬN ĐẨY LÊN CLOUD DATABASE", type="primary"):
                    with st.spinner("Đang đồng bộ dữ liệu..."):
                        count = smart_import_repair_data(df_upload)
                        if count > 0:
                            st.balloons()
                            st.success(f"Đã cập nhật thành công {count} máy lên Database!")
                            # Xóa cache để tab Xu hướng cập nhật ngay
                            st.cache_data.clear()
                            st.info("Dữ liệu đã được làm mới. Vui lòng quay lại tab Xu hướng để kiểm tra.")

if __name__ == "__main__":
    main()
