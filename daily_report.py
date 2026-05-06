import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
from datetime import datetime

# --- 網頁設定 ---
st.set_page_config(page_title="運輸日報表", page_icon="📝", layout="wide")
st.title("📝 運輸日報表")

# --- 連線設定 ---
def get_sheet():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds_dict = st.secrets["service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    sheet_url = "https://docs.google.com/spreadsheets/d/1VzyglFpEC3yS11aIoU1YJclw-6Moaewyf8DTR-j7HDc/edit?gid=0#gid=0"
    return client.open_by_url(sheet_url).sheet1

# --- 獎金計算模組 ---
def calculate_bonus(base_amount, total_month_pallets):
    if total_month_pallets >= 501:
        multiplier = 1.2
    elif total_month_pallets >= 451:
        multiplier = 1.1
    else:
        multiplier = 1.0
    return int(base_amount * (multiplier - 1) + 0.5)

# --- 主程式 ---
try:
    sheet = get_sheet()
    
    # --- 區塊 1：資料輸入表單 ---
    with st.form("daily_report_form", clear_on_submit=True):
        st.subheader("🚛 新增趟次紀錄")
        
        # 第一排：時間與路線 (改為下拉選單)
        c1, c2, c3, c4 = st.columns(4)
        date = c1.date_input("運輸日期", datetime.today())
        
        time_options = ["04:30", "05:00", "05:30", "06:00", "06:30", "07:00", "07:30"]
        start_time = c2.selectbox("上班時間", time_options)
        end_time = c3.selectbox("下班時間", time_options)
        
        route_options = ["中一線", "中二線", "中三線", "中四線", "中五線", "中六線", "中七線"]
        route = c4.selectbox("路線別", route_options)
        
        # 第二排：里程
        c5, c6 = st.columns(2)
        start_mileage = c5.number_input("里程 (起)", min_value=0, step=1)
        end_mileage = c6.number_input("里程 (迄)", min_value=start_mileage, step=1)
        
        # 第三排：點數、板數與籃數 (拆分為 6 格，更細緻)
        c7, c8, c9, c10, c11, c12 = st.columns(6)
        delivery_stops = c7.number_input("配送點數", min_value=0, step=1)
        delivery_pallets = c8.number_input("配送板數", min_value=0, step=1)
        pickup_stops = c9.number_input("收貨點數", min_value=0, step=1)
        pickup_pallets = c10.number_input("收貨板數", min_value=0, step=1)
        empty_baskets = c11.number_input("空籃數", min_value=0, step=1)
        empty_pallets = c12.number_input("空板數", min_value=0, step=1)
        
        submitted = st.form_submit_button("🚀 儲存紀錄")
        
        if submitted:
            # 計算基本數據 (注意：獎金基數通常只算「板數」，所以這裡用板數相加)
            total_pallets = delivery_pallets + pickup_pallets
            mileage_diff = end_mileage - start_mileage
            
            # 計算本趟基礎金額：合計板數40、空籃/2、空板3
            daily_base = (total_pallets * 40) + (empty_baskets / 2) + (empty_pallets * 3)
            
            # 寫入 Google Sheet (順序與您試算表的 15 個標題對齊)
            row_data = [
                str(date), start_time, end_time, route, 
                start_mileage, end_mileage, mileage_diff,
                delivery_stops, delivery_pallets, pickup_stops, pickup_pallets, 
                total_pallets, empty_baskets, empty_pallets, daily_base
            ]
            sheet.append_row(row_data)
            st.success(f"✅ 紀錄成功！總板數：{total_pallets} 板，基礎金額：${daily_base}")
            time.sleep(1)
            st.rerun()

    # --- 區塊 2：營運摘要與獎金預估 ---
    st.write("---")
    st.subheader("📊 當月營運摘要與獎金計算")
    
    data = sheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        
        # 防呆機制：檢查是否有標題列
        if '運輸日期' in df.columns:
            current_month = datetime.today().strftime('%Y-%m')
            # 將運輸日期轉為字串以防格式錯誤
            df_month = df[df['運輸日期'].astype(str).str.startswith(current_month)]
            
            if not df_month.empty:
                month_total_pallets = df_month['合計總板數'].sum() if '合計總板數' in df_month.columns else 0
                month_base_money = df_month['基礎金額'].sum() if '基礎金額' in df_month.columns else 0
                
                extra_bonus = calculate_bonus(month_base_money, month_total_pallets)
                
                m1, m2, m3 = st.columns(3)
                m1.metric("當月累積總板數", f"{month_total_pallets} 板")
                m2.metric("當月累積基礎額", f"${int(month_base_money)}")
                m3.metric("預估階梯達標獎金", f"${extra_bonus}")
                
                st.write("📋 歷史明細資料：")
                st.dataframe(df_month, use_container_width=True)
            else:
                st.info("當月尚無紀錄。")
        else:
            st.error("⚠️ 試算表缺少標題列！請確認 Google 試算表第一列是否包含「運輸日期」、「合計總板數」等標題。")
    else:
        st.info("試算表目前是空的，快輸入第一筆資料吧！")

except Exception as e:
    st.error("系統發生錯誤，請檢查連線或試算表欄位設定。")
    st.write(f"錯誤詳細資訊：{e}")
