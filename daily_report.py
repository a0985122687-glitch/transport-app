import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time

# 1. 頁面配置
st.set_page_config(page_title="運輸管理系統", page_icon="🚚", layout="centered")

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

# --- 3. 填報介面區 (嚴格垂直依序排列) ---
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
    
    # 點數輸入：司機手動輸入當日實際配送家數
    customer_count = st.number_input("🏠 配送點數 (今日送幾家)", value=None, placeholder="請輸入整數", step=1)
    st.divider()
    
    # 依序排列且無小數點
    m_start = st.number_input("📈 里程(起)", value=None, placeholder="出車前儀表里程", step=1)
    p_sent = st.number_input("🚚 送板數", value=None, placeholder="輸入數量", step=1)
    p_recv = st.number_input("📥 收板數", value=None, placeholder="輸入數量", step=1)
    basket_count = st.number_input("🧺 空籃數", value=None, placeholder="輸入數量", step=1)
    plate_count = st.number_input("🔄 空板數", value=None, placeholder="輸入數量", step=1)
    m_end = st.number_input("📉 里程(迄)", value=None, placeholder="收車後儀表里程", step=1)
    remark = st.text_input("💬 備註")

    if st.button("🚀 確認送出報表", use_container_width=True):
        if route_name == "請選擇路線" or m_start is None or m_end is None or customer_count is None:
            st.warning("⚠️ 請填妥所有必要欄位（包含配送點數與里程）！")
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

# --- 4. 績效生產力分析 (對標 Excel 邏輯) ---
st.divider()
if st.button("📊 查看路線績效分析"):
    with st.spinner('計算月度績效中...'):
        try:
            _, df = get_sheet_and_data()
            if not df.empty:
                df['日期'] = df['日期'].astype(str)
                this_month = datetime.now().strftime("%Y-%m")
                month_data = df[df['日期'].str.contains(this_month)].copy()
                
                if not month_data.empty:
                    # 數值標準化 (確保移除小數點)
                    map_cols = {'里程': '實際里程', '板數': '合計收送板數', '點數': '配送家數', '空籃': '空籃', '空板': '空板'}
                    for k, v in map_cols.items():
                        found = next((c for c in month_data.columns if v in c), None)
                        if found:
                            month_data[k] = pd.to_numeric(month_data[found], errors='coerce').fillna(0)
                        else:
                            month_data[k] = 0

                    # --- 頂部摘要 ---
                    st.subheader(f"📅 {this_month} 績效摘要")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("當月總趟數", f"{len(month_data)}")
                    c2.metric("合計總板數", f"{int(month_data['板數'].sum())}")
                    c3.metric("合計空籃", f"{int(month_data['空籃'].sum())}")
                    c4.metric("合計空板", f"{int(month_data['空板'].sum())}")

                    # --- 生產力分析 (獲利分子/成本分母) ---
                    analysis = month_data.groupby('路線別').agg({
                        '日期': 'count',
                        '里程': 'mean',
                        '板數': 'sum',
                        '點數': 'mean'
                    }).reset_index()
                    
                    analysis.columns = ['路線別', '趟次', '平均里程', '總板數', '平均點數']
                    
                    # 績效公式：獲利(總板數) / 成本(平均里程 * 平均點數)
                    def calc_productivity(row):
                        cost_denominator = row['平均里程'] * row['平均點數']
                        if cost_denominator == 0: return 0
                        return round((row['總板數'] / cost_denominator) * 100, 1)

                    analysis['生產力指標'] = analysis.apply(calc_productivity, axis=1)
                    analysis['績效排名'] = analysis['生產力指標'].rank(ascending=False, method='min').astype(int)
                    
                    # 整數美化
                    analysis['平均里程'] = analysis['平均里程'].astype(int)
                    analysis['平均點數'] = analysis['平均點數'].astype(int)

                    st.write("🛣️ 路線生產力排名分析：")
                    st.dataframe(analysis.sort_values('績效排名'), use_container_width=True, hide_index=True)
                    
                    # 獎金合計 (含公式) [cite: 2026-01-21]
                    total_bonus = int(month_data['板數'].sum() * 40 + month_data['空籃'].sum() / 2 + month_data['空板'].sum() * 3)
                    st.success(f"💰 當月預估獎金合計：{total_bonus} 元")
                else:
                    st.warning("本月尚無紀錄。")
        except Exception as e:
            st.error(f"分析失敗，請確認試算表欄位名稱：{e}")
