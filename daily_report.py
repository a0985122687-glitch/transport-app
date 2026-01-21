import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time

# 1. 頁面配置
st.set_page_config(page_title="運輸管理系統", page_icon="🚚", layout="wide") # 改為寬版以容納報表

st.markdown("""
    <style>
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    button[step="1"] { display: none !important; }
    input[type=number] { -moz-appearance: textfield; }
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

# --- 3. 填報介面區 (包含客戶維度) ---
driver_options = ["請選擇填報人", "司機A", "司機B", "司機C", "司機D"]
selected_driver = st.selectbox("👤 填報人", driver_options)

if selected_driver != "請選擇填報人":
    st.divider()
    input_date = st.date_input("📅 運送日期", datetime.now())
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        start_time = st.selectbox("🕔 上班時間", ["04:00", "04:30", "05:00", "05:30", "06:00", "06:30", "07:00", "07:30", "08:00"], index=2)
    with col_t2:
        end_time = st.selectbox("🕔 下班時間", [f"{h}:{m:02d}" for h in range(12, 22) for m in (0, 30)], index=10)

    route_name = st.selectbox("🛣️ 路線別", ["請選擇路線", "中一線", "中二線", "中三線", "中四線", "中五線", "中六線", "中七線", "其他"])
    
    col_cust1, col_cust2 = st.columns([1, 2])
    with col_cust1:
        customer_count = st.number_input("配送家數", value=None, placeholder="家數", step=1)
    with col_cust2:
        customer_detail = st.text_input("客戶別/板數", placeholder="例: A店/3, B店/2")

    st.divider()
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        m_start = st.number_input("📈 里程(起)", value=None, placeholder="輸入起點里程")
    with col_m2:
        m_end = st.number_input("📉 里程(迄)", value=None, placeholder="輸入終點里程")

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        p_sent = st.number_input("送板數", value=None, placeholder="輸入數量")
        basket_count = st.number_input("空籃數", value=None, placeholder="輸入數量")
    with col_p2:
        p_recv = st.number_input("收板數", value=None, placeholder="輸入數量")
        plate_count = st.number_input("空板數", value=None, placeholder="輸入數量")
    
    remark = st.text_input("💬 備註")

    if st.button("🚀 確認送出報表", use_container_width=True):
        if route_name == "請選擇路線" or m_start is None or m_end is None:
            st.warning("⚠️ 請填寫完整路線與里程！")
        else:
            with st.spinner('同步至雲端中...'):
                try:
                    sheet, _ = get_sheet_and_data()
                    actual_dist = int(m_end - m_start)
                    ps, pr = int(p_sent or 0), int(p_recv or 0)
                    bc, pc = int(basket_count or 0), int(plate_count or 0)
                    cc = int(customer_count or 0)
                    
                    # 計算工時 (用於後續效益分析)
                    fmt = '%H:%M'
                    tdelta = datetime.strptime(end_time, fmt) - datetime.strptime(start_time, fmt)
                    work_hours = round(tdelta.seconds / 3600, 2)

                    cust_info = f"{cc}家 ({customer_detail})" if customer_detail else f"{cc}家"
                    new_row = [selected_driver, str(input_date), start_time, end_time, route_name, int(m_start), int(m_end), actual_dist, ps, pr, ps+pr, bc, pc, cust_info, remark, work_hours]
                    sheet.append_row(new_row)
                    st.success("🎉 存檔成功！")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"連線失敗：{e}")

# --- 4. 統計分析區 (Excel 進階數據版) ---
st.divider()
if st.button("📊 查看進階效益分析 (對標 Excel)"):
    with st.spinner('正在分析各路線指標...'):
        try:
            _, df = get_sheet_and_data()
            if not df.empty:
                df['日期'] = df['日期'].astype(str)
                this_month = datetime.now().strftime("%Y-%m")
                month_data = df[df['日期'].str.contains(this_month)].copy()
                
                if not month_data.empty:
                    # 數值轉換
                    num_cols = ['實際里程', '送板', '收板', '合計板數', '空籃', '空板']
                    for c in num_cols:
                        month_data[c] = pd.to_numeric(month_data[c], errors='coerce').fillna(0)
                    
                    # 路線彙總運算 (對標您的 Excel 指標)
                    route_analysis = month_data.groupby('路線別').agg({
                        '日期': 'count',
                        '實際里程': 'sum',
                        '送板': 'sum',
                        '收板': 'sum',
                        '合計板數': 'sum'
                    }).reset_index()
                    
                    route_analysis.columns = ['路線別', '趟次', '里程數', '(送)板數', '(收)板數', '合計板數']
                    
                    # 計算進階指標
                    route_analysis['每點板數'] = (route_analysis['合計板數'] / route_analysis['趟次']).round(1)
                    route_analysis['每點里程數'] = (route_analysis['里程數'] / route_analysis['趟次']).round(1)
                    
                    # 效益指標計算 (範例邏輯：權重計算)
                    route_analysis['效益指標'] = ((route_analysis['合計板數'] * 0.7) + (route_analysis['里程數'] * 0.3)).round(0)
                    
                    # 排名計算
                    route_analysis['效益排名'] = route_analysis['效益指標'].rank(ascending=False, method='min').astype(int)
                    route_analysis['板數排名'] = route_analysis['合計板數'].rank(ascending=False, method='min').astype(int)
                    
                    st.subheader(f"📈 {this_month} 路線效益分析表")
                    
                    # 格式美化：對標 Excel 顯示順序
                    excel_view = route_analysis[['路線別', '效益排名', '板數排名', '趟次', '里程數', '(送)板數', '(收)板數', '合計板數', '每點板數', '每點里程數', '效益指標']]
                    
                    # 顯示表格 (隱藏索引，移除小數點)
                    st.dataframe(excel_view.sort_values('效益排名'), use_container_width=True, hide_index=True)
                    
                    st.info("💡 註：效益指標與排名是根據當月各路線的載運板數與總里程綜合評分得出。")
                    
                    # 獎金合計顯示
                    total_bonus = (month_data['合計板數'] * 40 + month_data['空籃'] / 2 + month_data['空板'] * 3).sum()
                    st.success(f"💰 當月預估獎金合計：{int(total_bonus)} 元")
                else:
                    st.warning("本月尚無填報紀錄。")
        except Exception as e:
            st.error(f"分析失敗：{e}")
