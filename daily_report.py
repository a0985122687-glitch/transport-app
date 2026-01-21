import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time

# 1. 頁面配置與美化
st.set_page_config(page_title="運輸管理系統", page_icon="🚚", layout="centered")

st.markdown("""
    <style>
    /* 隱藏頂部標題與選單 */
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 徹底隱藏數字輸入框的加減按鈕與小數點格式 */
    button[step="1"] { display: none !important; }
    input[type=number] { -moz-appearance: textfield; }
    input::-webkit-outer-spin-button, input::-webkit-inner-spin-button {
        -webkit-appearance: none; margin: 0;
    }
    
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
    
    # 里程輸入：使用 format="%d" 強制不顯示小數點
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        m_start = st.number_input("📈 里程(起)", value=None, placeholder="輸入起點里程", format="%d")
    with col_m2:
        m_end = st.number_input("📉 里程(迄)", value=None, placeholder="輸入終點里程", format="%d")

    # 顯示順序調整：送板 -> 收板 -> 空籃 -> 空板
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        p_sent = st.number_input("送板數", value=None, placeholder="輸入數量", format="%d")
        basket_count = st.number_input("空籃數", value=None, placeholder="輸入數量", format="%d")
    with col_p2:
        p_recv = st.number_input("收板數", value=None, placeholder="輸入數量", format="%d")
        plate_count = st.number_input("空板數", value=None, placeholder="輸入數量", format="%d")
    
    remark = st.text_input("💬 備註")

    if st.button("🚀 確認送出報表", use_container_width=True):
        if route_name == "請選擇路線" or m_start is None or m_end is None:
            st.warning("⚠️ 請填寫路線與里程！")
        else:
            with st.spinner('同步至雲端中...'):
                try:
                    sheet, _ = get_sheet_and_data()
                    actual_dist = int(m_end - m_start)
                    ps = int(p_sent) if p_sent is not None else 0
                    pr = int(p_recv) if p_recv is not None else 0
                    bc = int(basket_count) if basket_count is not None else 0
                    pc = int(plate_count) if plate_count is not None else 0
                    
                    total_plates = ps + pr
                    # 按照 A-O 欄位順序寫入試算表
                    new_row = [selected_driver, str(input_date), start_time, end_time, route_name, m_start, m_end, actual_dist, ps, pr, total_plates, bc, pc, "", remark]
                    sheet.append_row(new_row)
                    st.success("🎉 存檔成功！")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"連線失敗：{e}")

# --- 4. 統計分析區 ---
st.divider()
if st.button("📊 查看統計與獎金 (點擊載入)"):
    with st.spinner('正在讀取資料...'):
        try:
            _, df = get_sheet_and_data()
            if not df.empty:
                df['日期'] = df['日期'].astype(str)
                this_month = datetime.now().strftime("%Y-%m")
                month_data = df[df['日期'].str.contains(this_month)].copy()
                
                if not month_data.empty:
                    # 數值轉換並強制轉為整數
                    for c in ['實際里程', '合計收送板數', '空籃', '空板']:
                        # 處理舊資料中可能有的「空籃回收」標籤
                        col_target = c if c in month_data.columns else (c+'回收' if (c+'回收') in month_data.columns else c)
                        month_data[c] = pd.to_numeric(month_data[col_target], errors='coerce').fillna(0).astype(int)

                    # 獎金計算
                    month_data['載運獎金'] = (month_data['合計收送板數'] * 40).astype(int)
                    month_data['空籃獎金'] = (month_data['空籃'] / 2).astype(int)
                    month_data['空板獎金'] = (month_data['空板'] * 3).astype(int)
                    month_data['合計獎金'] = (month_data['載運獎金'] + month_data['空籃獎金'] + month_data['空板獎金']).astype(int)

                    st.subheader(f"📅 {this_month} 統計摘要")
                    m1, m2 = st.columns(2)
                    m1.metric("當月趟數", f"{len(month_data)} 趟")
                    m2.metric("合計總板數", f"{month_data['合計收送板數'].sum()} 板")

                    # 平均里程表：移除小數點與索引
                    st.write("🛣️ 各路線平均里程 (整數)：")
                    avg_route = month_data.groupby('路線別')['實際里程'].mean().reset_index()
                    avg_route.columns = ['路線名稱', '平均里程']
                    avg_route['平均里程'] = avg_route['平均里程'].astype(int)
                    st.table(avg_route)

                    st.success(f"💰 當月預估獎金合計：{month_data['合計獎金'].sum()} 元")
                    
                    # 獎金明細表：移除小數點與索引
                    st.write("📋 獎金統計明細：")
                    show_cols = ['日期', '路線別', '合計收送板數', '載運獎金', '空籃獎金', '空板獎金', '合計獎金']
                    final_df = month_data[show_cols].tail(10)
                    st.dataframe(final_df, use_container_width=True, hide_index=True)
                else:
                    st.warning("本月尚無紀錄。")
            else:
                st.info("目前雲端無資料。")
        except Exception as e:
            st.error(f"讀取失敗：{e}")
