import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
from datetime import datetime, timedelta

# --- 網頁與版面設定 ---
st.set_page_config(page_title="專業運輸日報表", page_icon="🚛", layout="wide")
st.title("🚛 專業運輸分析系統")

# --- 連線設定 ---
def get_sheet():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds_dict = st.secrets["service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    # 這是您確認過的試算表網址
    sheet_url = "https://docs.google.com/spreadsheets/d/1VzyglFpEC3yS11aIoU1YJclw-6Moaewyf8DTR-j7HDc/edit?gid=0#gid=0"
    return client.open_by_url(sheet_url).sheet1

# --- 工時計算小工具 ---
def calculate_work_hours(start_str, end_str):
    try:
        start = datetime.strptime(start_str, "%H:%M")
        end = datetime.strptime(end_str, "%H:%M")
        # 處理跨日問題 (雖然運輸很少跨日，但防呆)
        if end < start:
            end += timedelta(days=1)
        diff = end - start
        return diff.total_seconds() / 3600
    except:
        return 0

# --- 產生時間選單的函數 ---
def generate_time_options(start_hour, end_hour, step_minutes):
    options = []
    current_time = datetime.strptime(f"{start_hour}:00", "%H:%M")
    end_time = datetime.strptime(f"{end_hour}:00", "%H:%M")
    while current_time <= end_time:
        options.append(current_time.strftime("%H:%M"))
        current_time += timedelta(minutes=step_minutes)
    return options

# --- 主程式 ---
try:
    sheet = get_sheet()
    
    # --- 區塊 1：資料輸入表單 ---
    with st.form("daily_report_form", clear_on_submit=True):
        st.subheader("📝 新增趟次紀錄 (平板快速輸入區)")
        
        # 第一排：時間與路線 (使用預設的標準化選項)
        c1, c2, c3, c4 = st.columns(4)
        date = c1.date_input("運輸日期", datetime.today())
        
        start_time_options = generate_time_options(4, 7, 30) # 04:00 到 07:30
        start_time = c2.selectbox("上班時間", start_time_options, index=1) # 預設選 04:30
        
        end_time_options = generate_time_options(13, 18, 30) # 13:00 到 18:30
        end_time = c3.selectbox("下班時間", end_time_options, index=6) # 預設選 16:00
        
        route_options = ["中一線", "中二線", "中三線", "中四線", "中五線", "中六線", "中七線"]
        route = c4.selectbox("路線別", route_options)
        
        # 第二排：里程
        c5, c6 = st.columns(2)
        start_mileage = c5.number_input("里程 (起)", min_value=0, step=1)
        end_mileage = c6.number_input("里程 (迄)", min_value=start_mileage, step=1)
        
        # 第三排：點數與板數 (精細拆分)
        st.write("---")
        st.caption("作業數據")
        c7, c8, c9, c10, c11, c12 = st.columns(6)
        delivery_stops = c7.number_input("配送點數", min_value=0, step=1)
        delivery_pallets = c8.number_input("配送板數", min_value=0, step=1)
        pickup_stops = c9.number_input("收貨點數", min_value=0, step=1)
        pickup_pallets = c10.number_input("收貨板數", min_value=0, step=1)
        empty_baskets = c11.number_input("空籃數", min_value=0, step=1)
        empty_pallets = c12.number_input("空板數", min_value=0, step=1)
        
        submitted = st.form_submit_button("🚀 儲存紀錄")
        
        if submitted:
            total_pallets = delivery_pallets + pickup_pallets
            mileage_diff = end_mileage - start_mileage
            
            # 對應 A 到 N 欄，共 14 個欄位
            row_data = [
                str(date), start_time, end_time, route, 
                start_mileage, end_mileage, mileage_diff,
                delivery_stops, delivery_pallets, pickup_stops, pickup_pallets, 
                total_pallets, empty_baskets, empty_pallets
            ]
            sheet.append_row(row_data)
            st.success(f"✅ 成功寫入！本趟 {route}，共 {total_pallets} 板，行駛 {mileage_diff} 公里。")
            time.sleep(1)
            st.rerun()

    # --- 區塊 2：戰情分析儀表板 ---
    st.write("---")
    st.subheader("📊 當月戰情分析與預警系統")
    
    data = sheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        
        # 檢查標題列是否正確
        if '運輸日期' in df.columns and '行駛里程' in df.columns:
            current_month = datetime.today().strftime('%Y-%m')
            df_month = df[df['運輸日期'].astype(str).str.startswith(current_month)].copy()
            
            if not df_month.empty:
                # 計算分析數據
                month_total_pallets = df_month['合計總板數'].sum()
                month_total_mileage = df_month['行駛里程'].sum()
                
                # 計算每趟工時並找出是否超時
                df_month['工時'] = df_month.apply(lambda row: calculate_work_hours(row['上班時間'], row['下班時間']), axis=1)
                avg_hours = df_month['工時'].mean()
                overtime_count = len(df_month[df_month['工時'] > 10])
                
                # --- KPI 數字看板 ---
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("當月累積總板數", f"{month_total_pallets} 板")
                k2.metric("當月總行駛里程", f"{month_total_mileage} KM")
                
                # 超時預警變色設定
                if avg_hours > 10:
                    k3.error(f"平均工時: {avg_hours:.1f} 小時 (超時!)")
                else:
                    k3.metric("平均單趟工時", f"{avg_hours:.1f} 小時")
                    
                if overtime_count > 0:
                    k4.error(f"超時(>10H)趟次: {overtime_count} 趟 ⚠️")
                else:
                    k4.metric("超時(>10H)趟次", "0 趟 ✅")

                # --- 原始資料明細 ---
                st.write("📋 當月明細資料：")
                st.dataframe(df_month[['運輸日期', '路線別', '上班時間', '下班時間', '工時', '合計總板數', '行駛里程']], use_container_width=True)
            else:
                st.info(f"目前 {current_month} 尚無資料，請輸入您的第一趟任務。")
        else:
            st.error("⚠️ 試算表欄位錯誤！請確保 A-N 欄位標題已正確設定為：運輸日期、上班時間、下班時間...等 14 個標題。")
    else:
        st.info("試算表目前是空的，快去儲存第一筆資料吧！")

except Exception as e:
    st.error("系統連線異常或資料庫格式錯誤。")
    st.write(f"系統除錯訊息：{e}")
