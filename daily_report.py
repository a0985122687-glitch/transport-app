import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
from datetime import datetime, timedelta
import altair as alt

# --- 網頁與版面設定 ---
st.set_page_config(page_title="運輸日報表分析系統", page_icon="🚛", layout="wide")
st.title("🚛 運輸日報表戰情室")

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

def extract_month_safe(date_val):
    try:
        s = str(date_val).replace('/', '-').strip()
        parts = s.split('-')
        if len(parts) >= 2:
            if len(parts[0]) == 4: return f"{parts[0]}-{parts[1].zfill(2)}"
            if len(parts[2]) == 4: return f"{parts[2]}-{parts[0].zfill(2)}"
        return 'Unknown'
    except: return 'Unknown'

ROUTE_ORDER = ["中一線", "中二線", "中三線", "中四線", "中五線", "中六線", "中七線"]

# ==========================================
# 🟢 第一階段：輸入區塊 (穩定版)
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
                total_p = (p_del_pallets or 0) + (p_pick_pallets or 0)
                row_data = [str(date), start_time, end_time, route, start_mileage, end_mileage, end_mileage - start_mileage, total_stops or 0, p_del_pallets or 0, p_pick_pallets or 0, total_p, p_baskets or 0, p_empty_pallets or 0]
                sheet.append_row(row_data)
                st.success("✅ 儲存成功！"); time.sleep(1); st.rerun()

    # ==========================================
    # 資料處理與分析
    # ==========================================
    all_raw = sheet.get_all_values()
    if len(all_raw) > 1:
        df = pd.DataFrame(all_raw[1:], columns=[h.strip() for h in all_raw[0]])
        df['月份'] = df['運輸日期'].apply(extract_month_safe)
        num_cols = ['行駛里程', '合計總板數', '空籃數', '空板數', '總點數', '配送板數', '收貨板數']
        for col in num_cols: df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        df['工時'] = df.apply(lambda r: calculate_work_hours(r.get('上班時間','0'), r.get('下班時間','0')), axis=1)

        st.write("---")
        st.subheader("📊 專業營運戰情分析")

        # ==========================================
        # 🟡 第二階段：驚艷圖表區 (Altair 引擎)
        # ==========================================
        c_chart1, c_chart2 = st.columns(2)
        
        # 🏆 圖 1: 每月總板數
        with c_chart1:
            st.caption("🏆 年度每月總板數趨勢")
            m_sum = df.groupby('月份')['合計總板數'].sum().reset_index()
            chart1 = alt.Chart(m_sum).mark_bar(color='#27AE60', cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                x=alt.X('月份', title=''), y=alt.Y('合計總板數', title=''), tooltip=['月份', '合計總板數']
            )
            text1 = chart1.mark_text(align='center', baseline='bottom', dy=-5, fontWeight='bold').encode(text='合計總板數')
            st.altair_chart((chart1 + text1).properties(height=300), use_container_width=True)

        # 🚚 圖 2: 滿載率對比 (送貨線 vs 收貨線)
        with c_chart2:
            st.caption("🚚 年度雙線滿載率走勢 (送 vs 收)")
            m_ratio = df.groupby('月份').agg({'運輸日期':'count', '配送板數':'sum', '收貨板數':'sum'}).reset_index()
            m_ratio['送貨滿載率%'] = (m_ratio['配送板數'] / (m_ratio['運輸日期'] * 28) * 100).round(0)
            m_ratio['收貨滿載率%'] = (m_ratio['收貨板數'] / (m_ratio['運輸日期'] * 28) * 100).round(0)
            df_melt = m_ratio.melt(id_vars=['月份'], value_vars=['送貨滿載率%', '收貨滿載率%'], var_name='類別', value_name='比率')
            chart2 = alt.Chart(df_melt).mark_line(point=True).encode(
                x='月份', y=alt.Y('比率', title='滿載率 (%)'), color=alt.Color('類別', scale=alt.Scale(range=['#2980B9', '#E67E22'])), tooltip=['月份', '類別', '比率']
            )
            st.altair_chart(chart2.properties(height=300), use_container_width=True)

        st.write("")
        c_chart3, c_chart4 = st.columns(2)
        current_month = datetime.today().strftime('%Y-%m')
        if not df[df['月份'] == current_month].empty:
            df_cm = df[df['月份'] == current_month].copy()
            rg_eff = df_cm.groupby('路線別').agg({'運輸日期':'count', '合計總板數':'sum', '總點數':'mean', '工時':'mean', '行駛里程':'mean'}).reset_index()
            
            # 🎯 VRP 效益值
            def calc_vrp(r):
                p = r['合計總板數'] / r['運輸日期']
                s, h, m = r['總點數'] or 1, r['工時'] or 1, r['行駛里程'] or 1
                score = 100 * ((p / (s * m * h)) / (50 / (5 * 100 * 10)))
                return int(min(100, round(score, 0)))
            
            # ⚙️ 運務實質稼動率 (單趟板數/工時 比例)
            def calc_util(r):
                p_per_trip = r['合計總板數'] / r['運輸日期']
                h_per_trip = r['工時']
                # 以 50板/10小時 = 5板/時 為 100% 基準
                return int(round((p_per_trip / h_per_trip) / 5 * 100, 0))

            rg_eff['效益值'] = rg_eff.apply(calc_vrp, axis=1)
            rg_eff['實質稼動率%'] = rg_eff.apply(calc_util, axis=1)
            rg_eff['路線別'] = pd.Categorical(rg_eff['路線別'], categories=ROUTE_ORDER, ordered=True)
            rg_eff = rg_eff.sort_values('路線別')

            with c_chart3:
                st.caption("🎯 當月 VRP 效益指標 (滿分100)")
                chart3 = alt.Chart(rg_eff).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                    x=alt.X('路線別', title='', axis=alt.Axis(labelAngle=0)), y=alt.Y('效益值', title='效益分數'),
                    color=alt.Color('效益值', scale=alt.Scale(scheme='blues'), legend=None)
                )
                st.altair_chart(chart3.properties(height=300), use_container_width=True)

            with c_chart4:
                st.caption("⚙️ 當月運務實質稼動率 (%)")
                chart4 = alt.Chart(rg_eff).mark_bar(color='#8E44AD', cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                    x=alt.X('路線別', title='', axis=alt.Axis(labelAngle=0)), y=alt.Y('實質稼動率%', title='稼動率 (%)')
                )
                st.altair_chart(chart4.properties(height=300), use_container_width=True)

        st.write("---")

        # ==========================================
        # 🔴 第三階段：報表細節 (消滅小數點 + 每日對帳)
        # ==========================================
        st.subheader("📋 營運報表細節")
        
        # 1. 年度總表
        current_year = datetime.today().strftime('%Y')
        with st.expander(f"🗓️ {current_year} 年度營運總結報告 (1-12月)", expanded=False):
            y_sum = df[df['運輸日期'].astype(str).str.contains(current_year)].groupby('月份').agg({'合計總板數':'sum', '空籃數':'sum', '空板數':'sum', '運輸日期':'count'}).reset_index()
            y_sum.rename(columns={'運輸日期':'總趟次', '合計總板數':'月總板數'}, inplace=True)
            for c in ['月總板數', '空籃數', '空板數', '總趟次']: y_sum[c] = y_sum[c].astype(int)
            
            def calc_y_bonus(r):
                multi = 1.2 if r['月總板數'] >= 501 else (1.1 if r['月總板數'] >= 451 else 1.0)
                return int((r['月總板數']*40*multi) + (r['空籃數']*0.5) + (r['空板數']*3))
            y_sum['預估總獎金'] = y_sum.apply(calc_y_bonus, axis=1)
            st.dataframe(y_sum[['月份', '月總板數', '總趟次', '預估總獎金']].style.format({"預估總獎金":"${:,}"}), use_container_width=True, hide_index=True)

        # 2. 各月每日明細
        unique_months = sorted([m for m in df['月份'].unique() if m != 'Unknown'], reverse=True)
        for month in unique_months:
            with st.expander(f"📅 {month} 營運明細", expanded=(month == current_month)):
                df_m = df[df['月份'] == month].copy()
                m_tp = int(df_m['合計總板數'].sum())
                m_multi = 1.2 if m_tp >= 501 else (1.1 if m_tp >= 451 else 1.0)
                
                # A. 每日明細 (排序、隱藏里程、點數)
                st.markdown("##### 📝 每日對帳紀錄 (日期排序)")
                df_m = df_m.sort_values('運輸日期')
                df_m['合計獎金'] = ((df_m['合計總板數']*40*m_multi) + (df_m['空籃數']*0.5) + (df_m['空板數']*3)).astype(int)
                df_m['加班標示'] = df_m['工時'].apply(lambda x: f"⚠️ +{x-10:.1f}H" if x > 10 else "-")
                
                # 挑選顯示欄位：不顯示行駛里程與點數
                display_daily = ['運輸日期', '路線別', '合計總板數', '空籃數', '空板數', '合計獎金', '工時', '加班標示']
                for c in ['合計總板數', '空籃數', '空板數']: df_m[c] = df_m[c].astype(int)
                st.dataframe(df_m[display_daily].style.format({"合計獎金":"${:,}", "工時":"{:.1f}H"}), use_container_width=True, hide_index=True)

                # B. 路線彙整
                st.markdown("##### 📊 路線效益彙整")
                rg = df_m.groupby('路線別').agg({'運輸日期':'count', '合計總板數':'sum', '配送板數':'sum', '收貨板數':'sum', '工時':'mean', '行駛里程':'mean', '總點數':'mean'}).reset_index()
                rg.columns = ['路線別', '趟數', '總板數', '配', '收', '平均工時', '平均里程', '平均點數']
                rg['效益值'] = rg.apply(calc_vrp, axis=1)
                rg['滿載率%'] = (rg['總板數'] / (rg['趟數'] * 28) * 100).round(1)
                rg['收送比'] = rg.apply(lambda r: f"送{int(r['配']/(r['配']+r['收'])*100)}%/收{100-int(r['配']/(r['配']+r['收'])*100)}%" if (r['配']+r['收'])>0 else "0/0", axis=1)
                
                rg['路線別'] = pd.Categorical(rg['路線別'], categories=ROUTE_ORDER, ordered=True)
                st.dataframe(rg.sort_values('路線別')[['路線別', '趟數', '總板數', '平均工時', '收送比', '滿載率%', '效益值']].style.format({"平均工時":"{:.1f}H", "總板數":"{:.0f}"}), use_container_width=True, hide_index=True)

    else: st.info("資料庫連結成功，目前尚無數據。")
