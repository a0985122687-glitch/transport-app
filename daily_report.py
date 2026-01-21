import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time

# 1. 頁面配置與終極美化 (徹底鎖定所有多餘圖示)
st.set_page_config(page_title="運輸管理系統", page_icon="🚚", layout="centered")

st.markdown("""
    <style>
    /* 1. 徹底隱藏頂部標題列與所有連結 */
    .stAppHeader, header, [data-testid="stHeader"] {
        display: none !important;
    }
    
    /* 2. 徹底封鎖右下角所有浮動元件 (含紅色皇冠、藍綠連線圖示) */
    [data-testid="stStatusWidget"], 
    .stDeployButton, 
    #MainMenu, 
    footer, 
    div[class*="st-emotion-cache-"] > button {
        display: none !important;
    }

    /* 3. 移除裝飾用的多餘浮動容器 */
    [data-testid="stDecoration"], .st-emotion-cache-6q9sum, .st-emotion-cache-1avcm0n {
        display: none !important;
    }
    
    /* 4. 讓內容更靠頂部，適合手機操作 */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
    }

    /* 5. 藍色確認送出按鈕美化 */
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
    df = pd.DataFrame(sheet.get_all_records())
    df.columns = df.columns.str.strip()
    return sheet, df

# --- 3. 填報介面區 ---
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
    remark = st.text_input("💬 備註")

    if st.button("🚀 確認送出報表", use_container_width=True):
        if route_name == "請選擇路線":
            st.warning("⚠️ 請選擇路線別！")
        else:
            with st.spinner('同步至雲端中...'):
                try:
                    sheet, _ = get_sheet_and_data()
                    actual_dist = m_end - m_start
                    total_plates = p_sent + p_recv
                    # 按照 A-O 欄位順序寫入試算表 [cite: 2026-01-21]
                    new_row = [selected_driver, str(input_date), start_time, end_time, route_name, m_start, m_end, actual_dist, p_sent, p_recv, total_plates, basket_back, plate_back, detail_content, remark]
                    sheet.append_row(new_row)
                    st.success("🎉 存檔成功！")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                except:
                    st.error("連線繁忙，請稍候。")

# --- 4. 統計區 (確認版獎金公式) ---
st.divider()
if st.button("📊 查看當月獎金與統計 (點擊載入)"):
    with st.spinner('正在核算獎金...'):
        try:
            _, df = get_sheet_and_data()
            if not df.empty:
                df['日期'] = df['日期'].astype(str).str.replace('/', '-', regex=True)
                this_month = datetime.now().strftime("%Y-%m")
                month_data = df[df['日期'].str.contains(this_month)].copy()
                
                if not month_data.empty:
                    # 數值轉換，避免計算錯誤
                    for c in ['實際里程', '合計收送板數', '空籃回收', '空板回收']:
                        month_data[c] = pd.to_numeric(month_data[c], errors='coerce').fillna(0)

                    # 您指定的獎金公式：合計板數*40, 空籃/2, 空板*3
                    month_data['載運獎金'] = month_data['合計收送板數'] * 40
                    month_data['空籃獎金'] = month_data['空籃回收'] / 2
                    month_data['空板獎金'] = month_data['空板回收'] * 3
                    month_data['合計獎金'] = month_data['載運獎金'] + month_data['空籃獎金'] + month_data['空板獎金']

                    st.subheader(f"📅 {this_month} 累計概況")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("當月趟數", f"{len(month_data)} 趟")
                    c2.metric("平均里程", f"{round(month_data['實際里程'].mean(), 1)} km")
                    c3.metric("合計總板數", f"{int(month_data['合計收送板數'].sum())} 板")

                    st.success(f"💰 當月預估獎金合計：{round(month_data['合計獎金'].sum(), 1)} 元")

                    st.write("📋 詳細統計明細：")
                    show_cols = ['日期', '司機', '路線別', '實際里程', '載運獎金', '空籃獎金', '空板獎金', '合計獎金']
                    st.dataframe(month_data[show_cols].tail(10), use_container_width=True, hide_index=True)
                else:
                    st.warning("本月尚無紀錄。")
        except Exception as e:
            st.error(f"核算失敗：{e}")
