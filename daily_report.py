import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
from datetime import datetime, timedelta

# --- 網頁與版面設定 ---
st.set_page_config(page_title="運輸日報表分析系統", page_icon="🚛", layout="wide")
st.title("🚛 運輸日報表分析")

# --- 連線設定 ---
def get_sheet():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds_dict = st.secrets["service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    sheet_url = "https://docs.google.com/spreadsheets/d/1VzyglFpEC3yS11aIoU1YJclw-6Moaewyf8DTR-j7HDc/edit?gid=0#gid=0"
    return client.open_by_url(sheet_url).sheet1

# --- 工具函數 ---
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
        start_mileage = c5.number_input("里程 (起)", min_value=0, step=1, value=None, placeholder="輸入起始里程")
        end_mileage = c6.number_input("里程 (迄)", min_value=0, step=1, value=None, placeholder="輸入結束里程")
        
        st.write("---")
        st.caption("作業數據 (無資料請留白)")
        c7, c8, c9, c10, c11, c12 = st.columns(6)
        delivery_stops = c7.number_input("配送點數", min_value=0, step=1, value=None)
        delivery_pallets = c8.number_input("配送板數", min_value=0, step=1, value=None)
        pickup_stops = c9.number_input("收貨點數", min_value=0, step=1, value=None)
        pickup_pallets = c10.number_input("收貨板數", min_value=0, step=1, value=None)
        empty_baskets = c11.number_input("空籃數", min_value=0, step=1, value=None)
        empty_pallets = c12.number_input("空板數", min_value=0, step=1, value=None)
        
        submitted = st.form_submit_button("🚀 儲存紀錄")
        
        if submitted:
            if start_mileage is None or end_mileage is None:
                st.error("⚠️ 請輸入完整的「起/迄」里程數！")
            else:
                p_del_pallets, p_pick_pallets = delivery_pallets or 0, pickup_pallets or 0
                p_del_stops, p_pick_stops = delivery_stops or 0, pickup_stops or 0
                p_baskets, p_empty_pallets = empty_baskets or 0, empty_pallets or 0

                total_pallets = p_del_pallets + p_pick_pallets
                mileage_diff = end_mileage - start_mileage
                
                row_data = [str(date), start_time, end_time, route, start_mileage, end_mileage, mileage_diff, p_del_stops, p_del_pallets, p_pick_stops, p_pick_pallets, total_pallets, p_baskets, p_empty_pallets]
                sheet.append_row(row_data)
                st.success(f"✅ 成功寫入！本趟 {route} 共 {total_pallets} 板，實際行駛里程：{mileage_diff} 公里。")
                time.sleep(1.5)
                st.rerun()

    # --- 區塊 2：戰情分析儀表板 ---
    st.write("---")
    st.subheader("📊 營運數據分析與指標")
    
    raw_data = sheet.get_all_values()
    
    if len(raw_data) > 1:
        headers = [str(h).strip() for h in raw_data[0]]
        df_all = pd.DataFrame(raw_data[1:], columns=headers)
        
        # 資料轉換與清理
        df_all['月份'] = df_all['運輸日期'].apply(lambda x: str(x)[:7])
        numeric_cols = ['行駛里程', '合計總板數', '空籃數', '空板數', '配送點數', '收貨點數']
        for col in numeric_cols:
            df_all[col] = pd.to_numeric(df_all[col], errors='coerce').fillna(0)
        df_all['工時'] = df_all.apply(lambda row: calculate_work_hours(row['上班時間'], row['下班時間']), axis=1)
        df_all['總點數'] = df_all['配送點數'] + df_all['收貨點數']

        current_month = datetime.today().strftime('%Y-%m')
        
        # --- 依月份分層顯示路線別指標 ---
        st.markdown("### 📋 路線別指標 (年度分月明細)")
        
        unique_months = sorted(df_all['月份'].unique(), reverse=True)
        
        for month in unique_months:
            is_expanded = (month == current_month)
            with st.expander(f"📅 {month} 營運分析報表", expanded=is_expanded):
                df_month = df_all[df_all['月份'] == month].copy()
                
                # 計算該月各項統計
                route_group = df_month.groupby('路線別').agg({
                    '運輸日期': 'count',
                    '合計總板數': ['sum', 'mean'],
                    '工時': 'mean',
                    '行駛里程': 'mean',
                    '總點數': 'mean'
                }).reset_index()
                
                # 重新定義欄位名稱與順序
                route_group.columns = ['路線別', '趟數', '總板數', '平均板數', '平均工時', '平均里程', '平均點數']
                
                # 計算派車指標
                route_group['工時稼動(%)'] = (route_group['平均工時'] / 24) * 100
                route_group['趟次滿載率(%)'] = (route_group['平均板數'] / 28) * 100
                
                # 效益值 (VRP 邏輯計算)
                def calc_vrp(row):
                    p, s, h, m = row['平均板數'], row['平均點數'] or 1, row['平均工時'] or 1, row['平均里程'] or 1
                    return round((p / 50) * (5 / s) * (10 / h) * (100 / m) * 100, 1)
                
                route_group['效益值(VRP)'] = route_group.apply(calc_vrp, axis=1)
                
                # 顯示表格並隱藏索引
                st.dataframe(route_group.style.format({
                    "平均工時": "{:.1f} H",
                    "平均里程": "{:.1f} KM",
                    "平均板數": "{:.1f} 板",
                    "總板數": "{:,.0f} 板",
                    "平均點數": "{:.1f} 點",
                    "工時稼動(%)": "{:.1f}%",
                    "趟次滿載率(%)": "{:.1f}%",
                    "效益值(VRP)": "{:.1f}"
                }), use_container_width=True, hide_index=True)

        # --- 視覺化圖表區 ---
        st.write("---")
        st.markdown("### 📈 年度分析圖表")
        c_left, c_right = st.columns(2)
        
        with c_left:
            st.caption("🏆 年度每月板數比對")
            month_stats = df_all.groupby('月份')['合計總板數'].sum()
            st.bar_chart(month_stats)
            
        with c_right:
            st.caption("🚚 當月路線滿載率 (%)")
            if not df_all[df_all['月份'] == current_month].empty:
                current_route_stats = df_all[df_all['月份'] == current_month].groupby('路線別')['合計總板數'].mean() / 28 * 100
                st.line_chart(current_route_stats)

    else:
        st.info("💡 試算表連結成功，目前尚無資料。")

except Exception as e:
    st.error(f"系統異常：{e}")
