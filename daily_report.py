import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# 1. 網頁基本設定 (Transport Daily Report Pro)
st.set_page_config(page_title="運輸日報表 Pro", page_icon="🚚")
st.title("🚚 運輸日報表 Pro")

# 2. 設定連線權限
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    # 3. 讀取您剛才存好的 Secrets (gcp_service_account)
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # 4. 開啟您的試算表 (名稱必須與第一步改的一模一樣)
    spreadsheet_name = "Transport_System_2026" 
    sh = client.open(spreadsheet_name)
    sheet = sh.get_worksheet(0)
    
    # 5. 抓取資料並用表格顯示
    data = sheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        st.success("✅ 資料連線成功！")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("連線成功！但試算表內目前沒有資料，請先在表格內填入內容。")

except Exception as e:
    st.error(f"連線失敗，原因：{e}")
    st.info("提示：請確保 Secrets 已儲存，且試算表已『共用』給機器人 Email。")
