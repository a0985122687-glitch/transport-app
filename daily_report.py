import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
from datetime import datetime, timedelta

# --- 網頁與版面設定 ---
st.set_page_config(page_title="運輸日報表分析", page_icon="🚛", layout="wide")
st.title("🚛 運輸日報表分析")

# --- 連線設定 ---
def get_sheet():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds_dict = st.secrets["service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    sheet_url = "https://docs.google.com/spreadsheets/d/1VzyglFpEC3yS11aIoU1YJclw-6Moaewyf8DTR-j7HDc/edit?gid=0#gid=0"
    return client.open_by_url(sheet_url).sheet1

# --- 工時計算小工具 ---
def calculate_work_hours(start_str, end_str):
    try:
        start = datetime.strptime(str(start_str), "%H:%M")
        end = datetime.strptime(str(end_str), "%H:%M")
        if end < start:
            end += timedelta(days=1)
        return (end - start).total_seconds() / 3600
    except:
        return 0

# --- 主程式 ---
try:
    sheet = get_sheet()
    
    # --- 區塊 1：資料輸入表單 ---
    with st.form("daily_report_form", clear_on_submit=True):
        st.subheader("📝 趟次紀錄")
        
        c1, c2, c3, c4 = st.columns(4)
        date = c1.date_input("運輸日期", datetime.today())
        
        start_times = ["04:30", "05:00", "05:30", "06:00", "06:30", "07:00", "07:30"]
        end_times = ["13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30", "18:00", "18:30"]
        routes = ["中一線", "中二線", "中三線", "中四線", "中五線", "中六線", "中七線"]
        
        start_time = c2.selectbox("上班時間", start_times)
        end_time = c3.selectbox("下班時間", end_times, index=6) 
        route = c4.selectbox("路線別", routes)
        
        c5, c6 = st.columns(2)
        # 加入 value=None，讓格子預設為空白，不用再刪除 0
        start_mileage = c5.number_input("里程 (起)", min_value=0, step=1, value=None, placeholder="輸入起始里程")
        end_mileage = c6.number_input("里程 (迄)", min_value=0, step=1, value=None, placeholder="輸入結束里程")
        
        st.write("---")
        st.caption("作業數據 (無資料請留白)")
        c7, c8, c9, c10, c11, c12 = st.columns(6)
        # 全部設為 value=None，提升平板輸入流暢度
        delivery_stops = c7.number_input("配送點數", min_value=0, step=1, value=None)
        delivery_pallets = c8.number_input("配送板數", min_value=0, step=1, value=None)
        pickup_stops = c9.number_input("收貨點數", min_value=0, step=1, value=None)
        pickup_pallets = c10.number_input("收貨板數", min_value=0, step=1, value=None)
        empty_baskets = c11.number_input("空籃數", min_value=0, step=1, value=None)
        empty_pallets = c12.number_input("空板數", min_value=0, step=1, value=None)
        
        submitted = st.form_submit_button("🚀 儲存紀錄")
        
        if submitted:
            # 防呆：檢查是否忘記填寫里程
            if start_mileage is None or end_mileage is None:
                st.error("⚠️ 請輸入完整的「起/迄」里程數！")
            else:
                # 若留白(None)，則自動視為 0 計算，不影響公式
                p_del_pallets = delivery_pallets or 0
                p_pick_pallets = pickup_pallets or 0
                p_del_stops = delivery_stops or 0
                p_pick_stops = pickup_stops or 0
                p_baskets = empty_baskets or 0
                p_empty_pallets = empty_pallets or 0

                total_pallets = p_del_pallets + p_pick_pallets
                mileage_diff = end_mileage - start_mileage
                
                row_data = [
                    str(date), start_time, end_time, route, 
                    start_mileage, end_mileage, mileage_diff,
                    p_del_stops, p_del_pallets, p_pick_stops, p_pick_pallets, 
                    total_pallets, p_baskets, p_empty_pallets
                ]
                sheet.append_row(row_data)
                st.success(f"✅ 成功寫入！本趟 {route} 共 {total_pallets} 板，行駛里程：{mileage_diff} 公里。")
                time.sleep(1.5)
                st.rerun()

    # --- 區塊 2：戰情分析儀表板 ---
    st.write("---")
    st.subheader("📊 當月戰情分析與預警系統")
    
    raw_data = sheet.get_all_values()
    
    if len(raw_data) > 1:
        headers = [str(h).strip() for h in raw_data[0]]
        df = pd.DataFrame(raw_data[1:], columns=headers)
        
        if '運輸日期' in df.columns and '行駛里程' in df.columns:
            current_month = datetime.today().strftime('%Y-%m')
            df_month = df[df['運輸日期'].astype(str).str.startswith(current_month)].copy()
            
            if not df_month.empty:
                numeric_cols = ['行駛里程', '合計總板數', '配送點數', '收貨點數']
                for col in numeric_cols:
                    if col in df_month.columns:
                        df_month[col] = pd.to_numeric(df_month[col], errors='coerce').fillna(0)
                        
                month_total_pallets = int(df_month['合計總板數'].sum())
                month_total_mileage = int(df_month['行駛里程'].sum())
                
                df_month['工時'] = df_month.apply(lambda row: calculate_work_hours(row['上班時間'], row['下班時間']), axis=1)
                avg_hours = df_month['工時'].mean()
                overtime_count = len(df_month[df_month['工時'] > 10])
                
                # --- KPI 看板 ---
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("當月累積總板數", f"{month_total_pallets} 板")
                k2.metric("當月總行駛里程", f"{month_total_mileage} KM")
                
                if avg_hours > 10:
                    k3.error(f"平均工時: {avg_hours:.1f} 小時 (超時!)")
                else:
                    k3.metric("平均單趟工時", f"{avg_hours:.1f} 小時")
                    
                if overtime_count > 0:
                    k4.error(f"超時(>10H)趟次: {overtime_count} 趟 ⚠️")
                else:
                    k4.metric("超時(>10H)趟次", "0 趟 ✅")

                # ==========================================
                # 🔥 新增：視覺化里程分析區塊
                # ==========================================
                st.write("---")
                st.markdown("### 🗺️ 路線里程與年度趨勢準備區")
                
                chart_col1, chart_col2 = st.columns(2)
                
                with chart_col1:
                    st.caption("📅 每日各路線里程趨勢 (KM)")
                    # 將資料整理成：日期為 X 軸，路線為線條，里程為 Y 軸
                    daily_route_mileage = df_month.pivot_table(index='運輸日期', columns='路線別', values='行駛里程', aggfunc='sum').fillna(0)
                    st.line_chart(daily_route_mileage)

                with chart_col2:
                    st.caption("📊 各路線平均行駛里程 (KM)")
                    # 計算每條路線的「平均」里程
                    route_avg_mileage = df_month.groupby('路線別')['行駛里程'].mean().round(1)
                    st.bar_chart(route_avg_mileage)

                # ==========================================
                # 路線綜合指標矩陣
                # ==========================================
                st.write("---")
                st.markdown("### 📋 路線綜合指標矩陣")
                
                df_month['總點數'] = df_month['配送點數'] + df_month['收貨點數']
                route_group = df_month.groupby('路線別').agg({
                    '運輸日期': 'count',
                    '工時': 'mean',
                    '行駛里程': 'mean',
                    '合計總板數': 'mean',
                    '總點數': 'mean'
                }).reset_index()
                
                route_group.rename(columns={'運輸日期': '趟數', '工時': '平均工時', '行駛里程': '平均里程', '合計總板數': '平均板數', '總點數': '平均點數'}, inplace=True)
                
                route_group['工時稼動(%)'] = (route_group['平均工時'] / 24) * 100
                route_group['趟次滿載率(%)'] = (route_group['平均板數'] / 28) * 100
                
                def calc_vrp(row):
                    p = row['平均板數']
                    s = row['平均點數'] if row['平均點數'] > 0 else 1
                    h = row['平均工時'] if row['平均工時'] > 0 else 1
                    m = row['平均里程'] if row['平均里程'] > 0 else 1
                    score = (p / 50) * (5 / s) * (10 / h) * (100 / m) * 100
                    return round(score, 1)
                    
                route_group['效益值(VRP)'] = route_group.apply(calc_vrp, axis=1)

                st.dataframe(route_group.style.format({
                    "平均工時": "{:.1f} H",
                    "平均里程": "{:.1f} KM",
                    "平均板數": "{:.1f} 板",
                    "平均點數": "{:.1f} 點",
                    "工時稼動(%)": "{:.1f}%",
                    "趟次滿載率(%)": "{:.1f}%",
                    "效益值(VRP)": "{:.1f} 分"
                }), use_container_width=True)
                
            else:
                st.info(f"目前 {current_month} 尚無資料，請輸入您的第一趟任務。")
        else:
            st.error(f"⚠️ 標題對應失敗！目前抓到的標題是：{headers}")
            
    elif len(raw_data) == 1:
        st.info("💡 試算表已經完美連結！目前資料庫是空的，趕快按下上方按鈕，儲存您的第一筆紀錄吧！")
    else:
        st.error("⚠️ 試算表完全空白，請確認第一列是否已貼上標題。")

except Exception as e:
    st.error("系統連線異常或資料庫格式錯誤。")
    st.write(f"系統除錯訊息：{e}")
