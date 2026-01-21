import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time

# 頁面基本配置 (保留最穩定的貓咪隱藏指令)
st.set_page_config(page_title="運輸管理系統", page_icon="🚚", layout="centered")

st.markdown("""
    <style>
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stButton>button {
        width: 100%; border-radius: 12px; background-color: #007BFF; 
        color: white; height: 3.8em; font-size: 18px; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📝 運輸日報表")

# 核心連線函式
def get_sheet_and_data():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    # 請確保試算表名稱正確
    sheet = client.open("Transport_System_2026").get_worksheet(0)
    data = sheet.get_all_records()
    df = pd.DataFrame(data) if data else pd.DataFrame(columns=['司機','日期','上班時間','下班時間','路線別','里程起','里程迄','實際里程','送板','收板','合計板數','空籃','空板','備註'])
    df.columns = df.columns.str.strip()
    return sheet, df

# --- 填報介面區 ---

# 需求 2：司機選項改為 A~D
driver_options = ["請選擇填報人", "司機A", "司機B", "司機C", "司機D"]
selected_driver = st.selectbox("👤 填報人", driver_options, key="driver")

# 如果沒選司機，下方不顯示
if selected_driver != "請選擇填報人":
    st.divider()
    input_date = st.date_input("📅 運送日期", datetime.now())
    
    col_time1, col_time2 = st.columns(2)
    with col_time1:
        start_time = st.selectbox("🕔 上班時間", ["04:00", "04:30", "05:00", "05:30", "06:00", "06:30", "07:00", "07:30", "08:00"], index=2)
    with col_time2:
        end_times = [f"{h}:{m:02d}" for h in range(12, 19) for m in (0, 30)][:-1]
        end_time = st.selectbox("🕔 下班時間", end_times, index=10)

    route_name = st.selectbox("🛣️ 路線別", ["請選擇路線", "中一線", "中二線", "中三線", "中四線", "中五線", "中六線", "中七線", "其他"])
    
    # 需求 3：里程不預設 0，且使用無正負號格式
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        m_start = st.number_input("📈 里程(起)", value=None, placeholder="請輸入起始里程", step=1)
    with col_m2:
        m_end = st.number_input("📉 里程(迄)", value=None, placeholder="請輸入結束里程", step=1)

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        p_sent = st.number_input("送板數", value=0, step=1)
        basket_back = st.number_input("空籃回收", value=0, step=1)
    with col_p2:
        p_recv = st.number_input("收板數", value=0, step=1)
        plate_back = st.number_input("空板回收", value=0, step=1)
    
    # 需求 4：刪除詳細配送內容，僅保留備註
    remark = st.text_input("💬 備註")

    if st.button("🚀 確認送出報表", use_container_width=True):
        if route_name == "請選擇路線" or m_start is None or m_end is None:
            st.warning("⚠️ 請務必填寫路線與里程！")
        else:
            with st.spinner('同步至雲端中...'):
                try:
                    sheet, _ = get_sheet_and_data()
                    actual_dist = m_end - m_start
                    total_plates = p_sent + p_recv
                    # 按照 A-O 欄位寫入 (配合您的開發紀錄調整欄位順序)
                    new_row = [selected_driver, str(input_date), start_time, end_time, route_name, m_start, m_end, actual_dist, p_sent, p_recv, total_plates, basket_back, plate_back, "", remark]
                    sheet.append_row(new_row)
                    st.success("🎉 存檔成功！")
                    st.balloons()
                    time.sleep(1.5)
                    # 需求 1：送出後畫面自動歸零 (透過重新整理達成)
                    st.rerun()
                except Exception as e:
                    st.error(f"連線失敗：{e}")

# --- 統計分析區 ---
st.divider()
if st.button("📊 查看統計與獎金 (點擊載入)"):
    with st.spinner('讀取試算表資料中...'):
        try:
            _, df = get_sheet_and_data()
            if not df.empty:
                # 數值校正與當月篩選
                df['日期'] = df['日期'].astype(str)
                this_month = datetime.now().strftime("%Y-%m")
                month_data = df[df['日期'].str.contains(this_month)].copy()
                
                if not month_data.empty:
                    # 確保計算欄位為數字
                    for col in ['實際里程', '合計收送板數', '空籃回收', '空板回收']:
                        month_data[col] = pd.to_numeric(month_data[col], errors='coerce').fillna(0)

                    # 獎金公式
                    month_data['合計獎金'] = (month_data['合計收送板數'] * 40) + (month_data['空籃回收'] / 2) + (month_data['空板回收'] * 3)

                    st.subheader(f"📅 {this_month} 報表摘要")
                    
                    # 需求 5 & 7：保留趟數、呈現合計板數
                    m1, m2 = st.columns(2)
                    m1.metric("當月趟數", f"{len(month_data)} 趟")
                    m2.metric("合計總板數", f"{int(month_data['合計收送板數'].sum())} 板")

                    # 需求 6：按「路線別」區分平均里程
                    st.write("🛣️ 各路線平均里程統計：")
                    avg_dist_by_route = month_data.groupby('路線別')['實際里程'].mean().round(1).reset_index()
                    avg_dist_by_route.columns = ['路線名稱', '平均里程(km)']
                    st.table(avg_dist_by_route)

                    st.success(f"💰 當月預估獎金合計：{round(month_data['合計獎金'].sum(), 1)} 元")
                else:
                    st.warning("本月目前無填報紀錄。")
            else:
                st.info("目前試算表內無任何資料。")
        except Exception as e:
            st.error(f"讀取失敗：{e}")
