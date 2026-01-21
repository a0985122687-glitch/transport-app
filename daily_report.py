import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time

# 1. 頁面配置
st.set_page_config(page_title="運輸管理系統", page_icon="🚚", layout="wide")

# --- 溫和美化：只隱藏頂部貓咪，確保不傷及資料明細 ---
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

# --- 3. 填報介面區 ---
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
    
    # 客戶維度
    col_cust1, col_cust2 = st.columns([1, 2])
    with col_cust1:
        customer_count = st.number_input("配送家數", value=None, placeholder="家數")
    with col_cust2:
        customer_detail = st.text_input("客戶別/板數", placeholder="例: A/3, B/2")

    st.divider()
    # 里程與數量：預設全空白，無正負號
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        m_start = st.number_input("📈 里程(起)", value=None, placeholder="輸入起點里程")
    with col_m2:
        m_end = st.number_input("📉 里程(迄)", value=None, placeholder="輸入終點里程")

    # 顯示順序：送板 -> 收板 -> 空籃 -> 空板
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
            st.warning("⚠️ 請填妥路線與里程！")
        else:
            with st.spinner('同步中...'):
                try:
                    sheet, _ = get_sheet_and_data()
                    actual_dist = int(m_end - m_start)
                    ps, pr = int(p_sent or 0), int(p_recv or 0)
                    bc, pc = int(basket_count or 0), int(plate_count or 0)
                    cc = int(customer_count or 0)
                    
                    # 寫入 A-O 欄位順序 [cite: 2026-01-21]
                    new_row = [selected_driver, str(input_date), start_time, end_time, route_name, int(m_start), int(m_end), actual_dist, ps, pr, ps+pr, bc, pc, f"{cc}家|{customer_detail}", remark]
                    sheet.append_row(new_row)
                    st.success("🎉 存檔成功！")
                    time.sleep(1)
                    st.rerun() # 自動歸零
                except Exception as e:
                    st.error(f"連線失敗：{e}")

# --- 4. 統計分析區 (整數化與效益分析) ---
st.divider()
if st.button("📊 查看路線效益分析 (對標 Excel)"):
    with st.spinner('分析中...'):
        try:
            _, df = get_sheet_and_data()
            if not df.empty:
                df['日期'] = df['日期'].astype(str)
                this_month = datetime.now().strftime("%Y-%m")
                month_data = df[df['日期'].str.contains(this_month)].copy()
                
                if not month_data.empty:
                    # 數值轉型與標準化 (移除小數點)
                    for c in ['實際里程', '合計板數', '空籃', '空板']:
                        col_key = c if c in month_data.columns else (c+'回收' if (c+'回收') in month_data.columns else c)
                        month_data[c] = pd.to_numeric(month_data[col_key], errors='coerce').fillna(0).astype(int)

                    # 彙總分析
                    analysis = month_data.groupby('路線別').agg({
                        '日期': 'count',
                        '實際里程': 'sum',
                        '合計板數': 'sum'
                    }).reset_index()
                    
                    analysis.columns = ['路線別', '趟次', '里程數', '合計板數']
                    analysis['均點板數'] = (analysis['合計板數'] / analysis['趟次']).round(1)
                    analysis['效益排名'] = analysis['合計板數'].rank(ascending=False, method='min').astype(int)
                    
                    st.subheader(f"📅 {this_month} 效益概況")
                    
                    # 核心指標
                    m1, m2 = st.columns(2)
                    m1.metric("當月趟數", f"{len(month_data)} 趟")
                    m2.metric("合計總板數", f"{int(month_data['合計板數'].sum())} 板")

                    # 顯示效益表格
                    st.table(analysis.sort_values('效益排名'))

                    # 獎金明細 (整數化)
                    total_bonus = (month_data['合計板數'] * 40 + month_data['空籃'] / 2 + month_data['空板'] * 3).sum()
                    st.success(f"💰 當月預估獎金合計：{int(total_bonus)} 元")
                else:
                    st.warning("本月尚無填報紀錄。")
        except Exception as e:
            st.error(f"分析失敗：{e}")
