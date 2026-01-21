import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# 手機版佈局優化
st.set_page_config(page_title="運輸管理系統", page_icon="🚚", layout="centered")

# 隱藏預設選單
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>""", unsafe_allow_html=True)

st.title("🚚 運輸日報表輸入")

# --- 修正後的連線函式 ---
def get_gspread_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # 從 Secrets 讀取金鑰
    creds_info = st.secrets["gcp_service_account"]
    # 使用官方推薦的 google-auth 方式建立連線
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

try:
    # 建立連線並讀取資料
    client = get_gspread_client()
    sh = client.open("Transport_System_2026")
    sheet = sh.get_worksheet(0)
    
    # 這裡加入簡單的快取，避免每打一個字就去連線一次
    @st.cache_data(ttl=60) # 資料快取 1 分鐘，既能防斷線又能維持數據新鮮
    def fetch_data():
        return pd.DataFrame(sheet.get_all_records())

    df = fetch_data()

    # 2. 司機選擇
    driver_list = ["請選擇司機", "司機A", "司機B", "車號001"]
    selected_driver = st.selectbox("👤 選擇填報人", driver_list)

    if selected_driver != "請選擇司機":
        st.divider()
        
        # --- 基本時間資訊 ---
        input_date = st.date_input("日期", datetime.now())
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            start_time = st.text_input("上班時間", value="05:00")
        with col_t2:
            end_time = st.text_input("下班時間", value="17:00")
        
        # --- 路線選擇 ---
        route_options = ["請選擇路線", "中一線", "中二線", "中三線", "中四線", "中五線", "中六線", "中七線", "其他"]
        route_name = st.selectbox("路線別", route_options)
        
        # --- 里程自動連動 ---
        # 尋找該司機在資料庫中的最後一筆里程
        driver_df = df[df['司機'] == selected_driver] if not df.empty and '司機' in df.columns else pd.DataFrame()
        last_m = int(driver_df.iloc[-1]['里程迄']) if not driver_df.empty else 0
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            m_start = st.number_input("里程(起)", value=last_m)
        with col_m2:
            m_end = st.number_input("里程(迄)", value=last_m)
        
        # --- 板數與空籃回收 ---
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            p_sent = st.number_input("總送板數", value=0, step=1)
            basket_back = st.number_input("空籃回收", value=0, step=1)
        with col_p2:
            p_recv = st.number_input("總收板數", value=0, step=1)
            plate_back = st.number_input("空板回收", value=0, step=1)
        
        detail_content = st.text_area("詳細配送內容 (僅存入 Excel)")
        input_remark = st.text_input("備註 (選填)")

        # 🚀 確認送出按鈕
        if st.button("🚀 確認送出資料", use_container_width=True):
            if route_name == "請選擇路線":
                st.error("請先選擇路線別！")
            else:
                actual_dist = m_end - m_start
                total_plates = p_sent + p_recv
                
                # 寫入 Excel
                new_row = [
                    selected_driver, str(input_date), start_time, end_time, route_name,
                    m_start, m_end, actual_dist, p_sent, p_recv, 
                    total_plates, basket_back, plate_back, detail_content, input_remark
                ]
                sheet.append_row(new_row)
                
                # 成功後強制清除快取，讓下次能抓到最新里程
                st.cache_data.clear()
                st.success("存檔成功！")
                st.balloons()
                st.rerun()

    # 3. 報表預覽
    st.divider()
    st.subheader("📋 最近紀錄預覽")
    if not df.empty:
        display_cols = ['司機', '日期', '上班時間', '下班時間', '路線別', '實際里程']
        if all(c in df.columns for c in display_cols):
            st.dataframe(df[display_cols].tail(5), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"連線異常，請重新整理網頁：{e}")
