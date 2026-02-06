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
    # --- TABS DEFINITION ---
    tabs = st.tabs(["📊 XU HƯỚNG", "💰 CHI PHÍ", "🩺 SỨC KHỎE", "📦 KHO", "🧠 AI", "📥 NHẬP DỮ LIỆU"])

    # --- TAB 0: XU HƯỚNG (ENTERPRISE DASHBOARD) ---
    with tabs[0]:
        if df_db.empty:
            st.info("👋 Chào sếp! Database đang trống. Sếp vui lòng sang tab **NHẬP DỮ LIỆU** để khởi tạo.")
        else:
            # 1. LỌC DỮ LIỆU THEO KỲ (NĂM/THÁNG)
            df_view = df_db[df_db['NĂM'] == sel_year]
            if sel_month != "Tất cả":
                df_view = df_view[df_view['THÁNG'] == sel_month]

            st.subheader(f"🚀 BÁO CÁO VẬN HÀNH - THÁNG {sel_month}/{sel_year}")

            # 2. KPI NÂNG CẤP: CHẤT LƯỢNG & HIỆU SUẤT
            total_cases = len(df_view)
            # Giả định cột 'status' có các giá trị: 'DONE', 'PENDING', 'FAILED', 'REPAIRING'
            done_cases = len(df_view[df_view['status'] == 'DONE'])
            pending_cases = len(df_view[df_view['status'] == 'PENDING'])
            failed_cases = len(df_view[df_view['status'] == 'FAILED'])
            
            done_rate = (done_cases / total_cases * 100) if total_cases > 0 else 0

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("TỔNG CASE", f"{total_cases} máy")
            k2.metric("ĐÃ SỬA XONG", f"{done_cases} máy", f"{done_rate:.1f}%")
            k3.metric("TỒN ĐỌNG", f"{pending_cases} máy", delta="⚠️ Cần xử lý", delta_color="inverse")
            k4.metric("HƯ - THANH LÝ", f"{failed_cases} máy", delta="Rủi ro tài sản")

            st.divider()

            # 3. BIỂU ĐỒ CHIẾN LƯỢC
            c1, c2 = st.columns([1, 1])
            
            with c1:
                # FUNNEL: NHÌN PHÁT BIẾT NGHẼN Ở ĐÂU
                # Dữ liệu mẫu cho luồng vận hành
                funnel_stages = ["Nhận máy", "Đang sửa", "Sửa ngoài", "Hoàn tất"]
                funnel_values = [total_cases, pending_cases + done_cases, pending_cases // 2, done_cases]
                
                fig_funnel = px.funnel(
                    dict(number=funnel_values, stage=funnel_stages),
                    x='number', y='stage',
                    title="PHÂN TÍCH LUỒNG SỬA CHỮA (FUNNEL)",
                    color_discrete_sequence=[ORANGE_COLORS[0]]
                )
                st.plotly_chart(fig_funnel, use_container_width=True)

            with c2:
                # HEATMAP: BIẾT VÙNG NÀO ĐANG TỒN NHIỀU NHẤT
                if not df_view.empty:
                    heat_df = df_view.groupby(['VÙNG', 'status']).size().unstack(fill_value=0)
                    fig_heat = px.imshow(
                        heat_df, text_auto=True,
                        title="HEATMAP: TRẠNG THÁI THEO KHU VỰC",
                        color_continuous_scale='Oranges'
                    )
                    st.plotly_chart(fig_heat, use_container_width=True)
                else:
                    st.info("Chưa đủ dữ liệu để vẽ Heatmap")

            # 4. INSIGHT DÀNH CHO QUẢN TRỊ
            st.markdown("---")
            st.subheader("📉 INSIGHT & CẢNH BÁO RỦI RO")
            i1, i2 = st.columns(2)
            
            with i1:
                st.warning("⚠️ **Vấn đề tồn đọng:**")
                st.write(f"- Tỷ lệ hoàn thành đang đạt {done_rate:.1f}%.")
                st.write(f"- {pending_cases} máy đang kẹt ở khâu kiểm tra và sửa ngoài.")
                
            with i2:
                st.success("💡 **Đề xuất tối ưu:**")
                top_vung = df_view['VÙNG'].mode()[0] if not df_view.empty else "N/A"
                st.write(f"- Tập trung nhân lực cho vùng **{top_vung}** vì lượng máy nhận cao nhất.")
                st.write("- Rà soát lại danh sách 'Hư - Thanh lý' để thu hồi linh kiện.")
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
