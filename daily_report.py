import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# 1. 網頁基本設定
st.set_page_config(page_title="運輸日報表 Pro", page_icon="🚚")
st.title("🚚 運輸日報表 Pro")

# 2. 設定 Google Sheets 連線權限
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    # 核心修復：從 st.secrets 讀取您之前儲存成功的 [gcp_service_account]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # 3. 開啟您的試算表 (請確認名稱與您的 Google 表格完全一致)
    spreadsheet_name = "運輸成本紀錄" 
    sh = client.open(spreadsheet_name)
    sheet = sh.get_worksheet(0)
    
    # 4. 抓取資料並呈現
    data = sheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        st.success("✅ 資料連線成功！")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("連線成功！但目前表格內沒有資料，請先在 Excel 裡填入內容。")

except Exception as e:
    st.error(f"連線失敗，原因：{e}")
    st.info("提示：請確認試算表名稱正確，且已『共用』給機器人 Email。")
