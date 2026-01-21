import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import time

# 1. 頁面配置與隱藏選單
st.set_page_config(page_title="運輸管理系統", page_icon="🚚", layout="centered")

st.markdown("""
    <style>
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 隱藏數字輸入框的加減按鈕 */
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
    
    # 新增：配送家數與客戶板數明細
    col_cust1, col_cust2 = st.columns([1, 2])
    with col_cust1:
        customer_count = st.number_input("配送家數", value=None, placeholder="家數", step=1)
    with col_cust2:
        customer_detail = st.text_input("客戶別/板數", placeholder="例: A店/3, B店/2")

    st.divider()
    
    # 里程輸入
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        m_start = st.number_input("📈 里程(起)", value=None, placeholder="輸入起點里程")
    with col_m2:
        m_end = st.number_input("📉 里程(迄)", value=None, placeholder="輸入終點里程")

    # 板數與回收 (順序：送板 -> 收板 -> 空籃 -> 空板)
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
                    cc = int(customer_count) if customer_count is not None else 0
                    
                    total_plates = ps + pr
                    # 按照 A-O 欄位順序寫入試算表 (將客戶資訊放入原預留位置)
                    # 順序：司機, 日期, 上班, 下班, 路線, 里程起, 里程迄, 實際里程, 送板, 收板, 合計板, 空籃, 空板, 客戶資訊(家數/明細), 備註
                    cust_info = f"{cc}家 ({customer_detail})" if customer_detail else f"{cc}家"
                    new_row = [selected_driver, str(input_date), start_time, end_time, route_name, int(m_start), int(m_end), actual_dist, ps, pr, total_plates, bc, pc, cust_info, remark]
                    
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
    with st.spinner('讀取中...'):
        try:
            _, df = get_sheet_and_data()
            if not df.empty:
                df['日期'] = df['日期'].astype(str)
                this_month = datetime.now().strftime("%Y-%m")
                month_data = df[df['日期'].str.contains(this_month)].copy()
                
                if not month_data.empty:
                    for c in ['實際里程', '合計收送板數', '空籃', '空板']:
                        col_target = c if c in month_data.columns else (c+'回收' if (c+'回收') in month_data.columns else c)
                        month_data[c] = pd.to_numeric(month_data[col_target], errors='coerce').fillna(0).astype(int)

                    month_data['載運獎金'] = (month_data['合計收送板數'] * 40).astype(int)
                    month_data['空籃獎金'] = (month_data['空籃'] / 2).astype(int)
                    month_data['空板獎金'] = (month_data['空板'] * 3).astype(int)
                    month_data['合計獎金'] = (month_data['載運獎金'] + month_data['空籃獎金'] + month_data['空板獎金']).astype(int)

                    st.subheader(f"📅 {this_month} 統計摘要")
                    m1, m2 = st.columns(2)
                    m1.metric("當月趟數", f"{len(month_data)} 趟")
                    m2.metric("合計總板數", f"{int(month_data['合計收送板數'].sum())} 板")

                    st.write("🛣️ 各路線平均里程 (整數)：")
                    avg_route = month_data.groupby('路線別')['實際里程'].mean().reset_index()
                    avg_route.columns = ['路線名稱', '平均里程']
                    avg_route['平均里程'] = avg_route['平均里程'].astype(int)
                    st.table(avg_route)

                    st.success(f"💰 當月預估獎金合計：{int(month_data['合計獎金'].sum())} 元")
                    
                    st.write("📋 獎金統計明細：")
                    show_cols = ['日期', '路線別', '合計收送板數', '合計獎金']
                    final_df = month_data[show_cols].tail(10)
                    st.dataframe(final_df, use_container_width=True, hide_index=True)
                else:
                    st.warning("本月尚無資料。")
            else:
                st.info("目前雲端無資料。")
        except Exception as e:
            st.error(f"讀取失敗：{e}")
