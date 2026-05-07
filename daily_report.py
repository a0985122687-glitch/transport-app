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
        start = datetime.strptime(str(start_str).strip(), "%H:%M")
        end = datetime.strptime(str(end_str).strip(), "%H:%M")
        if end < start:
            end += timedelta(days=1)
        return (end - start).total_seconds() / 3600
    except:
        return 0

# ==========================================
# 🟢 第一階段：輸入區塊 (保持完美現狀)
# ==========================================
try:
    sheet = get_sheet()
    
    with st.form("daily_report_form", clear_on_submit=True):
        st.subheader("📝 趟次紀錄")
        
        st.markdown("##### ▶️ 出車整備作業")
        c1, c2, c3, c4 = st.columns(4)
        date = c1.date_input("運輸日期", datetime.today())
        start_times = ["04:30", "05:00", "05:30", "06:00", "06:30", "07:00", "07:30"]
        start_time = c2.selectbox("上班時間", start_times)
        routes = ["中一線", "中二線", "中三線", "中四線", "中五線", "中六線", "中七線"]
        route = c3.selectbox("路線別", routes)
        start_mileage = c4.number_input("里程 (起)", min_value=0, step=1, value=None, placeholder="出站里程")
        
        st.write("") 
        
        st.markdown("##### 🔄 途程與站點執行 (無資料請留白)")
        c5, c6, c7, c8, c9 = st.columns(5)
        total_stops = c5.number_input("總點數", min_value=0, step=1, value=None)
        p_del_pallets = c6.number_input("配送板數", min_value=0, step=1, value=None)
        p_pick_pallets = c7.number_input("收貨板數", min_value=0, step=1, value=None)
        p_baskets = c8.number_input("空籃數", min_value=0, step=1, value=None)
        p_empty_pallets = c9.number_input("空板數", min_value=0, step=1, value=None)

        st.write("")
        
        st.markdown("##### ⏹️ 返站結報作業")
        c10, c11, c12 = st.columns([1, 1, 2])
        end_times = ["13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30", "18:00", "18:30"]
        end_time = c10.selectbox("下班時間", end_times, index=6) 
        end_mileage = c11.number_input("里程 (迄)", min_value=0, step=1, value=None, placeholder="回站里程")
        
        submitted = st.form_submit_button("🚀 儲存紀錄")
        
        if submitted:
            if start_mileage is None or end_mileage is None:
                st.error("⚠️ 請輸入完整的「起/迄」里程數！")
            else:
                t_stops = total_stops or 0
                d_pallets = p_del_pallets or 0
                r_pallets = p_pick_pallets or 0
                baskets = p_baskets or 0
                empty_p = p_empty_pallets or 0
                
                total_p = d_pallets + r_pallets
                mileage_diff = end_mileage - start_mileage
                
                row_data = [str(date), start_time, end_time, route, start_mileage, end_mileage, mileage_diff, t_stops, d_pallets, r_pallets, total_p, baskets, empty_p]
                sheet.append_row(row_data)
                st.success(f"✅ 成功寫入！本趟 {route} 共 {total_p} 板。")
                time.sleep(1.5)
                st.rerun()

    # ==========================================
    # 資料清洗與防呆轉換 (背景處理)
    # ==========================================
    st.write("---")
    st.subheader("📊 營運數據分析與指標")
    
    all_raw = sheet.get_all_values()
    actual_data = [row for row in all_raw if any(str(cell).strip() for cell in row)]
    
    if len(actual_data) > 1:
        headers = [str(h).strip() for h in actual_data[0]]
        df_all = pd.DataFrame(actual_data[1:], columns=headers)
        
        if '合計總板數' in df_all.columns:
            df_all['月份'] = df_all['運輸日期'].apply(lambda x: str(x)[:7])
            
            # 【關鍵修復】強制把所有計算欄位轉換為純數字，避免 'int' and 'str' 錯誤
            num_cols = ['行駛里程', '合計總板數', '空籃數', '空板數', '總點數', '配送板數', '收貨板數']
            for col in num_cols:
                if col in df_all.columns:
                    df_all[col] = pd.to_numeric(df_all[col].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
            
            df_all['工時'] = df_all.apply(lambda row: calculate_work_hours(row['上班時間'], row['下班時間']), axis=1)
            current_month = datetime.today().strftime('%Y-%m')

            # ==========================================
            # 🟡 第二階段：營運圖表區 (精緻版雙圖表)
            # ==========================================
            c_chart1, c_chart2 = st.columns(2)
            
            with c_chart1:
                st.caption("🏆 年度每月總板數趨勢")
                month_stats = df_all.groupby('月份')['合計總板數'].sum()
                st.bar_chart(month_stats)
            
            with c_chart2:
                st.caption("🎯 當月各路線 VRP 效益指標")
                if not df_all[df_all['月份'] == current_month].empty:
                    df_cm = df_all[df_all['月份'] == current_month]
                    route_eff = df_cm.groupby('路線別').agg({
                        '合計總板數': 'mean', '總點數': 'mean', '工時': 'mean', '行駛里程': 'mean'
                    }).reset_index()
                    
                    # 計算當月圖表用的 VRP 效益值
                    def calc_chart_vrp(row):
                        p = row['合計總板數']
                        s = row['總點數'] if row['總點數'] > 0 else 1
                        h = row['工時'] if row['工時'] > 0 else 1
                        m = row['行駛里程'] if row['行駛里程'] > 0 else 1
                        return round((p / 50) * (5 / s) * (10 / h) * (100 / m) * 100, 1)
                    
                    route_eff['效益值'] = route_eff.apply(calc_chart_vrp, axis=1)
                    st.bar_chart(route_eff.set_index('路線別')['效益值'])
                else:
                    st.info("當月尚無資料可產生效益圖表")

            st.write("---")

            # ==========================================
            # 🔴 第三階段：獎金與路線指標明細 (清晰排版)
            # ==========================================
            unique_months = sorted(df_all['月份'].unique(), reverse=True)
            for month in unique_months:
                is_expanded = (month == current_month)
                with st.expander(f"📅 {month} 獎金與路線報表明細", expanded=is_expanded):
                    df_m = df_all[df_all['月份'] == month].copy()
                    
                    # 💰 獎金區塊
                    m_total_p = df_m['合計總板數'].sum()
                    base_bonus = (m_total_p * 40) + (df_m['空籃數'].sum() * 0.5) + (df_m['空板數'].sum() * 3)
                    multiplier = 1.2 if m_total_p >= 501 else (1.1 if m_total_p >= 451 else 1.0)
                    
                    st.success(f"💰 **{month} 結報預估總獎金：${int(base_bonus * multiplier):,}** (結算總板數: {int(m_total_p)} 板 / 適用倍率: {multiplier})")

                    # 📋 路線指標區塊
                    route_group = df_m.groupby('路線別').agg({
                        '運輸日期': 'count', 
                        '合計總板數': 'sum', 
                        '配送板數': 'sum',
                        '收貨板數': 'sum',
                        '總點數': 'mean',
                        '工時': 'mean', 
                        '行駛里程': 'mean'
                    }).reset_index()
                    
                    route_group.columns = ['路線別', '趟數', '總板數', '總配板', '總收板', '平均點數', '平均工時', '平均里程']
                    
                    # 進階計算
                    def calc_pallet_ratio(row):
                        total = row['總配板'] + row['總收板']
                        if total == 0: return "0% / 0%"
                        del_pct = int((row['總配板'] / total) * 100)
                        return f"送{del_pct}% / 收{100-del_pct}%"
                        
                    route_group['收送佔比'] = route_group.apply(calc_pallet_ratio, axis=1)
                    route_group['滿載率(%)'] = (route_group['總板數'] / (route_group['趟數'] * 28)) * 100
                    
                    def calc_vrp(row):
                        p = row['總板數'] / row['趟數'] # 平均板數
                        s = row['平均點數'] if row['平均點數'] > 0 else 1
                        h = row['平均工時'] if row['平均工時'] > 0 else 1
                        m = row['平均里程'] if row['平均里程'] > 0 else 1
                        return round((p / 50) * (5 / s) * (10 / h) * (100 / m) * 100, 1)
                    
                    route_group['效益值(VRP)'] = route_group.apply(calc_vrp, axis=1)
                    
                    # 重新排列顯示欄位，讓重點一目了然
                    display_cols = ['路線別', '趟數', '總板數', '收送佔比', '滿載率(%)', '平均工時', '平均里程', '效益值(VRP)']
                    
                    st.dataframe(route_group[display_cols].style.format({
                        "總板數": "{:,.0f} 板",
                        "滿載率(%)": "{:.1f}%",
                        "平均工時": "{:.1f} H",
                        "平均里程": "{:.1f} KM",
                        "效益值(VRP)": "{:.1f}"
                    }), use_container_width=True, hide_index=True)
        else:
            st.error(f"找不到『合計總板數』欄位。請檢查試算表第一列標題。")
    else:
        st.info("💡 試算表已連結。目前資料庫為空，請輸入第一筆紀錄。")

except Exception as e:
    st.error(f"系統異常：{e}")
