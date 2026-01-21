import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time

# 1. 頁面配置 (寬版顯示)
st.set_page_config(page_title="運輸管理系統", page_icon="🚚", layout="wide")

st.markdown("""
    <style>
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 徹底隱藏加減按鈕並防止小數點輸入 */
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

# --- 3. 填報介面區 (依司機實際作業流程順序) ---
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
    
    # 配送家數
    customer_count = st.number_input("🏠 配送家數", value=None, placeholder="輸入總家數", step=1)

    st.divider()
    
    # 里程(起) - 放在最上方
    m_start = st.number_input("📈 里程(起)", value=None, placeholder="出車前里程", step=1)

    # 配送明細 (順序：送板 -> 收板 -> 空籃 -> 空板)
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        p_sent = st.number_input("🚚 送板數", value=None, placeholder="輸入數量", step=1)
        basket_count = st.number_input("🧺 空籃數", value=None, placeholder="輸入數量", step=1)
    with col_p2:
        p_recv = st.number_input("📥 收板數", value=None, placeholder="輸入數量", step=1)
        plate_count = st.number_input("🔄 空板數", value=None, placeholder="輸入數量", step=1)

    # 里程(迄) - 放在最下方
    m_end = st.number_input("📉 里程(迄)", value=None, placeholder="收車後里程", step=1)
    
    remark = st.text_input("💬 備註")

    if st.button("🚀 確認送出報表", use_container_width=True):
        if route_name == "請選擇路線" or m_start is None or m_end is None:
            st.warning("⚠️ 請填妥路線與里程！")
        else:
            with st.spinner('同步中...'):
                try:
                    sheet, _ = get_sheet_and_data()
                    actual_dist = int(m_end - m_start)
                    ps, pr = int(p_sent or 0), int(p_recv or 0)
                    bc, pc = int(basket_count or 0), int(plate_count or 0)
                    cc = int(customer_count or 0)
                    
                    # 按照 A-O 欄位順序寫入試算表 [cite: 2026-01-21]
                    new_row = [selected_driver, str(input_date), start_time, end_time, route_name, int(m_start), int(m_end), actual_dist, ps, pr, ps+pr, bc, pc, cc, remark]
                    sheet.append_row(new_row)
                    st.success("🎉 存檔成功！已重置畫面。")
                    time.sleep(1)
                    st.rerun() # 自動歸零
                except Exception as e:
                    st.error(f"連線失敗：{e}")

# --- 4. 統計分析區 (整數美化版) ---
st.divider()
if st.button("📊 查看路線效益分析"):
    with st.spinner('資料分析中...'):
        try:
            _, df = get_sheet_and_data()
            if not df.empty:
                # 數值整數化處理
                for c in ['實際里程', '送板', '收板', '合計板數']:
                    if c in df.columns:
                        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)

                this_month = datetime.now().strftime("%Y-%m")
                month_data = df[df['日期'].astype(str).str.contains(this_month)].copy()
                
                if not month_data.empty:
                    # 分類彙總與效益排名
                    analysis = month_data.groupby('路線別').agg({
                        '日期': 'count',
                        '實際里程': 'sum',
                        '合計板數': 'sum'
                    }).reset_index()
                    
                    analysis.columns = ['路線別', '趟次', '總里程', '合計板數']
                    analysis['均點板數'] = (analysis['合計板數'] / analysis['趟次']).round(0).astype(int)
                    # 效益排名：合計板數越多排名越高
                    analysis['效益排名'] = analysis['合計板數'].rank(ascending=False, method='min').astype(int)
                    
                    st.subheader(f"📅 {this_month} 路線競爭力排名")
                    # 隱藏左側空白索引列
                    st.dataframe(analysis.sort_values('效益排名'), use_container_width=True, hide_index=True)
                    
                    # 獎金公式：合計板數*40, 空籃/2, 空板*3 [cite: 2026-01-21]
                    # 注意：此處僅概算載運獎金，完整明細請見 Google Sheet
                    st.success(f"💰 當月預估載運獎金合計：{int(month_data['合計板數'].sum() * 40)} 元")
                else:
                    st.warning("本月尚無填報紀錄。")
        except Exception as e:
            st.error(f"分析失敗：{e}")
