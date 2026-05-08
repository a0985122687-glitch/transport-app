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
        if "service_account" not in st.secrets:
            st.error("系統異常：找不到 Secret 金鑰設定。")
            return None
        creds_dict = st.secrets["service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        sheet_url = "https://docs.google.com/spreadsheets/d/1VzyglFpEC3yS11aIoU1YJclw-6Moaewyf8DTR-j7HDc/edit?gid=0#gid=0"
        return client.open_by_url(sheet_url).sheet1
    except Exception as e:
        st.error(f"資料庫連線失敗：{e}")
        return None

# --- 工具函數 ---
def calculate_work_hours(start_str, end_str):
    try:
        s_str, e_str = str(start_str).strip(), str(end_str).strip()
        fmt_s = "%H:%M:%S" if s_str.count(':') == 2 else "%H:%M"
        fmt_e = "%H:%M:%S" if e_str.count(':') == 2 else "%H:%M"
        start, end = datetime.strptime(s_str, fmt_s), datetime.strptime(e_str, fmt_e)
        if end < start: end += timedelta(days=1)
        return (end - start).total_seconds() / 3600
    except: return 0

def extract_month(date_val):
    try:
        d_str = str(date_val).replace('/', '-').strip()
        parts = d_str.split('-')
        return f"{parts[0]}-{parts[1].zfill(2)}" if len(parts) >= 2 else 'Unknown'
    except: return 'Unknown'

ROUTE_ORDER = ["中一線", "中二線", "中三線", "中四線", "中五線", "中六線", "中七線"]

# ==========================================
# 🟢 第一階段：輸入區塊
# ==========================================
sheet = get_sheet()
if sheet:
    with st.form("daily_report_form", clear_on_submit=True):
        st.subheader("📝 趟次紀錄")
        c1, c2, c3, c4 = st.columns(4)
        date = c1.date_input("運輸日期", datetime.today())
        start_time = c2.selectbox("上班時間", ["04:30", "05:00", "05:30", "06:00", "06:30", "07:00", "07:30"])
        route = c3.selectbox("路線別", ROUTE_ORDER)
        start_mileage = c4.number_input("里程 (起)", min_value=0, step=1, value=None)
        
        c5, c6, c7, c8, c9 = st.columns(5)
        total_stops = c5.number_input("總點數", min_value=0, step=1, value=None)
        p_del_pallets = c6.number_input("配送板數", min_value=0, step=1, value=None)
        p_pick_pallets = c7.number_input("收貨板數", min_value=0, step=1, value=None)
        p_baskets = c8.number_input("空籃數", min_value=0, step=1, value=None)
        p_empty_pallets = c9.number_input("空板數", min_value=0, step=1, value=None)

        c10, c11 = st.columns([1, 1])
        end_time = c10.selectbox("下班時間", ["13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30", "18:00", "18:30"], index=6) 
        end_mileage = c11.number_input("里程 (迄)", min_value=0, step=1, value=None)
        
        if st.form_submit_button("🚀 儲存紀錄"):
            if start_mileage is not None and end_mileage is not None:
                row_data = [str(date), start_time, end_time, route, start_mileage, end_mileage, end_mileage - start_mileage, total_stops or 0, p_del_pallets or 0, p_pick_pallets or 0, (p_del_pallets or 0)+(p_pick_pallets or 0), p_baskets or 0, p_empty_pallets or 0]
                try:
                    sheet.append_row(row_data)
                    st.success("✅ 儲存成功！"); time.sleep(1); st.rerun()
                except Exception as e:
                    st.error(f"⚠️ 儲存失敗：{e}")

    # ==========================================
    # 🔴 資料處理與智慧校正
    # ==========================================
    try:
        all_raw = sheet.get_all_values()
        if len(all_raw) > 1:
            headers = [str(h).replace(' ', '').strip() for h in all_raw[0]]
            df = pd.DataFrame(all_raw[1:], columns=headers)
            
            rename_map = {
                '日期': '運輸日期', '合計': '合計總板數', '總板數': '合計總板數',
                '里程數': '行駛里程', '點數': '總點數', '空籃數量': '空籃數',
                '空棧板數量': '空板數', '空板數量': '空板數'
            }
            df.rename(columns=rename_map, inplace=True)
            
            if '運輸日期' not in df.columns: st.stop()
            if '合計總板數' not in df.columns:
                if '配送板數' in df.columns and '收貨板數' in df.columns:
                    df['合計總板數'] = pd.to_numeric(df['配送板數'], errors='coerce').fillna(0) + pd.to_numeric(df['收貨板數'], errors='coerce').fillna(0)
                else: st.stop()

            # 🛡️ 終極防呆裝甲：缺什麼欄位就自動補 0，保證不斷線
            core_cols = ['行駛里程', '合計總板數', '空籃數', '空板數', '總點數', '配送板數', '收貨板數']
            for c in core_cols:
                if c not in df.columns:
                    df[c] = 0

            df['月份'] = df['運輸日期'].apply(extract_month)
            for col in core_cols: 
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            
            df['工時'] = df.apply(lambda r: calculate_work_hours(r.get('上班時間','0'), r.get('下班時間','0')), axis=1)

            st.write("---")
            st.subheader("📋 營運報表明細與效益分析")

            # ==========================================
            # 🟡 第二階段：營運圖表區 (效能指數版)
            # ==========================================
            c_chart1, c_chart2 = st.columns(2)
            current_month = datetime.today().strftime('%Y-%m')
            
            with c_chart1:
                st.caption("🏆 年度每月總板數趨勢")
                st.bar_chart(df.groupby('月份')['合計總板數'].sum())
            
            with c_chart2:
                st.caption("🎯 當月各路線相對效能指數 (越高越好)")
                if not df[df['月份'] == current_month].empty:
                    df_cm = df[df['月份'] == current_month]
                    route_eff = df_cm.groupby('路線別').agg({
                        '運輸日期': 'count', '合計總板數': 'sum', '總點數': 'mean', '工時': 'mean', '行駛里程': 'mean'
                    }).reset_index()
                    route_eff.rename(columns={'運輸日期': '趟數'}, inplace=True)
                    
                    def calc_chart_efficiency(r):
                        p = r['合計總板數'] / r['趟數'] if r['趟數'] > 0 else 0
                        s, h, m = r['總點數'] or 1, r['工時'] or 1, r['行駛里程'] or 1
                        return round((p / (s * m * h)) * 10000, 1)

                    route_eff['效能指數'] = route_eff.apply(calc_chart_efficiency, axis=1)
                    route_eff['路線別'] = pd.Categorical(route_eff['路線別'], categories=ROUTE_ORDER, ordered=True)
                    st.bar_chart(route_eff.sort_values('路線別').set_index('路線別')['效能指數'])
                else:
                    st.info("當月尚無資料可產生效益圖表")

            st.write("---")

            # ==========================================
            # 🔴 第三階段：營運報表細節 (年度 + 每日 + 總結)
            # ==========================================
            current_year = datetime.today().strftime('%Y')
            with st.expander(f"🗓️ {current_year} 年度營運總結報告 (1-12月)", expanded=False):
                df_y = df[df['年份'] == current_year].copy()
                if not df_y.empty:
                    y_sum = df_y.groupby('月份').agg({'合計總板數':'sum', '空籃數':'sum', '空板數':'sum', '運輸日期':'count'}).reset_index()
                    
                    y_sum.rename(columns={'運輸日期': '總趟次', '合計總板數': '月總板數(40元)', '空籃數': '月總空籃(0.5元)', '空板數': '月總空板(3元)'}, inplace=True)
                    y_sum['趟次平均板數'] = (y_sum['月總板數(40元)'] / y_sum['總趟次']).round(1)
                    
                    for col in ['月總板數(40元)', '月總空籃(0.5元)', '月總空板(3元)', '總趟次']:
                        y_sum[col] = y_sum[col].astype(int)
                        
                    def calc_y_bonus(row):
                        multi = 1.2 if row['月總板數(40元)'] >= 501 else (1.1 if row['月總板數(40元)'] >= 451 else 1.0)
                        return int((row['月總板數(40元)'] * 40 * multi) + (row['月總空籃(0.5元)'] * 0.5) + (row['月總空板(3元)'] * 3))
                    
                    y_sum['預估總獎金'] = y_sum.apply(calc_y_bonus, axis=1)
                    
                    display_y_cols = ['月份', '月總板數(40元)', '月總空籃(0.5元)', '月總空板(3元)', '總趟次', '趟次平均板數', '預估總獎金']
                    st.dataframe(y_sum[display_y_cols].style.format({
                        "月總板數(40元)": "{:,}", "月總空籃(0.5元)": "{:,}", "月總空板(3元)": "{:,}",
                        "趟次平均板數": "{:.1f}", "預估總獎金":"${:,}"
                    }), use_container_width=True, hide_index=True)
                else: st.write("目前尚無年度數據。")

            unique_months = sorted([m for m in df['月份'].unique() if m != 'Unknown'], reverse=True)
            for month in unique_months:
                with st.expander(f"📅 {month} 營運報表細節", expanded=(month == current_month)):
                    df_m = df[df['月份'] == month].copy()
                    
                    m_tp, m_b, m_e = int(df_m['合計總板數'].sum()), int(df_m['空籃數'].sum()), int(df_m['空板數'].sum())
                    multi = 1.2 if m_tp >= 501 else (1.1 if m_tp >= 451 else 1.0)
                    final_bonus = (m_tp * 40 * multi) + (m_b * 0.5) + (m_e * 3)
                    
                    st.success(f"💰 **{month} 結算預估總獎金：${int(final_bonus):,}** \n"
                               f"*(計算基準：[總板數 {m_tp} 板 × 40元 × 階梯 {multi} 倍] ＋ [空籃 {m_b} 個 × 0.5元] ＋ [空板 {m_e} 個 × 3元])*")

                    st.markdown("##### 📝 當月每日出勤紀錄")
                    daily_cols = ['運輸日期', '路線別', '上班時間', '下班時間', '工時', '行駛里程', '總點數', '合計總板數', '空籃數', '空板數']
                    safe_daily_cols = [c for c in daily_cols if c in df_m.columns]
                    st.dataframe(df_m[safe_daily_cols].sort_values('運輸日期').style.format({
                        "工時": "{:.1f} H", "行駛里程": "{:.1f} KM", "合計總板數": "{:.0f}", "空籃數": "{:.0f}", "空板數": "{:.0f}"
                    }), use_container_width=True, hide_index=True)

                    st.markdown("##### 📊 路線彙整與效能指標")
                    
                    # 🛡️ 安全計算：保證所有要用到的欄位都抓得到
                    agg_cols = {
                        '運輸日期':'count', '合計總板數':'sum', '總點數':'mean', 
                        '工時':'mean', '行駛里程':'mean', '配送板數':'sum', 
                        '收貨板數':'sum', '空籃數':'sum', '空板數':'sum'
                    }
                    rg = df_m.groupby('路線別').agg(agg_cols).reset_index()
                    rg.columns = ['路線別', '總趟次', '總板數(40元)', '平均點數', '平均工時', '平均里程', '配板', '收板', '空籃(0.5元)', '空板(3元)']
                    
                    for col in ['總板數(40元)', '空籃(0.5元)', '空板(3元)']: rg[col] = rg[col].astype(int)

                    def calc_pallet_ratio(row):
                        total = row['配板'] + row['收板']
                        if total == 0: return "0% / 0% ➖"
                        del_pct = int((row['配板'] / total) * 100)
                        pick_pct = 100 - del_pct
                        arrow = "🔼" if del_pct > pick_pct else ("🔽" if pick_pct > del_pct else "➖")
                        return f"送{del_pct}% / 收{pick_pct}% {arrow}"
                        
                    rg['收送佔比'] = rg.apply(calc_pallet_ratio, axis=1)
                    rg['滿載率%'] = (rg['總板數(40元)'] / (rg['總趟次'] * 28)) * 100
                    
                    def calc_efficiency_index(r):
                        p = r['總板數(40元)'] / r['總趟次'] if r['總趟次'] > 0 else 0
                        s, h, m = r['平均點數'] or 1, r['平均工時'] or 1, r['平均里程'] or 1
                        return round((p / (s * m * h)) * 10000, 1)

                    rg['效能指數'] = rg.apply(calc_efficiency_index, axis=1)
                    
                    rg['路線別'] = pd.Categorical(rg['路線別'], categories=ROUTE_ORDER, ordered=True)
                    rg = rg.sort_values('路線別').reset_index(drop=True)
                    
                    avg_row = pd.DataFrame([{
                        '路線別': '【全月總計/平均】', '總趟次': int(rg['總趟次'].sum()), '總板數(40元)': int(rg['總板數(40元)'].sum()),
                        '空籃(0.5元)': int(rg['空籃(0.5元)'].sum()), '空板(3元)': int(rg['空板(3元)'].sum()),
                        '平均點數': rg['平均點數'].mean(), '平均工時': rg['平均工時'].mean(), '平均里程': rg['平均里程'].mean(),
                        '效能指數': rg['效能指數'].mean(), '滿載率%': rg['滿載率%'].mean(), '收送佔比': '-'
                    }])
                    final_t = pd.concat([rg, avg_row], ignore_index=True)

                    display_cols = ['路線別', '總趟次', '總板數(40元)', '空籃(0.5元)', '空板(3元)', '平均點數', '平均工時', '平均里程', '收送佔比', '滿載率%', '效能指數']
                    st.dataframe(final_t[display_cols].style.format({
                        "總趟次": "{:.0f}", "總板數(40元)": "{:,.0f}", "空籃(0.5元)": "{:,.0f}", "空板(3元)": "{:,.0f}",
                        "平均點數": "{:.1f}", "平均工時": "{:.1f}H", "平均里程": "{:.1f}KM", "滿載率%": "{:.1f}%", "效能指數": "{:.1f}"
                    }), use_container_width=True, hide_index=True)

        else: st.info("💡 試算表已連結，目前尚無歷史數據。請輸入第一筆紀錄！")
    except Exception as e: st.error(f"數據讀取或顯示異常：{e}")
