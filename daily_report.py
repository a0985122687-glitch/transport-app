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
    # 這是您指定的 14 欄格式試算表網址
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
    
    # --- 區塊 1：資料輸入表單 (三階段物理作業流程) ---
    with st.form("daily_report_form", clear_on_submit=True):
        st.subheader("📝 趟次紀錄")
        
        # ▶️ 第一層：出車準備
        st.markdown("##### ▶️ 第一階段：出車準備")
        c1, c2, c3, c4 = st.columns(4)
        date = c1.date_input("運輸日期", datetime.today())
        start_times = ["04:30", "05:00", "05:30", "06:00", "06:30", "07:00", "07:30"]
        start_time = c2.selectbox("上班時間", start_times)
        routes = ["中一線", "中二線", "中三線", "中四線", "中五線", "中六線", "中七線"]
        route = c3.selectbox("路線別", routes)
        start_mileage = c4.number_input("里程 (起)", min_value=0, step=1, value=None, placeholder="出站里程")
        
        st.write("") 
        
        # 🔄 第二層：站點作業 (點數、板數拆分)
        st.markdown("##### 🔄 第二階段：站點作業 (無資料請留白)")
        c5, c6, c7, c8, c9, c10 = st.columns(6)
        p_del_stops = c5.number_input("配送點數", min_value=0, step=1, value=None)
        p_del_pallets = c6.number_input("配送板數", min_value=0, step=1, value=None)
        p_pick_stops = c7.number_input("收貨點數", min_value=0, step=1, value=None)
        p_pick_pallets = c8.number_input("收貨板數", min_value=0, step=1, value=None)
        p_baskets = c9.number_input("空籃數", min_value=0, step=1, value=None)
        p_empty_pallets = c10.number_input("空板數", min_value=0, step=1, value=None)

        st.write("")
        
        # ⏹️ 第三層：收工打卡
        st.markdown("##### ⏹️ 第三階段：收工打卡")
        c11, c12, c13 = st.columns([1, 1, 2])
        end_times = ["13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30", "18:00", "18:30"]
        end_time = c11.selectbox("下班時間", end_times, index=6) 
        end_mileage = c12.number_input("里程 (迄)", min_value=0, step=1, value=None, placeholder="回站里程")
        
        submitted = st.form_submit_button("🚀 儲存紀錄")
        
        if submitted:
            if start_mileage is None or end_mileage is None:
                st.error("⚠️ 請輸入完整的「起/迄」里程數！")
            else:
                d_stops = p_del_stops or 0
                d_pallets = p_del_pallets or 0
                r_stops = p_pick_stops or 0
                r_pallets = p_pick_pallets or 0
                baskets = p_baskets or 0
                empty_p = p_empty_pallets or 0

                total_pallets = d_pallets + r_pallets
                mileage_diff = end_mileage - start_mileage
                
                # 寫入 14 欄位資料 (A 到 N)
                row_data = [
                    str(date), start_time, end_time, route, 
                    start_mileage, end_mileage, mileage_diff, 
                    d_stops, d_pallets, r_stops, r_pallets, 
                    total_pallets, baskets, empty_p
                ]
                sheet.append_row(row_data)
                st.success(f"✅ 成功寫入！本趟 {route} 共 {total_pallets} 板，實際里程：{mileage_diff} 公里。")
                time.sleep(1.5)
                st.rerun()

    # --- 區塊 2：戰情分析儀表板 ---
    st.write("---")
    st.subheader("📊 營運數據分析與指標")
    
    raw_data = sheet.get_all_values()
    
    if len(raw_data) > 1:
        headers = [str(h).strip() for h in raw_data[0]]
        df_all = pd.DataFrame(raw_data[1:], columns=headers)
        
        df_all['月份'] = df_all['運輸日期'].apply(lambda x: str(x)[:7])
        numeric_cols = ['行駛里程', '合計總板數', '空籃數', '空板數', '配送點數', '配送板數', '收貨點數', '收貨板數']
        for col in numeric_cols:
            if col in df_all.columns:
                df_all[col] = pd.to_numeric(df_all[col], errors='coerce').fillna(0)
            
        df_all['工時'] = df_all.apply(lambda row: calculate_work_hours(row['上班時間'], row['下班時間']), axis=1)

        current_month = datetime.today().strftime('%Y-%m')
        
        # --- 當月產能與獎金 ---
        if not df_all[df_all['月份'] == current_month].empty:
            df_m = df_all[df_all['月份'] == current_month].copy()
            month_total_p = df_m['合計總板數'].sum()
            base_bonus = (month_total_p * 40) + (df_m['空籃數'].sum() * 0.5) + (df_m['空板數'].sum() * 3)
            multiplier = 1.2 if month_total_p >= 501 else (1.1 if month_total_p >= 451 else 1.0)
            
            st.markdown("#### 💰 當月產能與獎金摘要")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("當月總板數", f"{int(month_total_p)} 板")
            k2.metric("預估基礎獎金", f"${int(base_bonus):,}")
            k3.metric("目前階梯倍率", f"{multiplier} 倍")
            k4.metric("💰 預估總獎金", f"${int(base_bonus * multiplier):,}")

        # --- 路線別指標 (含收送佔比) ---
        st.write("---")
        st.markdown("### 📋 路線別指標 (年度分月明細)")
        
        unique_months = sorted(df_all['月份'].unique(), reverse=True)
        for month in unique_months:
            is_expanded = (month == current_month)
            with st.expander(f"📅 {month} 營運分析報表", expanded=is_expanded):
                df_m = df_all[df_all['月份'] == month].copy()
                
                route_group = df_m.groupby('路線別').agg({
                    '運輸日期': 'count',
                    '合計總板數': ['sum', 'mean'],
                    '配送板數': 'sum',
                    '收貨板數': 'sum',
                    '配送點數': 'sum',
                    '收貨點數': 'sum',
                    '工時': 'mean',
                    '行駛里程': 'mean'
                }).reset_index()
                
                route_group.columns = ['路線別', '趟數', '總板數', '平均板數', '總配板', '總收板', '總配點', '總收點', '平均工時', '平均里程']
                
                # 計算佔比分析
                def calc_ratios(row):
                    p_total = row['總配板'] + row['總收板']
                    s_total = row['總配點'] + row['總收點']
                    p_ratio = f"{int(row['總配板']/p_total*100)}% / {100-int(row['總配板']/p_total*100)}%" if p_total > 0 else "0% / 0%"
                    s_ratio = f"{int(row['總配點']/s_total*100)}% / {100-int(row['總配點']/s_total*100)}%" if s_total > 0 else "0% / 0%"
                    return p_ratio, s_ratio
                
                ratios = route_group.apply(calc_ratios, axis=1)
                route_group['板數收送比'] = [r[0] for r in ratios]
                route_group['點數收送比'] = [r[1] for r in ratios]
                route_group['滿載率(%)'] = (route_group['平均板數'] / 28) * 100
                
                # 重新排列顯示欄位
                display_cols = ['路線別', '趟數', '總板數', '板數收送比', '點數收送比', '平均板數', '平均工時', '平均里程', '滿載率(%)']
                
                st.dataframe(route_group[display_cols].style.format({
                    "平均工時": "{:.1f} H",
                    "平均里程": "{:.1f} KM",
                    "平均板數": "{:.1f} 板",
                    "總板數": "{:,.0f} 板",
                    "滿載率(%)": "{:.1f}%"
                }), use_container_width=True, hide_index=True)

        # --- 視覺化圖表 ---
        st.write("---")
        st.markdown("### 📈 年度分析圖表")
        c_left, c_right = st.columns(2)
        with c_left:
            st.caption("🏆 年度每月板數比對")
            st.bar_chart(df_all.groupby('月份')['合計總板數'].sum())
        with c_right:
            st.caption("🚚 當月各路線平均里程 (KM)")
            if not df_all[df_all['月份'] == current_month].empty:
                st.bar_chart(df_all[df_all['月份'] == current_month].groupby('路線別')['行駛里程'].mean())

    else:
        st.info("💡 試算表已連結。目前資料庫為空，請輸入第一筆趟次紀錄。")

except Exception as e:
    st.error(f"系統異常：{e}")
