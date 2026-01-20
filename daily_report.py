import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# 1. 設定標題
st.set_page_config(page_title="運輸日報表 Pro", layout="wide")
st.title("🚚 運輸日報表 Pro")

# 2. 連接 Google Sheets (雲端保險箱版)
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

try:
    if "gcp_service_account" in st.secrets:
        # 雲端環境使用 Secrets
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        # 本機環境使用檔案
        creds = Credentials.from_service_account_file("service_account.json", scopes=scopes)
    
    client = gspread.authorize(creds)
    # 請確保這跟您的 Google Sheet 檔案名稱一模一樣
    sh = client.open("運輸成本紀錄") 
    wks = sh.get_worksheet(0)
    st.success("✅ 已成功連接 Google 試算表！")
except Exception as e:
    st.error(f"❌ 連線錯誤：{e}")
    st.stop()

# 3. 輸入介面
st.subheader("新增趟次資料")
col1, col2, col3 = st.columns(3)

with col1:
    date = st.date_input("日期")
    route = st.text_input("路線", placeholder="例如：台北-台中")
with col2:
    driver = st.text_input("司機姓名")
    miles = st.number_input("行駛里程 (km)", min_value=0.0, step=0.1)
with col3:
    points = st.number_input("配送點數", min_value=0, step=1)
    bonus = st.number_input("趟次獎金", min_value=0)

# 4. 提交按鈕
if st.button("確認送出 📤"):
    new_data = [str(date), route, driver, miles, points, bonus]
    wks.append_row(new_data)
    st.balloons()
    st.success("資料已成功存入 Google 試算表！")

# 5. 顯示最近資料
st.divider()
st.subheader("最近 5 筆紀錄")
data = wks.get_all_records()
if data:
    df = pd.DataFrame(data)
    st.table(df.tail(5))
else:
    st.info("目前尚無資料紀錄。")