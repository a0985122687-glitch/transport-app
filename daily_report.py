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
    driver_list = ["請選擇司機", "司機A", "司機B", "車號001"]
    selected_driver = st.selectbox("👤 選擇填報人", driver_list)

    if selected_driver != "請選擇司機":
        st.divider()
        
        # --- 基本時間資訊 ---
        input_date = st.date_input("日期", datetime.now())
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            start_time = st.text_input("上班時間", value="05:00")
        with col_t2:
            end_time = st.text_input("下班時間", value="17:00")
        
        # --- 路線選擇 ---
        route_options = ["請選擇路線", "中一線", "中二線", "中三線", "中四線", "中五線", "中六線", "中七線", "其他"]
        route_name = st.selectbox("路線別", route_options)
        
        # --- 里程自動連動 ---
        driver_df = df[df['司機'] == selected_driver] if not df.empty and '司機' in df.columns else pd.DataFrame()
        last_m = int(driver_df.iloc[-1]['里程迄']) if not driver_df.empty else 0
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            m_start = st.number_input("里程(起)", value=last_m)
        with col_m2:
            m_end = st.number_input("里程(迄)", value=last_m)
        
        # --- 板數與空籃回收 ---
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            p_sent = st.number_input("總送板數", value=0, step=1)
            basket_back = st.number_input("空籃回收", value=0, step=1)
        with col_p2:
            p_recv = st.number_input("總收板數", value=0, step=1)
            plate_back = st.number_input("空板回收", value=0, step=1)
        
        detail_content = st.text_area("詳細配送內容 (僅存入 Excel)")
        input_remark = st.text_input("備註 (選填)")

        # 🚀 確認送出按鈕
        if st.button("🚀 確認送出資料", use_container_width=True):
            if route_name == "請選擇路線":
                st.error("請先選擇路線別！")
            else:
                actual_dist = m_end - m_start
                total_plates = p_sent + p_recv
                
                # 嚴格對齊您的 A~O 欄位順序 (加入下班時間後順延)
                new_row = [
                    selected_driver,    # A 司機
                    str(input_date),    # B 日期
                    start_time,         # C 上班時間
                    end_time,           # D 下班時間
                    route_name,         # E 路線別
                    m_start,            # F 里程起
                    m_end,              # G 里程迄
                    actual_dist,        # H 實際里程
                    p_sent,             # I 總送板數
                    p_recv,             # J 總收板數
                    total_plates,       # K 合計收送板數
                    basket_back,        # L 空籃回收
                    plate_back,         # M 空板回收
                    detail_content,     # N 詳細配送內容
                    input_remark        # O 備註
                ]
                sheet.append_row(new_row)
                st.success(f"存檔成功！今日共行駛 {actual_dist} 公里")
                st.balloons()
                st.rerun()

    # 3. 報表預覽
    st.divider()
    st.subheader("📋 最近紀錄預覽")
    if not df.empty:
        # 這裡也把下班時間放進預覽，方便確認工時
        display_cols = ['司機', '日期', '上班時間', '下班時間', '路線別', '實際里程']
        if all(c in df.columns for c in display_cols):
            st.dataframe(df[display_cols].tail(5), use_container_width=True, hide_index=True)
        else:
            st.dataframe(df.tail(5), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"系統錯誤：{e}")
