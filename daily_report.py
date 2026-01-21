import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time

# 1. 頁面配置 (維持寬版以對應 Excel 豐富欄位)
st.set_page_config(page_title="運輸管理系統", page_icon="🚚", layout="wide")

st.markdown("""
    <style>
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    button[step="1"] { display: none !important; }
    input[type=number] { -moz-appearance: textfield; }
    input::-webkit-outer-spin-button, input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
    .stButton>button {
        width: 100%; border-radius: 12px; background-color: #007BFF; 
        color: white; height: 3.8em; font-size: 18px; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📝 運輸日報表")

# 2. 核心連線
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

# --- 3. 填報介面區 (嚴格順序：里程起 -> 板數 -> 點數 -> 里程迄) ---
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
    
    # 司機輸入今日配送點數
    customer_count = st.number_input("🏠 配送點數 (今日點位數)", value=None, placeholder="輸入家數", step=1)
    
    st.divider()
    # 按照要求排列且無小數點
    m_start = st.number_input("📈 里程(起)", value=None, placeholder="起點里程", step=1)
    p_sent = st.number_input("🚚 送板數", value=None, placeholder="輸入數量", step=1)
    p_recv = st.number_input("📥 收板數", value=None, placeholder="輸入數量", step=1)
    basket_count = st.number_input("🧺 空籃數", value=None, placeholder="輸入數量", step=1)
    plate_count = st.number_input("🔄 空板數", value=None, placeholder="輸入數量", step=1)
    m_end = st.number_input("📉 里程(迄)", value=None, placeholder="終點里程", step=1)
    
    remark = st.text_input("💬 備註")

    if st.button("🚀 確認送出報表", use_container_width=True):
        if route_name == "請選擇路線" or m_start is None or m_end is None or customer_count is None:
            st.warning("⚠️ 路線、里程與點數皆為必填！")
        else:
            with st.spinner('數據同步中...'):
                try:
                    sheet, _ = get_sheet_and_data()
                    actual_dist = int(m_end - m_start)
                    ps, pr, bc, pc, cc = int(p_sent or 0), int(p_recv or 0), int(basket_count or 0), int(plate_count or 0), int(customer_count or 0)
                    # 按照 A-O 欄位順序寫入 [cite: 2026-01-21]
                    new_row = [selected_driver, str(input_date), start_time, end_time, route_name, int(m_start), int(m_end), actual_dist, ps, pr, ps+pr, bc, pc, cc, remark]
                    sheet.append_row(new_row)
                    st.success("🎉 存檔成功！畫面已自動重置。")
                    time.sleep(1)
                    st.rerun() 
                except Exception as e:
                    st.error(f"連線失敗：{e}")

# --- 4. 績效生產力分析 (對標 Excel 最終修正版) ---
st.divider()
if st.button("📊 查看績效效益分析 (對標 Excel)"):
    with st.spinner('重新核算各路線平均里程與績效...'):
        try:
            _, df = get_sheet_and_data()
            if not df.empty:
                df['日期'] = df['日期'].astype(str)
                this_month = datetime.now().strftime("%Y-%m")
                month_data = df[df['日期'].str.contains(this_month)].copy()
                
                if not month_data.empty:
                    # 確保所有數據欄位皆為數值型態
                    map_cols = {'里程': '實際里程', '板數': '合計收送板數', '點數': '配送家數', '空籃': '空籃', '空板': '空板'}
                    for k, v in map_cols.items():
                        found = next((c for c in month_data.columns if v in c or k in c), None)
                        if found:
                            month_data[k] = pd.to_numeric(month_data[found], errors='coerce').fillna(0)
                        else:
                            month_data[k] = 0

                    # --- 正確匯總邏輯：先求總和再算平均 ---
                    analysis = month_data.groupby('路線別').agg({
                        '日期': 'count',
                        '里程': 'sum',      # 總里程
                        '板數': 'sum',      # 獲利分子
                        '點數': 'sum'       # 總點數
                    }).reset_index()
                    
                    analysis.columns = ['路線別', '趟次', '總里程', '總板數', '總點數']
                    
                    # 修正：平均里程 = 總里程 / 趟次
                    analysis['平均里程'] = (analysis['總里程'] / analysis['趟次']).round(0).astype(int)
                    
                    # 修正：平均點數 = 總點數 / 趟次
                    analysis['平均點數'] = (analysis['總點數'] / analysis['趟次']).round(1)
                    
                    # 對標 Excel 績效排名邏輯：板數越高且里程/點數負擔越低則排名越前
                    def calc_efficiency(row):
                        # 分母為單位成本 (平均里程與平均點數的綜合佔比)
                        denominator = (row['平均里程'] * 0.4) + (row['平均點數'] * 0.6)
                        if denominator == 0: return 0
                        return round((row['總板數'] / denominator) * 10, 1)

                    analysis['生產力指標'] = analysis.apply(calc_efficiency, axis=1)
                    analysis['績效排名'] = analysis['生產力指標'].rank(ascending=False, method='min').astype(int)

                    # 呈現摘要摘要
                    st.subheader(f"📅 {this_month} 績效摘要")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("當月總趟數", f"{len(month_data)}")
                    c2.metric("合計總板數", f"{int(month_data['板數'].sum())}")
                    c3.metric("合計空籃", f"{int(month_data['空籃'].sum())}")
                    c4.metric("合計空板", f"{int(month_data['空板'].sum())}")

                    st.write("🛣️ 路線效能對照表：")
                    # 顯示欄位對標您的 Excel
                    show_view = analysis[['績效排名', '路線別', '趟次', '平均里程', '平均點數', '總板數', '生產力指標']]
                    st.dataframe(show_view.sort_values('績效排名'), use_container_width=True, hide_index=True)
                    
                    # 獎金合計 (同步 2026-01-21 紀錄)
                    bonus = int(month_data['板數'].sum() * 40 + month_data['空籃'].sum() / 2 + month_data['空板'].sum() * 3)
                    st.success(f"💰 當月預估獎金合計：{bonus} 元")
                else:
                    st.warning("本月尚無資料。")
        except Exception as e:
            st.error(f"分析失敗，錯誤：{e}")
