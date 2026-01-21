import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time

# 1. 頁面配置 (寬版顯示，方便查看對比表)
st.set_page_config(page_title="運輸管理系統", page_icon="🚚", layout="wide")

st.markdown("""
    <style>
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 移除數字輸入框的調節按鈕並防止小數點 */
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

# --- 3. 填報介面區 (嚴格依序排列) ---
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
    
    # 加入配送點數手動填寫
    customer_count = st.number_input("🏠 配送家數 (今日配送點數)", value=None, placeholder="請輸入點數", step=1)
    
    st.divider()
    # 填報流程：里程起 -> 板數 -> 空籃 -> 空板 -> 里程迄
    m_start = st.number_input("📈 里程(起)", value=None, placeholder="出車前里程", step=1)
    p_sent = st.number_input("🚚 送板數", value=None, placeholder="數量", step=1)
    p_recv = st.number_input("📥 收板數", value=None, placeholder="數量", step=1)
    basket_count = st.number_input("🧺 空籃數", value=None, placeholder="數量", step=1)
    plate_count = st.number_input("🔄 空板數", value=None, placeholder="數量", step=1)
    m_end = st.number_input("📉 里程(迄)", value=None, placeholder="收車後里程", step=1)
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
                    
                    # 按照 A-O 欄位順序寫入試算表
                    new_row = [selected_driver, str(input_date), start_time, end_time, route_name, int(m_start), int(m_end), actual_dist, ps, pr, ps+pr, bc, pc, cc, remark]
                    sheet.append_row(new_row)
                    st.success("🎉 存檔成功！畫面已自動重置。")
                    time.sleep(1)
                    st.rerun() 
                except Exception as e:
                    st.error(f"連線失敗：{e}")

# --- 4. 統計分析區 (對標 Excel 績效理論) ---
st.divider()
if st.button("📊 查看路線績效效益分析"):
    with st.spinner('重新核算里程與生產力...'):
        try:
            _, df = get_sheet_and_data()
            if not df.empty:
                df['日期'] = df['日期'].astype(str)
                this_month = datetime.now().strftime("%Y-%m")
                month_data = df[df['日期'].str.contains(this_month)].copy()
                
                if not month_data.empty:
                    # 數值化處理與防錯匹配
                    map_cols = {'起': '里程(起)', '迄': '里程(迄)', '實際': '實際里程', '板數': '合計收送板數', '家數': '配送家數', '空籃': '空籃', '空板': '空板'}
                    for k, v in map_cols.items():
                        found = next((c for c in month_data.columns if v in c), None)
                        month_data[k] = pd.to_numeric(month_data[found], errors='coerce').fillna(0) if found else 0

                    # --- 核心摘要摘要 ---
                    st.subheader(f"📅 {this_month} 營運摘要")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("當月總趟數", f"{len(month_data)}")
                    c2.metric("合計總板數", f"{int(month_data['板數'].sum())}")
                    c3.metric("合計空籃", f"{int(month_data['空籃'].sum())}")
                    c4.metric("合計空板", f"{int(month_data['空板'].sum())}")

                    # --- 路線生產力排名分析 ---
                    analysis = month_data.groupby('路線別').agg({
                        '日期': 'count',
                        '起': 'sum',
                        '迄': 'sum',
                        '實際': 'sum',
                        '板數': 'sum',
                        '家數': 'sum'
                    }).reset_index()
                    analysis.columns = ['路線別', '趟次', '總起點', '總迄點', '總實際里程', '總板數', '總家數']
                    
                    # 修正：平均里程公式 = ((總起點 + 總迄點) - 總實際里程) / 趟次
                    analysis['平均里程'] = (((analysis['總起點'] + analysis['總迄點']) - analysis['總實際里程']) / analysis['趟次']).round(0).astype(int)
                    
                    # 修正：平均點數 = 總家數 / 趟次
                    analysis['平均點數'] = (analysis['總家數'] / analysis['趟次']).round(1)
                    
                    # 績效生產力 = 總板數 / (平均里程 * 0.4 + 平均點數 * 0.6) -> 分母為成本加權
                    def calc_prod(row):
                        denominator = (row['平均里程'] * 0.4) + (row['平均點數'] * 0.6)
                        if denominator == 0: return 0
                        return round((row['總板數'] / denominator) * 10, 1)

                    analysis['生產力指標'] = analysis.apply(calc_prod, axis=1)
                    analysis['績效排名'] = analysis['生產力指標'].rank(ascending=False, method='min').astype(int)

                    st.write("🛣️ 路線績效對照表 (依生產力排名)：")
                    view_df = analysis[['績效排名', '路線別', '趟次', '平均里程', '平均點數', '總板數', '生產力指標']]
                    st.dataframe(view_df.sort_values('績效排名'), use_container_width=True, hide_index=True)
                    
                    # 獎金合計 (板數*40 + 空籃/2 + 空板*3) [cite: 2026-01-21]
                    total_bonus = int(month_data['板數'].sum() * 40 + month_data['空籃'].sum() / 2 + month_data['空板'].sum() * 3)
                    st.success(f"💰 當月預估獎金合計：{total_bonus} 元")
                    
                else:
                    st.warning("本月尚無資料。")
        except Exception as e:
            st.error(f"分析失敗：{e}")
