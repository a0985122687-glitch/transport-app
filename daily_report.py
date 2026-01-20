import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

st.set_page_config(page_title="運輸日報表 Pro", page_icon="🚚")
st.title("🚚 運輸日報表 Pro")

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    # 直接讀取保險箱標籤
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # 開啟對應名稱的試算表
    sh = client.open("Transport_System_2026")
    sheet = sh.get_worksheet(0)
    
    data = sheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        st.success("✅ 資料連線成功！")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("連線成功，但表格目前沒有資料。")

except Exception as e:
    st.error(f"連線失敗：{e}")
