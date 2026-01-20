import streamlit as st
import pandas as pd
import plotly.express as px

# --- GIỮ NGUYÊN PHẦN CẤU HÌNH VÀ LOAD DATA CỦA SẾP ---
st.set_page_config(page_title="STRATEGIC HUB V17.6", layout="wide", page_icon="🚀")

URL_LAPTOP_LOI = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=675485241&single=true&output=csv"
URL_MIEN_BAC = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=602348620&single=true&output=csv"
URL_DA_NANG = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-UP5WFVE63byPckNy_lsT9Rys84A8pPq6cm6rFFBbOnPAsSl1QDLS_A9E45oytg/pub?gid=1519063387&single=true&output=csv"

@st.cache_data(ttl=60)
def load_data(url):
    try: return pd.read_csv(url, on_bad_lines='skip', low_memory=False).fillna("0")
    except: return pd.DataFrame()

def main():
    # --- PHẦN SIDEBAR VÀ XỬ LÝ DỮ LIỆU TÀI CHÍNH (GIỮ NGUYÊN) ---
    df_loi_raw = load_data(URL_LAPTOP_LOI)
    df_bac_raw = load_data(URL_MIEN_BAC)
    df_nam_raw = load_data(URL_DA_NANG)
    
    # ... (Giữ nguyên logic xử lý df_f và df_display từ bản V17.5 của sếp) ...
    # Giả định df_f đã được xử lý xong để không làm gián đoạn hệ thống hiện tại
    
    st.title("🚀 STRATEGIC HUB V17.6")
    tabs = st.tabs(["📊 XU HƯỚNG", "💰 TÀI CHÍNH", "🩺 SỨC KHỎE MÁY", "📦 KHO LOGISTICS", "🧠 AI & DỰ BÁO"])

    # --- CHỈ TẬP TRUNG NÂNG CẤP TAB KHO LOGISTICS ---
    with tabs[3]:
        st.subheader("📦 TRUNG TÂM ĐIỀU PHỐI KHO VẬN TOÀN QUỐC")
        
        wh_list = []
        for region, raw in [("BẮC", df_bac_raw), ("NAM", df_nam_raw)]:
            if not raw.empty:
                for _, r in raw.iloc[1:].iterrows():
                    m_id = str(r.iloc[1]).strip()
                    if m_id and "MÃ" not in m_id.upper():
                        # Thu thập dữ liệu trạng thái từ cột G và J
                        stt_info = (str(r.iloc[6]) + str(r.iloc[9])).upper()
                        if "OK" in stt_info: stt = "🔵 ĐÃ NHẬN"
                        elif "HỎNG" in stt_info or "LÝ" in stt_info: stt = "🔴 THANH LÝ"
                        else: stt = "🟡 ĐANG XỬ LÝ"
                        wh_list.append({"VÙNG": region, "MÃ_MÁY": m_id, "TRẠNG_THÁI": stt})
        
        if wh_list:
            df_wh = pd.DataFrame(wh_list)
            
            # 1. Dashboard chỉ số kho nhanh
            k1, k2, k3 = st.columns(3)
            total_inv = len(df_wh)
            done = len(df_wh[df_wh['TRẠNG_THÁI'] == "🔵 ĐÃ NHẬN"])
            pending = len(df_wh[df_wh['TRẠNG_THÁI'] == "🟡 ĐANG XỬ LÝ"])
            
            k1.metric("TỔNG THIẾT BỊ TRONG KHO", f"{total_inv:,} máy")
            k2.metric("TỶ LỆ HOÀN TẤT", f"{(done/total_inv*100):.1f}%", f"{done} máy")
            k3.metric("ĐANG TỒN ĐỌNG", f"{pending} máy", delta_color="inverse")
            
            st.write("---")
            
            # 2. Trực quan hóa bằng biểu đồ
            col_chart, col_table = st.columns([3, 2])
            
            with col_chart:
                # Biểu đồ cột chồng thể hiện tỷ lệ trạng thái giữa 2 miền
                fig_wh = px.histogram(df_wh, x="VÙNG", color="TRẠNG_THÁI",
                                     title="SỐ LƯỢNG MÁY THEO TRẠNG THÁI & VÙNG",
                                     barmode="stack",
                                     color_discrete_map={"🔵 ĐÃ NHẬN": "#3182bd", "🟡 ĐANG XỬ LÝ": "#feb24c", "🔴 THANH LÝ": "#f03b20"})
                st.plotly_chart(fig_wh, use_container_width=True)
            
            with col_table:
                # Bảng tổng hợp số liệu chi tiết
                st.write("**BẢNG ĐỐI SOÁT CHI TIẾT**")
                summary = df_wh.groupby(['VÙNG', 'TRẠNG_THÁI']).size().unstack(fill_value=0)
                st.dataframe(summary.style.highlight_max(axis=0, color='#e6f4ff'), use_container_width=True)
            
            # 3. Chức năng tra cứu nhanh máy trong kho
            st.write("---")
            search_id = st.text_input("🔍 Tra cứu vị trí máy (Nhập mã máy):").upper()
            if search_id:
                res = df_wh[df_wh['MÃ_MÁY'].str.contains(search_id)]
                if not res.empty:
                    st.success(f"Kết quả: Máy {search_id} đang ở kho Miền {res.iloc[0]['VÙNG']} - Trạng thái: {res.iloc[0]['TRẠNG_THÁI']}")
                else:
                    st.error("Không tìm thấy máy này trong hệ thống kho.")
        else:
            st.info("Hệ thống đang đồng bộ dữ liệu kho, sếp vui lòng đợi...")

    # --- GIỮ NGUYÊN CÁC TAB CÒN LẠI (XU HƯỚNG, TÀI CHÍNH, AI...) ---
    # ... (Code cũ của sếp tiếp tục ở đây) ...

if __name__ == "__main__":
    main()
