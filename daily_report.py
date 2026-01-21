import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time

# 1. 頁面美化配置
st.set_page_config(page_title="運輸日報表系統", page_icon="🚚", layout="centered")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        background-color: #007BFF;
        color: white;
        height: 3.5em;
        font-size: 18px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📝 運輸日報表")

# 2. 穩定連線函式 (增加錯誤重試機制)
@st.cache_resource
def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

# 3. 穩定抓取資料 (加入 TTL 快取避免頻繁請求)
@st.cache_data(ttl=300) # 每 5 分鐘才真正去 Google 抓一次
def fetch_full_data(sheet_name):
    client = get_gspread_client()
    sh = client.open(sheet_name)
    sheet = sh.get_worksheet(0)
    return pd.DataFrame(sheet.get_all_records()), sheet

try:
    # 嘗試獲取資料
    df, sheet = fetch_full_data("Transport_System_2026")

    # --- 第一區：填報人資訊 ---
    driver_list = ["請選擇司機", "司機A", "司機B", "車號001"]
    selected_driver = st.selectbox("👤 填報人", driver_list)

    if selected_driver != "請選擇司機":
        st.divider()
        
        # --- 第二區：日期與時間 (優化選項) ---
        input_date = st.date_input("📅 運送日期", datetime.now())
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            # 上班時間選項
            start_options = ["04:00", "04:30", "05:00", "05:30", "06:00", "06:30", "07:00", "07:30", "08:00"]
            start_time = st.selectbox("🕔 上班時間", start_options, index=2)
        with col_t2:
            # 下班時間選項 (12:00~18:00 每半小時)
            end_options = [f"{h}:{m:02d}" for h in range(12, 19) for m in (0, 30)][:-1]
            end_time = st.selectbox("🕔 下班時間", end_options, index=10)

        # --- 第三區：路線與里程 ---
        route_options = ["請選擇路線", "中一線", "中二線", "中三線", "中四線", "中五線", "中六線", "中七線", "其他"]
        route_name = st.selectbox("🛣️ 路線別", route_options)
        
        # 自動帶入上次里程 (從快取讀取)
        driver_df = df[df['司機'] == selected_driver] if not df.empty and '司機' in df.columns else pd.DataFrame()
        last_m = int(driver_df.iloc[-1]['里程迄']) if not driver_df.empty else 0
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            # 移除加減按鈕，改為純數字輸入 (format="%d" 隱藏千分位逗號)
            m_start = st.number_input("📈 里程(起)", value=last_m, step=None, format="%d")
        with col_m2:
            m_end = st.number_input("📉 里程(迄)", value=last_m, step=None, format="%d")
        
        # --- 第四區：載運數據 ---
        st.caption("📦 載運數據輸入")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            p_sent = st.number_input("送板數", value=0, step=1)
            basket_back = st.number_input("空籃回收", value=0, step=1)
        with col_p2:
            p_recv = st.number_input("收板數", value=0, step=1)
            plate_back = st.number_input("空板回收", value=0, step=1)
        
        detail_content = st.text_area("📝 詳細配送內容 (僅存後台)")
        input_remark = st.text_input("💬 備註")

        # --- 送出邏輯 ---
        if st.button("🚀 確認送出報表", use_container_width=True):
            if route_name == "請選擇路線":
                st.warning("⚠️ 請選擇路線別後再送出")
            else:
                with st.spinner('正在安全同步至雲端...'):
                    actual_dist = m_end - m_start
                    total_plates = p_sent + p_recv
                    
                    new_row = [
                        selected_driver, str(input_date), start_time, end_time, route_name,
                        m_start, m_end, actual_dist, p_sent, p_recv, 
                        total_plates, basket_back, plate_back, detail_content, input_remark
                    ]
                    
                    # 送出成功後強制清除快取
                    sheet.append_row(new_row)
                    st.cache_data.clear()
                    st.success("🎉 資料已成功寫入！")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()

    # --- 第五區：最近紀錄 ---
    st.divider()
    st.subheader("📋 最近紀錄")
    if not df.empty:
        # 僅顯示關鍵資訊，維持手機簡潔
        display_cols = ['司機', '日期', '路線別', '實際里程']
        st.dataframe(df[display_cols].tail(5), use_container_width=True, hide_index=True)

except Exception as e:
    st.error("系統暫時連線不穩，請稍候 30 秒後重新整理網頁。")
    # 隱藏具體技術報錯，避免使用者困惑
