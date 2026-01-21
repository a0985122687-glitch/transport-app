import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# 1. 頁面美化與配置
st.set_page_config(page_title="運輸日報表", page_icon="🚚", layout="centered")

# 隱藏選單，美化按鈕
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}
    .stButton>button {width: 100%; border-radius: 12px; background-color: #007BFF; color: white; height: 3.8em; font-size: 20px; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.1);}</style>""", unsafe_allow_html=True)

st.title("📝 運輸日報表")

# 2. 超穩定連線機制
def get_sheet():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    return client.open("Transport_System_2026").get_worksheet(0)

# --- 介面開始 ---
driver_list = ["請選擇填報人", "司機A", "司機B", "車號001"]
selected_driver = st.selectbox("👤 填報人", driver_list)

if selected_driver != "請選擇填報人":
    st.divider()
    
    # 日期與上下班時間
    input_date = st.date_input("📅 運送日期", datetime.now())
    col1, col2 = st.columns(2)
    with col1:
        start_time = st.selectbox("🕔 上班時間", ["04:00", "04:30", "05:00", "05:30", "06:00", "06:30", "07:00", "07:30", "08:00"], index=2)
    with col2:
        end_times = [f"{h}:{m:02d}" for h in range(12, 19) for m in (0, 30)][:-1]
        end_time = st.selectbox("🕔 下班時間", end_times, index=10)

    # 路線與里程 (手動輸入，避免連線抓取上次里程)
    route_name = st.selectbox("🛣️ 路線別", ["請選擇路線", "中一線", "中二線", "中三線", "中四線", "中五線", "中六線", "中七線", "其他"])
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        m_start = st.number_input("📈 里程(起)", step=1, format="%d", help="請輸入儀表板起點里程")
    with col_m2:
        m_end = st.number_input("📉 里程(迄)", step=1, format="%d", help="請輸入儀表板終點里程")

    # 載運數據
    st.caption("📦 載運數據")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        p_sent = st.number_input("送板數", value=0, step=1)
        basket_back = st.number_input("空籃回收", value=0, step=1)
    with col_p2:
        p_recv = st.number_input("收板數", value=0, step=1)
        plate_back = st.number_input("空板回收", value=0, step=1)
    
    detail_content = st.text_area("📝 詳細配送內容")
    input_remark = st.text_input("💬 備註")

    # 3. 核心送出邏輯 (只有這裡會觸發連線)
    if st.button("🚀 確認送出報表", use_container_width=True):
        if route_name == "請選擇路線":
            st.warning("⚠️ 請選擇路線別！")
        elif m_end <= 0:
            st.error("⚠️ 請輸入正確的終點里程！")
        else:
            with st.spinner('正在同步至雲端，請勿關閉網頁...'):
                try:
                    sheet = get_sheet()
                    actual_dist = m_end - m_start
                    total_plates = p_sent + p_recv
                    
                    new_row = [
                        selected_driver, str(input_date), start_time, end_time, route_name,
                        m_start, m_end, actual_dist, p_sent, p_recv, 
                        total_plates, basket_back, plate_back, detail_content, input_remark
                    ]
                    
                    sheet.append_row(new_row)
                    st.success("🎉 報表存檔成功！您可以關閉網頁了。")
                    st.balloons()
                    time.sleep(3)
                    st.rerun()
                except Exception as e:
                    st.error(f"連線失敗，請檢查網路或稍候再試。")

st.divider()
st.info("💡 提醒：若遇到連線問題，請稍候 1 分鐘後重新整理頁面即可。")
