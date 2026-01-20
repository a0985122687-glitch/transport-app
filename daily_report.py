import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# 1. 網頁基本設定
st.set_page_config(page_title="運輸管理系統", page_icon="🚚", layout="wide")
st.title("🚚 運輸日報表輸入系統")

# 2. 設定連線權限
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    # 讀取 Secrets
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sh = client.open("Transport_System_2026")
    sheet = sh.get_worksheet(0)

    # --- 第一部分：資料輸入介面 ---
    with st.expander("➕ 新增今日運輸紀錄", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            date = st.date_input("日期", datetime.now())
            start_time = st.text_input("上班時間", "05:00")
        with col2:
            mileage_start = st.number_input("里程起", value=0)
            mileage_end = st.number_input("里程迄", value=0)
        with col3:
            plates_sent = st.number_input("總送板數", value=0)
            plates_received = st.number_input("總收板數", value=0)
        
        remark = st.text_area("備註 (選填)")

        if st.button("確認送出資料"):
            # 準備要寫入的一列資料 (順序需對應您的試算表欄位)
            new_row = [str(date), start_time, "", mileage_start, mileage_end, 
                       (mileage_end - mileage_start), plates_sent, plates_received, remark]
            sheet.append_row(new_row)
            st.success("🎉 資料已成功寫入 Google 試算表！")
            st.balloons()

    # --- 第二部分：即時報表檢視 ---
    st.divider()
    st.subheader("📊 即時運輸報表")
    data = sheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("目前尚無資料紀錄。")

except Exception as e:
    st.error(f"連線或操作失敗：{e}")
