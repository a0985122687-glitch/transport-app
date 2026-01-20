import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

st.set_page_config(page_title="運輸日報表 Pro", page_icon="🚚")
st.title("🚚 運輸日報表 Pro")

# 權限設定
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    # 從 Secrets 讀取金鑰
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    # 連接試算表
    sh = client.open("運輸成本紀錄")
    sheet = sh.get_worksheet(0)

    # 抓取資料並顯示
    data = sheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        st.success("✅ 資料連線成功！")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("目前試算表內沒有資料。")

except Exception as e:
    st.error(f"連線失敗，原因：{e}")
