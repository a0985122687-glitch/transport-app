import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time

# 1. 頁面配置
st.set_page_config(page_title="運輸管理系統", page_icon="🚚", layout="centered")

st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}
    .stButton>button {width: 100%; border-radius: 12px; background-color: #007BFF; color: white; height: 3.8em; font-size: 18px; font-weight: bold;}</style>""", unsafe_allow_html=True)

st.title("📝 運輸日報表")

# 2. 連線函式
def get_sheet_and_data():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open("Transport_System_2026").get_worksheet(0)
    df = pd.DataFrame(sheet.get_all_records())
    return sheet, df

# --- 填報介面 (保持原本優化後的樣子) ---
driver_list = ["請選擇填報人", "司機A", "司機B", "車號001"]
selected_driver = st.selectbox("👤 填報人", driver_list)

if selected_driver != "請選擇填報人":
    st.divider()
    input_date = st.date_input("📅 運送日期", datetime.now())
    col1, col2 = st.columns(2)
    with col1:
        start_time = st.selectbox("🕔 上班時間", ["04:00", "04:30", "05:00", "05:30", "06:00", "06:30", "07:00", "07:30", "08:00"], index=2)
    with col2:
        end_times = [f"{h}:{m:02d}" for h in range(12, 19) for m in (0, 30)][:-1]
        end_time = st.selectbox("🕔 下班時間", end_times, index=10)

    route_name = st.selectbox("🛣️ 路線別", ["請選擇路線", "中一線", "中二線", "中三線", "中四線", "中五線", "中六線", "中七線", "其他"])
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        m_start = st.number_input("📈 里程(起)", step=1, format="%d")
    with col_m2:
        m_end = st.number_input("📉 里程(迄)", step=1, format="%d")

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        p_sent = st.number_input("送板數", value=0, step=1)
        basket_back = st.number_input("空籃回收", value=0, step=1)
    with col_p2:
        p_recv = st.number_input("收板數", value=0, step=1)
        plate_back = st.number_input("空板回收", value=0, step=1)
    
    detail_content = st.text_area("📝 詳細配送內容")
    input_remark = st.text_input("💬 備註")

    if st.button("🚀 確認送出報表", use_container_width=True):
        if route_name == "請選擇路線":
            st.warning("⚠️ 請選擇路線別！")
        else:
            with st.spinner('同步至雲端中...'):
                try:
                    sheet, _ = get_sheet_and_data()
                    actual_dist = m_end - m_start
                    total_plates = p_sent + p_recv
                    new_row = [selected_driver, str(input_date), start_time, end_time, route_name, m_start, m_end, actual_dist, p_sent, p_recv, total_plates, basket_back, plate_back, detail_content, input_remark]
                    sheet.append_row(new_row)
                    st.success("🎉 存檔成功！")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                except:
                    st.error("連線繁忙，請稍候。")

# --- 終極版統計區 (當月獎金與報表) ---
st.divider()
if st.button("📊 查看當月獎金與統計 (點擊載入)"):
    with st.spinner('正在核算當月獎金...'):
        try:
            _, df = get_sheet_and_data()
            if not df.empty:
                # 1. 統一日期格式
                df['日期'] = df['日期'].astype(str).str.replace('/', '-', regex=True)
                this_month = datetime.now().strftime("%Y-%m")
                
                # 2. 過濾當月資料
                month_data = df[df['日期'].str.contains(this_month)].copy()
                
                if not month_data.empty:
                    # 3. 數值轉換 (確保能計算)
                    num_cols = ['實際里程', '合計收送板數', '空籃回收', '空板回收']
                    for col in num_cols:
                        month_data[col] = pd.to_numeric(month_data[col], errors='coerce').fillna(0)

                    # 4. 獎金計算邏輯 (此處可自行修改倍率)
                    basket_rate = 1  # 空籃一筆 1 元
                    plate_rate = 2   # 空板一筆 2 元
                    
                    month_data['空籃獎金'] = month_data['空籃回收'] * basket_rate
                    month_data['空板獎金'] = month_data['空板回收'] * plate_rate
                    month_data['合計獎金'] = month_data['空籃獎金'] + month_data['空板獎金']

                    # 5. 顯示頂部統計卡片
                    st.subheader(f"📅 {this_month} 累計概況")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("當月趟數", f"{len(month_data)} 趟")
                    c2.metric("當月總里程", f"{int(month_data['實際里程'].sum())} km")
                    c3.metric("累計總板數", f"{int(month_data['合計收送板數'].sum())} 板")

                    # 6. 獎金摘要卡片
                    st.success(f"💰 當月預估獎金合計：{int(month_data['合計獎金'].sum())} 元")
                    b1, b2, b3 = st.columns(3)
                    b1.write(f"空籃獎金: {int(month_data['空籃獎金'].sum())}")
                    b2.write(f"空板獎金: {int(month_data['空板獎金'].sum())}")
                    b3.write(f"平均里程: {round(month_data['實際里程'].mean(), 1)} km")

                    # 7. 顯示詳細報表資料
                    st.write("📋 詳細統計明細：")
                    final_df = month_data[['日期', '司機', '路線別', '實際里程', '合計收送板數', '空籃獎金', '空板獎金', '合計獎金']]
                    st.dataframe(final_df.tail(10), use_container_width=True, hide_index=True)
                else:
                    st.warning(f"本月 ({this_month}) 尚無填報紀錄。")
            else:
                st.info("目前試算表無資料。")
        except Exception as e:
            st.error(f"核算失敗：{e}")
