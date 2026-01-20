import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# 針對手機螢幕優化：窄版布局
st.set_page_config(page_title="運輸管理系統", page_icon="🚚", layout="centered")

# 隱藏不必要的選單，最大化操作空間
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>""", unsafe_allow_html=True)

st.title("🚚 運輸日報表輸入")

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    # 連線 Google Sheets
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sh = client.open("Transport_System_2026")
    sheet = sh.get_worksheet(0)
    
    # 抓取資料庫內容
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    # --- 1. 新增紀錄區 (垂直排列，適合手機) ---
    st.subheader("📝 新增運輸紀錄")
    
    input_date = st.date_input("選擇日期", datetime.now())
    input_time = st.text_input("上班時間", value="05:00")
    
    # 里程數 (自動帶入上次迄點)
    last_m = int(df.iloc[-1]['里程迄']) if not df.empty else 0
    m_start = st.number_input("里程(起)", value=last_m)
    m_end = st.number_input("里程(迄)", value=last_m)
    
    # 貨物與空容器
    col1, col2 = st.columns(2)
    with col1:
        p_sent = st.number_input("總送板數", value=0, step=1)
        basket_back = st.number_input("空籃回收", value=0, step=1)
    with col2:
        p_recv = st.number_input("總收板數", value=0, step=1)
        plate_back = st.number_input("空板回收", value=0, step=1)
    
    # 詳細配送內容 (改成文字輸入，方便輸入客戶資訊)
    detail_content = st.text_area("詳細配送內容", placeholder="例如：客戶 1(送10/收0) | 客戶 2(送0/收5)...")
    input_remark = st.text_input("備註 (選填)")

    # 寬版送出按鈕
    if st.button("🚀 確認送出資料", use_container_width=True):
        actual_dist = m_end - m_start
        # 依照您的 Google 試算表欄位順序排列
        new_row = [
            str(input_date), input_time, "", m_start, m_end, 
            actual_dist, p_sent, p_recv, (p_sent + p_recv), 
            basket_back, plate_back, detail_content, input_remark
        ]
        sheet.append_row(new_row)
        st.success("存檔成功！資料已同步至 Excel")
        st.rerun()

    # --- 2. 報表預覽 ---
    st.divider()
    st.subheader("📋 最近 5 筆紀錄")
    if not df.empty:
        # 在手機上表格可以左右滑動
        st.dataframe(df.tail(5), use_container_width=True, hide_index=True)
    else:
        st.info("尚無資料")

except Exception as e:
    st.error(f"連線失敗：{e}")
