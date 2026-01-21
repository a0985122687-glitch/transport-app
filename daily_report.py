import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time

# 1. 頁面基本配置 (保留隱藏頂部與選單功能)
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

# 2. 核心連線函式
def get_sheet_and_data():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open("Transport_System_2026").get_worksheet(0)
    data = sheet.get_all_records()
    df = pd.DataFrame(data) if data else pd.DataFrame()
    if not df.empty:
        df.columns = df.columns.str.strip()
    return sheet, df

# --- 3. 填報介面區 ---
driver_options = ["請選擇填報人", "司機A", "司機B", "司機C", "司機D"]
selected_driver = st.selectbox("👤 填報人", driver_options)

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
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        # 需求 3：里程預設為空白，不帶正負號
        m_start = st.number_input("📈 里程(起)", value=None, placeholder="輸入起點里程")
    with col_m2:
        m_end = st.number_input("📉 里程(迄)", value=None, placeholder="輸入終點里程")

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        p_sent = st.number_input("送板數", value=0, step=1)
        basket_back = st.number_input("空籃回收", value=0, step=1)
    with col_p2:
        p_recv = st.number_input("收板數", value=0, step=1)
        plate_back = st.number_input("空板回收", value=0, step=1)
    
    remark = st.text_input("💬 備註")

    if st.button("🚀 確認送出報表", use_container_width=True):
        if route_name == "請選擇路線" or m_start is None or m_end is None:
            st.warning("⚠️ 請完整填寫路線與里程！")
        else:
            with st.spinner('同步至雲端中...'):
                try:
                    sheet, _ = get_sheet_and_data()
                    actual_dist = m_end - m_start
                    total_plates = p_sent + p_recv
                    # 按照 A-O 欄位寫入
                    new_row = [selected_driver, str(input_date), start_time, end_time, route_name, m_start, m_end, actual_dist, p_sent, p_recv, total_plates, basket_back, plate_back, "", remark]
                    sheet.append_row(new_row)
                    st.success("🎉 存檔成功！")
                    st.balloons()
                    time.sleep(1)
                    # 需求 1：送出後自動重新整理歸零
                    st.rerun()
                except Exception as e:
                    st.error(f"連線失敗：{e}")

# --- 4. 統計分析區 ---
st.divider()
if st.button("📊 查看統計與獎金 (點擊載入)"):
    with st.spinner('正在從試算表讀取資料...'):
        try:
            _, df = get_sheet_and_data()
            if not df.empty:
                df['日期'] = df['日期'].astype(str)
                this_month = datetime.now().strftime("%Y-%m")
                month_data = df[df['日期'].str.contains(this_month)].copy()
                
                if not month_data.empty:
                    # 數值校正
                    for c in ['實際里程', '合計收送板數', '空籃回收', '空板回收']:
                        month_data[c] = pd.to_numeric(month_data[c], errors='coerce').fillna(0)

                    # 獎金計算公式
                    month_data['載運獎金'] = month_data['合計收送板數'] * 40
                    month_data['空籃獎金'] = month_data['空籃回收'] / 2
                    month_data['空板獎金'] = month_data['空板回收'] * 3
                    month_data['合計獎金'] = month_data['載運獎金'] + month_data['空籃獎金'] + month_data['空板獎金']

                    st.subheader(f"📅 {this_month} 統計摘要")
                    
                    # 需求 5 & 7：當月趟數與合計板數
                    m1, m2 = st.columns(2)
                    m1.metric("當月趟數", f"{len(month_data)} 趟")
                    m2.metric("合計總板數", f"{int(month_data['合計收送板數'].sum())} 板")

                    # 需求 6：按路線區分平均里程 (並移除小數點)
                    st.write("🛣️ 各路線平均里程 (整數)：")
                    avg_route = month_data.groupby('路線別')['實際里程'].mean().reset_index()
                    avg_route.columns = ['路線', '平均里程']
                    # 將平均里程轉換為整數型態，移除小數點
                    avg_route['平均里程'] = avg_route['平均里程'].astype(int)
                    st.table(avg_route)

                    # 顯示獎金總計與明細
                    st.success(f"💰 當月預估獎金合計：{int(month_data['合計獎金'].sum())} 元")
                    st.write("📋 獎金統計明細：")
                    show_cols = ['日期', '路線別', '合計收送板數', '載運獎金', '空籃獎金', '空板獎金', '合計獎金']
                    st.dataframe(month_data[show_cols].tail(10), use_container_width=True, hide_index=True)
                else:
                    st.warning("本月尚無紀錄。")
            else:
                st.info("目前雲端無資料。")
        except Exception as e:
            st.error(f"讀取資料失敗：{e}")
