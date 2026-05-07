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
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds_dict = st.secrets["service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        sheet_url = "https://docs.google.com/spreadsheets/d/1VzyglFpEC3yS11aIoU1YJclw-6Moaewyf8DTR-j7HDc/edit?gid=0#gid=0"
        return client.open_by_url(sheet_url).sheet1
    except Exception as e:
        st.error(f"資料庫連線失敗，請檢查金鑰設定：{e}")
        return None

# --- 工具函數 ---
def calculate_work_hours(start_str, end_str):
    try:
        s_str = str(start_str).strip()
        e_str = str(end_str).strip()
        fmt_s = "%H:%M:%S" if s_str.count(':') == 2 else "%H:%M"
        fmt_e = "%H:%M:%S" if e_str.count(':') == 2 else "%H:%M"
        start = datetime.strptime(s_str, fmt_s)
        end = datetime.strptime(e_str, fmt_e)
        if end < start:
            end += timedelta(days=1)
        return (end - start).total_seconds() / 3600
    except:
        return 0

def extract_month(date_val):
    try:
        d_str = str(date_val).replace('/', '-').strip()
        parts = d_str.split('-')
        if len(parts) >= 2:
            return f"{parts[0]}-{parts[1].zfill(2)}"
        return 'Unknown'
    except:
        return 'Unknown'

# ==========================================
# 🟢 第一階段：輸入區塊
# ==========================================
try:
    sheet = get_sheet()
    if sheet:
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
            
            if '合計總板數' not in df_all.columns:
                if '合計' in df_all.columns:
                    df_all['合計總板數'] = df_all['合計']
                elif '配送板數' in df_all.columns and '收貨板數' in df_all.columns:
                    df_all['合計總板數'] = pd.to_numeric(df_all['配送板數'], errors='coerce').fillna(0) + pd.to_numeric(df_all['收貨板數'], errors='coerce').fillna(0)

            if '合計總板數' in df_all.columns:
                df_all['年份'] = df_all['運輸日期'].astype(str).str[:4]
                df_all['月份'] = df_all['運輸日期'].apply(extract_month)
                
                expected_num_cols = ['行駛里程', '合計總板數', '空籃數', '空板數', '總點數', '配送板數', '收貨板數']
                safe_num_cols = [c for c in expected_num_cols if c in df_all.columns]
                
                for col in safe_num_cols:
                    df_all[col] = pd.to_numeric(df_all[col].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
                
                df_all['工時'] = df_all.apply(lambda row: calculate_work_hours(row.get('上班時間','00:00'), row.get('下班時間','00:00')), axis=1)
                current_month = datetime.today().strftime('%Y-%m')

                # ==========================================
                # 🟡 第二階段：營運圖表區
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
                        
                        def calc_chart_vrp(row):
                            p = row['合計總板數']
                            s = row['總點數'] if row['總點數'] > 0 else 1
                            h = row['工時'] if row['工時'] > 0 else 1
                            m = row['行駛里程'] if row['行駛里程'] > 0 else 1
                            return int(min(100, round(100 * (p / (s * m * h)) / 0.01, 0)))
                        
                        route_eff['效益值'] = route_eff.apply(calc_chart_vrp, axis=1)
                        st.bar_chart(route_eff.set_index('路線別')['效益值'])
                    else:
                        st.info("當月尚無資料可產生效益圖表")

                st.write("---")

                # ==========================================
                # 🔴 第三階段：營運報表與獎金明細 (細節微調)
                # ==========================================
                st.markdown("### 📋 營運報表與獎金明細")
                
                # --- 1. 年度總表展開 ---
                current_year = datetime.today().strftime('%Y')
                with st.expander(f"🗓️ {current_year} 年度營運總結報告 (1-12月)", expanded=False):
                    df_y = df_all[df_all['年份'] == current_year].copy()
                    if not df_y.empty:
                        y_sum = df_y.groupby('月份').agg({'合計總板數':'sum', '空籃數':'sum', '空板數':'sum', '行駛里程':'sum', '運輸日期':'count'}).reset_index()
                        
                        y_sum.columns = ['月份', '月總板數(40元)', '月總空籃(0.5元)', '月總空板(3元)', '總里程(KM)', '趟數']
                        
                        for col in ['月總板數(40元)', '月總空籃(0.5元)', '月總空板(3元)', '總里程(KM)', '趟數']:
                            y_sum[col] = y_sum[col].astype(int)
                            
                        # 修正：倍數只影響總板數，空板空籃固定獎金
                        def calc_y_bonus(row):
                            pallet_bonus = row['月總板數(40元)'] * 40
                            multi = 1.2 if row['月總板數(40元)'] >= 501 else (1.1 if row['月總板數(40元)'] >= 451 else 1.0)
                            fixed_bonus = (row['月總空籃(0.5元)'] * 0.5) + (row['月總空板(3元)'] * 3)
                            return int((pallet_bonus * multi) + fixed_bonus)
                        
                        y_sum['預估總獎金'] = y_sum.apply(calc_y_bonus, axis=1)
                        
                        st.dataframe(y_sum.style.format({
                            "月總板數(40元)": "{:,}",
                            "月總空籃(0.5元)": "{:,}",
                            "月總空板(3元)": "{:,}",
                            "總里程(KM)": "{:,}",
                            "預估總獎金":"${:,}"
                        }), use_container_width=True, hide_index=True)
                    else:
                        st.write("目前尚無年度數據。")

                # --- 2. 月度展開 ---
                unique_months = sorted([m for m in df_all['月份'].unique() if m != 'Unknown'], reverse=True)
                
                for month in unique_months:
                    is_expanded = (month == current_month)
                    with st.expander(f"📅 {month} 營運報表細節", expanded=is_expanded):
                        df_m = df_all[df_all['月份'] == month].copy()
                        
                        m_total_p = df_m['合計總板數'].sum()
                        m_baskets = df_m['空籃數'].sum() if '空籃數' in df_m.columns else 0
                        m_empty_p = df_m['空板數'].sum() if '空板數' in df_m.columns else 0
                        
                        # 修正：倍數只影響總板數，空板空籃固定獎金
                        pallet_bonus = m_total_p * 40
                        multiplier = 1.2 if m_total_p >= 501 else (1.1 if m_total_p >= 451 else 1.0)
                        fixed_bonus = (m_baskets * 0.5) + (m_empty_p * 3)
                        final_bonus = (pallet_bonus * multiplier) + fixed_bonus
                        
                        st.success(f"💰 **{month} 結算預估總獎金：${int(final_bonus):,}** \n"
                                   f"*(計算基準：[總板數 {int(m_total_p)} 板 × 40元 × 階梯 {multiplier} 倍] ＋ [空籃 {int(m_baskets)} 個 × 0.5元] ＋ [空板 {int(m_empty_p)} 個 × 3元])*")

                        agg_dict = {'運輸日期': 'count', '合計總板數': 'sum', '工時': 'mean', '行駛里程': 'mean'}
                        if '配送板數' in df_m.columns: agg_dict['配送板數'] = 'sum'
                        if '收貨板數' in df_m.columns: agg_dict['收貨板數'] = 'sum'
                        if '總點數' in df_m.columns: agg_dict['總點數'] = 'mean'
                        
                        route_group = df_m.groupby('路線別').agg(agg_dict).reset_index()
                        
                        rename_dict = {'運輸日期': '趟數', '合計總板數': '總板數', '工時': '平均工時', '行駛里程': '平均里程', '配送板數': '總配板', '收貨板數': '總收板', '總點數': '平均點數'}
                        route_group.rename(columns=rename_dict, inplace=True)
                        
                        for col in ['總配板', '總收板', '平均點數']:
                            if col not in route_group.columns: route_group[col] = 0

                        def calc_pallet_ratio(row):
                            total = row['總配板'] + row['總收板']
                            if total == 0: return "0% / 0%"
                            del_pct = int((row['總配板'] / total) * 100)
                            return f"送{del_pct}% / 收{100-del_pct}%"
                            
                        route_group['收送佔比'] = route_group.apply(calc_pallet_ratio, axis=1)
                        route_group['滿載率(%)'] = (route_group['總板數'] / (route_group['趟數'] * 28)) * 100
                        
                        def calc_vrp_user(row):
                            p = row['總板數'] / row['趟數'] if row['趟數'] > 0 else 0
                            s = row['平均點數'] if row['平均點數'] > 0 else 1
                            h = row['平均工時'] if row['平均工時'] > 0 else 1
                            m = row['平均里程'] if row['平均里程'] > 0 else 1
                            raw_score = 100 * (p / (s * m * h)) / 0.01
                            return int(min(100, round(raw_score, 0)))
                        
                        route_group['效益值(VRP)'] = route_group.apply(calc_vrp_user, axis=1)
                        
                        display_cols = ['路線別', '趟數', '總板數', '收送佔比', '滿載率(%)', '平均工時', '平均里程', '效益值(VRP)']
                        
                        st.dataframe(route_group[display_cols].style.format({
                            "總板數": "{:,.0f} 板",
                            "滿載率(%)": "{:.1f}%",
                            "平均工時": "{:.1f} H",
                            "平均里程": "{:.1f} KM",
                            "效益值(VRP)": "{:d} 分"
                        }), use_container_width=True, hide_index=True)
            else:
                st.error(f"找不到『合計總板數』相關欄位。目前抓到的標題為：{headers}")
        else:
            st.info("💡 試算表已連結。目前資料庫為空，請輸入第一筆紀錄。")

except Exception as e:
    st.error(f"系統異常：{e}")
