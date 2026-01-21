import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# 針對手機螢幕優化：配置頁面標題與佈局
st.set_page_config(page_title="運輸日報表系統", page_icon="🚚", layout="centered")

# 專業介面 CSS 美化 (隱藏選單、加大按鈕)
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #007BFF;
        color: white;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📝 運輸日報表")

# --- 連線函式 ---
def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

try:
    client = get_gspread_client()
    sh = client.open("Transport_System_2026")
    sheet = sh.get_worksheet(0)
    
    @st.cache_data(ttl=60)
    def fetch_data():
        return pd.DataFrame(sheet.get_all_records())

    df = fetch_data()

    # 1. 司機填報人
    driver_list = ["請選擇司機", "司機A", "司機B", "車號001"]
    selected_driver = st.selectbox("👤 填報人", driver_list)

    if selected_driver != "請選擇司機":
        st.divider()
        
        # 2. 日期
        input_date = st.date_input("📅 運送日期", datetime.now())
        
        # 3. 上下班時間 (下拉選單優化)
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            start_times = ["04:00", "04:30", "05:00", "05:30", "06:00", "06:30", "07:00", "07:30", "08:00"]
            start_time = st.selectbox("🕔 上班時間", start_times, index=2) # 預設 05:00
        with col_t2:
            # 產生 12:00 ~ 18:00 每半小時的清單
            end_times = [f"{h}:{m:02d}" for h in range(12, 19) for m in (0, 30)][:-1]
            end_time = st.selectbox("🕔 下班時間", end_times, index=10) # 預設約 17:00

        # 4. 路線選擇
        route_options = ["請選擇路線", "中一線", "中二線", "中三線", "中四線", "中五線", "中六線", "中七線", "其他"]
        route_name = st.selectbox("🛣️ 路線別", route_options)
        
        # 5. 里程數 (移除加減按鈕，改為純數字輸入)
        driver_df = df[df['司機'] == selected_driver] if not df.empty and '司機' in df.columns else pd.DataFrame()
        last_m = int(driver_df.iloc[-1]['里程迄']) if not df.empty and not driver_df.empty else 0
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            m_start = st.number_input("📈 里程(起)", value=last_m, step=None, format="%d")
        with col_m2:
            m_end = st.number_input("📉 里程(迄)", value=last_m, step=None, format="%d")
        
        # 6. 板數與空籃回收
        st.caption("📦 載運數據")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            p_sent = st.number_input("送板數", value=0, step=1)
            basket_back = st.number_input("空籃回收", value=0, step=1)
        with col_p2:
            p_recv = st.number_input("收板數", value=0, step=1)
            plate_back = st.number_input("空板回收", value=0, step=1)
        
        # 7. 詳細配送內容
        detail_content = st.text_area("📝 詳細配送內容", help="此內容將存入 Excel 後台")
        input_remark = st.text_input("💬 備註")

        # 🚀 提交按鈕
        if st.button("🚀 確認送出報表", use_container_width=True):
            if route_name == "請選擇路線":
                st.warning("⚠️ 請選擇路線別後再送出")
            elif m_end < m_start:
                st.error("⚠️ 里程迄點不可小於起點")
            else:
                actual_dist = m_end - m_start
                total_plates = p_sent + p_recv
                
                # A~O 欄位精準寫入
                new_row = [
                    selected_driver, str(input_date), start_time, end_time, route_name,
                    m_start, m_end, actual_dist, p_sent, p_recv, 
                    total_plates, basket_back, plate_back, detail_content, input_remark
                ]
                sheet.append_row(new_row)
                st.cache_data.clear()
                st.success("🎉 報表存檔成功！")
                st.balloons()
                st.rerun()

    # 8. 報表預覽
    st.divider()
    st.subheader("📋 最近紀錄")
    if not df.empty:
        display_cols = ['司機', '日期', '路線別', '實際里程', '合計收送板數']
        st.dataframe(df[display_cols].tail(5), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"系統暫時繁忙，請稍候再試或重新整理。")
