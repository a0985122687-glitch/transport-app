import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time

# 1. 頁面配置 (寬版以呈現 Excel 指標)
st.set_page_config(page_title="運輸管理系統", page_icon="🚚", layout="wide")

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

# --- 3. 填報介面區 (客戶維度) ---
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
        customer_count = st.number_input("配送家數", value=None, placeholder="家數")
    with col_cust2:
        customer_detail = st.text_input("客戶別/板數", placeholder="例: 客戶A/3, 客戶B/5")

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
            st.warning("⚠️ 請填妥路線與里程！")
        else:
            with st.spinner('同步中...'):
                try:
                    sheet, _ = get_sheet_and_data()
                    actual_dist = int(m_end - m_start)
                    ps, pr = int(p_sent or 0), int(p_recv or 0)
                    bc, pc = int(basket_count or 0), int(plate_count or 0)
                    cc = int(customer_count or 0)
                    
                    new_row = [selected_driver, str(input_date), start_time, end_time, route_name, int(m_start), int(m_end), actual_dist, ps, pr, ps+pr, bc, pc, f"{cc}家|{customer_detail}", remark]
                    sheet.append_row(new_row)
                    st.success("🎉 存檔成功！")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"連線失敗：{e}")

# --- 4. 統計分析區 (對標 Excel 指標) ---
st.divider()
if st.button("📊 查看進階效益分析 (對標 Excel)"):
    with st.spinner('正在彙總各路線指標...'):
        try:
            _, df = get_sheet_and_data()
            if not df.empty:
                # 欄位容錯匹配：自動尋找包含關鍵字的欄位
                col_map = {
                    '里程': next((c for c in df.columns if '實際里程' in c or '里程數' in c), '實際里程'),
                    '合計': next((c for c in df.columns if '合計' in c and '板' in c), '合計板數'),
                    '空籃': next((c for c in df.columns if '空籃' in c), '空籃'),
                    '空板': next((c for c in df.columns if '空板' in c), '空板')
                }
                
                this_month = datetime.now().strftime("%Y-%m")
                month_data = df[df['日期'].astype(str).str.contains(this_month)].copy()
                
                if not month_data.empty:
                    for k, v in col_map.items():
                        month_data[k] = pd.to_numeric(month_data[v], errors='coerce').fillna(0)

                    # 彙總分析
                    analysis = month_data.groupby('路線別').agg({
                        '日期': 'count',
                        '里程': 'sum',
                        '合計': 'sum'
                    }).reset_index()
                    
                    analysis.columns = ['路線別', '趟次', '總里程', '合計板數']
                    analysis['均點板數'] = (analysis['合計板數'] / analysis['趟次']).round(1)
                    # 效益值：對標您檔案中的權重邏輯
                    analysis['效益值'] = ((analysis['合計板數'] * 0.8) + (analysis['總里程'] * 0.2)).round(0).astype(int)
                    analysis['效益排名'] = analysis['效益值'].rank(ascending=False, method='min').astype(int)

                    st.subheader(f"📅 {this_month} 路線競爭力排名")
                    # 隱藏索引列美化
                    st.dataframe(analysis.sort_values('效益排名'), use_container_width=True, hide_index=True)
                    
                    st.success(f"💰 當月預估獎金合計：{int(month_data['合計'].sum() * 40)} 元")
                else:
                    st.warning("本月尚無紀錄。")
        except Exception as e:
            st.error(f"分析失敗，請檢查試算表欄位名稱。錯誤原因：{e}")
