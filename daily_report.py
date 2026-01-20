import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# 手機版佈局優化
st.set_page_config(page_title="運輸管理系統", page_icon="🚚", layout="centered")

# 隱藏預設選單與頁尾
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
        st.divider()
        
        # --- A 欄 & B 欄 & C 欄 & D 欄 ---
        input_date = st.date_input("日期", datetime.now())
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            input_time = st.text_input("上班時間", value="05:00")
        with col_t2:
            route_name = st.text_input("路線別", placeholder="如：北區A線")
        
        # --- E 欄 & F 欄 (里程) ---
        # 自動抓取該司機上次的里程迄點
        driver_df = df[df['司機'] == selected_driver] if not df.empty and '司機' in df.columns else pd.DataFrame()
        last_m = int(driver_df.iloc[-1]['里程迄']) if not driver_df.empty else 0
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            m_start = st.number_input("里程(起)", value=last_m)
        with col_m2:
            m_end = st.number_input("里程(迄)", value=last_m)
        
        # --- H 欄 ~ L 欄 (板數與空籃) ---
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            p_sent = st.number_input("總送板數", value=0, step=1)
            basket_back = st.number_input("空籃回收", value=0, step=1)
        with col_p2:
            p_recv = st.number_input("總收板數", value=0, step=1)
            plate_back = st.number_input("空板回收", value=0, step=1)
        
        # --- M 欄 & N 欄 (詳細內容與備註) ---
        detail_content = st.text_area("詳細配送內容 (僅存入 Excel)")
        input_remark = st.text_input("備註 (選填)")

        # 🚀 確認送出按鈕
        if st.button("🚀 確認送出資料", use_container_width=True):
            actual_dist = m_end - m_start
            total_plates = p_sent + p_recv
            
            # 【關鍵】嚴格對齊您的 A~N 欄位順序
            new_row = [
                selected_driver,    # A 司機
                str(input_date),    # B 日期
                input_time,         # C 上班時間
                route_name,         # D 路線別
                m_start,            # E 里程起
                m_end,              # F 里程迄
                actual_dist,        # G 實際里程
                p_sent,             # H 總送板數
                p_recv,             # I 總收板數
                total_plates,       # J 合計收送板數
                basket_back,        # K 空籃回收
                plate_back,         # L 空板回收
                detail_content,     # M 詳細配送內容
                input_remark        # N 備註
            ]
            sheet.append_row(new_row)
            st.success(f"存檔成功！已同步至 Excel 第 {len(df)+2} 列")
            st.balloons()
            st.rerun()

    # 3. 報表預覽 (保持精簡)
    st.divider()
    st.subheader("📋 最近紀錄預覽")
    if not df.empty:
        # 只顯示最關鍵的幾欄，避免手機畫面密密麻麻
        display_cols = ['司機', '日期', '路線別', '實際里程', '合計收送板數']
        if all(c in df.columns for c in display_cols):
            st.dataframe(df[display_cols].tail(5), use_container_width=True, hide_index=True)
        else:
            st.dataframe(df.tail(5), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"連線失敗或欄位不符：{e}")
