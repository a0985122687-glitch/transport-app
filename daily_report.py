import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# 手機版佈局優化
st.set_page_config(page_title="運輸管理系統", page_icon="🚚", layout="centered")

# 隱藏預設選單
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>""", unsafe_allow_html=True)

st.title("🚚 運輸日報表輸入")

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    # 1. 連線 Google Sheets
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sh = client.open("Transport_System_2026")
    sheet = sh.get_worksheet(0)
    
    # 讀取現有資料
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    # 2. 司機選擇
    driver_list = ["請選擇", "司機A", "司機B", "車號001"]
    selected_driver = st.selectbox("👤 選擇填報人", driver_list)

    if selected_driver != "請選擇":
        st.subheader(f"📝 {selected_driver} 的新紀錄")
        
        input_date = st.date_input("日期", datetime.now())
        input_time = st.text_input("上班時間", value="05:00")
        
        # --- 找回路線別輸入 ---
        route_name = st.text_input("路線別", placeholder="例如：北區 A 線、台中專車...")
        
        # 里程自動連動
        driver_df = df[df['司機'] == selected_driver] if not df.empty and '司機' in df.columns else pd.DataFrame()
        last_m = int(driver_df.iloc[-1]['里程迄']) if not driver_df.empty else 0
        
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
        
        detail_content = st.text_area("詳細配送內容 (僅存入 Excel)")
        input_remark = st.text_input("備註 (選填)")

        # 3. 確認送出按鈕
        if st.button("🚀 確認送出資料", use_container_width=True):
            actual_dist = m_end - m_start
            # 確保寫入順序與 Excel 欄位對齊：司機, 日期, 上班時間, 路線別, 里程起...
            new_row = [
                selected_driver, str(input_date), input_time, route_name, 
                m_start, m_end, actual_dist, p_sent, p_recv, 
                (p_sent + p_recv), basket_back, plate_back, detail_content, input_remark
            ]
            sheet.append_row(new_row)
            st.success(f"存檔成功！已記錄路線：{route_name}")
            st.rerun()

    # 4. 報表預覽 (顯示路線別，隱藏長文字)
    st.divider()
    st.subheader("📋 最近 5 筆紀錄")
    if not df.empty:
        # 這次把 '路線別' 加回顯示清單中
        display_columns = ['司機', '日期', '路線別', '里程起', '里程迄', '實際里程', '總送板數', '總收板數']
        
        if all(c in df.columns for c in display_columns):
            st.dataframe(df[display_columns].tail(5), use_container_width=True, hide_index=True)
        else:
            # 如果欄位名稱還沒完全對齊，先顯示全表
            st.dataframe(df.tail(5), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"系統錯誤：{e}")
