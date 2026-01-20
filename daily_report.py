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
    # 3. 讀取您之前已經存好的 Secrets 金鑰
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # 4. 開啟您的試算表 (請確認您的 Google 試算表名稱真的是『運輸成本紀錄』)
    spreadsheet_name = "運輸成本紀錄" 
    sh = client.open(spreadsheet_name)
    sheet = sh.get_worksheet(0)
    
    # 5. 抓取資料並用表格顯示
    data = sheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        st.success("✅ 資料連線成功！")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("連線成功！但目前試算表內沒有資料，請先在 Excel 裡填入內容。")

except Exception as e:
    st.error(f"連線失敗，原因：{e}")
    st.info("提示：請確認您的 Google 試算表名稱正確，且已『共用』給機器人 Email。")
