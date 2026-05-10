import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
from datetime import datetime, timedelta
import altair as alt  # 導入 Streamlit 內建的高階繪圖庫

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

ROUTE_ORDER = ["中一線", "中二線", "中三線", "中四線", "中五線", "中六線", "中七線"]

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
            route = c3.selectbox("路線別", ROUTE_ORDER)
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
        # 資料預處理
        # ==========================================
        st.write("---")
        st.subheader("📊 營運戰情分析與專業指標")
        
        all_raw = sheet.get_all_values()
        actual_data = [row for row in all_raw if any(str(cell).strip() for cell in row)]
        
        if len(actual_data) > 1:
            headers = [str(h).strip() for h in actual_data[0]]
            df_all = pd.DataFrame(actual_data[1:], columns=headers)
            
            if '合計總板數' not in df_all.columns:
                if '合計' in df_all.columns: df_all['合計總板數'] = df_all['合計']
                elif '配送板數' in df_all.columns and '收貨板數' in df_all.columns:
                    df_all['合計總板數'] = pd.to_numeric(df_all['配送板數'], errors='coerce').fillna(0) + pd.to_numeric(df_all['收貨板數'], errors='coerce').fillna(0)

            if '合計總板數' in df_all.columns:
                df_all['年份'] = df_all['運輸日期'].astype(str).str[:4]
                df_all['月份'] = df_all['運輸日期'].apply(extract_month)
                
                safe_num_cols = [c for c in ['行駛里程', '合計總板數', '空籃數', '空板數', '總點數', '配送板數', '收貨板數'] if c in df_all.columns]
                for col in safe_num_cols:
                    df_all[col] = pd.to_numeric(df_all[col].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
                
                df_all['工時'] = df_all.apply(lambda row: calculate_work_hours(row.get('上班時間','00:00'), row.get('下班時間','00:00')), axis=1)
                current_month = datetime.today().strftime('%Y-%m')

                # ==========================================
                # 🟡 第二階段：高階動態圖表區 (Altair 引擎)
                # ==========================================
                c_chart1, c_chart2 = st.columns(2)
                
                # 🏆 圖 1: 年度每月總板數趨勢
                with c_chart1:
                    st.caption("🏆 年度每月總板數趨勢")
                    month_group = df_all.groupby('月份')['合計總板數'].sum().reset_index()
                    base1 = alt.Chart(month_group).encode(x=alt.X('月份', title='', axis=alt.Axis(labelAngle=-45)))
                    bar1 = base1.mark_bar(color='#2ECC71', cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(y=alt.Y('合計總板數', title='總板數'))
                    text1 = base1.mark_text(align='center', baseline='bottom', dy=-5, color='#333333', fontWeight='bold').encode(y='合計總板數', text='合計總板數')
                    st.altair_chart((bar1 + text1).properties(height=320), use_container_width=True)

                # 🚚 圖 2: 年度雙線滿載率對比 (送 vs 收)
                with c_chart2:
                    st.caption("🚚 年度雙線滿載率對比 (送 vs 收)")
                    m_ratio = df_all.groupby('月份').agg({'運輸日期':'count', '配送板數':'sum', '收貨板數':'sum'}).reset_index()
                    m_ratio['送貨滿載率(%)'] = ((m_ratio['配送板數'] / (m_ratio['運輸日期'] * 28)) * 100).astype(int)
                    m_ratio['收貨滿載率(%)'] = ((m_ratio['收貨板數'] / (m_ratio['運輸日期'] * 28)) * 100).astype(int)
                    df_melt = m_ratio.melt(id_vars=['月份'], value_vars=['送貨滿載率(%)', '收貨滿載率(%)'], var_name='類別', value_name='滿載率(%)')
                    
                    chart2 = alt.Chart(df_melt).mark_line(point=alt.OverlayMarkDef(filled=True, size=60)).encode(
                        x=alt.X('月份', title='', axis=alt.Axis(labelAngle=-45)),
                        y=alt.Y('滿載率(%)', title='滿載率 (%)'),
                        color=alt.Color('類別', scale=alt.Scale(domain=['送貨滿載率(%)', '收貨滿載率(%)'], range=['#3498DB', '#E67E22']), legend=alt.Legend(title="", orient="top")),
                        tooltip=['月份', '類別', '滿載率(%)']
                    ).properties(height=320)
                    st.altair_chart(chart2, use_container_width=True)

                st.write("")
                c_chart3, c_chart4 = st.columns(2)
                
                if not df_all[df_all['月份'] == current_month].empty:
                    df_cm = df_all[df_all['月份'] == current_month].copy()
                    route_eff = df_cm.groupby('路線別').agg({
                        '運輸日期': 'count', '合計總板數': 'sum', '總點數': 'mean', '工時': 'mean', '行駛里程': 'mean'
                    }).reset_index().rename(columns={'運輸日期': '趟數'})
                    
                    # 🎯 VRP 公式 (效益)
                    def calc_chart_vrp(row):
                        p = row['合計總板數'] / row['趟數'] if row['趟數'] > 0 else 0
                        s, h, m = row['總點數'] if row['總點數'] > 0 else 1, row['工時'] if row['工時'] > 0 else 1, row['行駛里程'] if row['行駛里程'] > 0 else 1
                        score = 100 * ((p / (s * m * h)) / (50 / (5 * 100 * 10)))
                        return int(min(100, round(score, 0)))
                    
                    # ⚙️ 稼動率公式 (實質產能飽和度) -> (單趟板數/工時) 相對於 (50板/10H)
                    def calc_utilization(row):
                        p = row['合計總板數'] / row['趟數'] if row['趟數'] > 0 else 0
                        h = row['工時'] if row['工時'] > 0 else 1
                        util = (p / h) / (50 / 10) * 100
                        return int(round(util, 0))
                    
                    route_eff['效益值'] = route_eff.apply(calc_chart_vrp, axis=1)
                    route_eff['實質稼動率(%)'] = route_eff.apply(calc_utilization, axis=1)
                    
                    route_eff['路線別'] = pd.Categorical(route_eff['路線別'], categories=ROUTE_ORDER, ordered=True)
                    route_eff = route_eff.sort_values('路線別')

                    # 🎯 圖 3: 當月各路線 VRP 效益指標
                    with c_chart3:
                        st.caption("🎯 當月 VRP 效益指標 (滿分100)")
                        base3 = alt.Chart(route_eff).encode(x=alt.X('路線別', sort=ROUTE_ORDER, title='', axis=alt.Axis(labelAngle=0)))
                        bar3 = base3.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                            y=alt.Y('效益值', title='效益分數'),
                            color=alt.Color('效益值', scale=alt.Scale(scheme='blues'), legend=None)
                        )
                        text3 = base3.mark_text(align='center', baseline='bottom', dy=-5, fontWeight='bold').encode(y='效益值', text='效益值')
                        st.altair_chart((bar3 + text3).properties(height=320), use_container_width=True)

                    # ⚙️ 圖 4: 當月運務實質稼動率
                    with c_chart4:
                        st.caption("⚙️ 當月運務實質稼動率 (%)")
                        base4 = alt.Chart(route_eff).encode(x=alt.X('路線別', sort=ROUTE_ORDER, title='', axis=alt.Axis(labelAngle=0)))
                        bar4 = base4.mark_bar(color='#9B59B6', cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(y=alt.Y('實質稼動率(%)', title='稼動率 (%)'))
                        text4 = base4.mark_text(align='center', baseline='bottom', dy=-5, fontWeight='bold', color='#333333').encode(y='實質稼動率(%)', text=alt.Text('實質稼動率(%)'))
                        st.altair_chart((bar4 + text4).properties(height=320), use_container_width=True)
                else:
                    st.info("當月尚無資料可產生效益圖表")

                st.write("---")

                # ==========================================
                # 🔴 第三階段：營運報表與獎金明細 (完美對帳版)
                # ==========================================
                st.markdown("### 📋 營運報表與獎金明細")
                
                current_year = datetime.today().strftime('%Y')
                with st.expander(f"🗓️ {current_year} 年度營運總結報告 (1-12月)", expanded=False):
                    df_y = df_all[df_all['年份'] == current_year].copy()
                    if not df_y.empty:
                        y_sum = df_y.groupby('月份').agg({'合計總板數':'sum', '空籃數':'sum', '空板數':'sum', '行駛里程':'sum', '運輸日期':'count'}).reset_index()
                        y_sum.columns = ['月份', '月總板數(40元)', '月總空籃(0.5元)', '月總空板(3元)', '總里程(KM)', '總趟次']
                        
                        for col in ['月總板數(40元)', '月總空籃(0.5元)', '月總空板(3元)', '總里程(KM)', '總趟次']:
                            y_sum[col] = y_sum[col].astype(int)
                            
                        def calc_y_bonus(row):
                            multi = 1.2 if row['月總板數(40元)'] >= 501 else (1.1 if row['月總板數(40元)'] >= 451 else 1.0)
                            return int((row['月總板數(40元)'] * 40 * multi) + (row['月總空籃(0.5元)'] * 0.5) + (row['月總空板(3元)'] * 3))
                        y_sum['預估總獎金'] = y_sum.apply(calc_y_bonus, axis=1)
                        
                        display_y_cols = ['月份', '月總板數(40元)', '月總空籃(0.5元)', '月總空板(3元)', '總趟次', '總里程(KM)', '預估總獎金']
                        st.dataframe(y_sum[display_y_cols].style.format({
                            "月總板數(40元)": "{:,}", "月總空籃(0.5元)": "{:,}", "月總空板(3元)": "{:,}",
                            "總里程(KM)": "{:,}", "預估總獎金":"${:,}"
                        }), use_container_width=True, hide_index=True)
                    else: st.write("目前尚無年度數據。")

                unique_months = sorted([m for m in df_all['月份'].unique() if m != 'Unknown'], reverse=True)
                for month in unique_months:
                    is_expanded = (month == current_month)
                    with st.expander(f"📅 {month} 營運報表細節", expanded=is_expanded):
                        df_m = df_all[df_all['月份'] == month].copy()
                        
                        m_total_p = int(df_m['合計總板數'].sum())
                        m_baskets = int(df_m['空籃數'].sum() if '空籃數' in df_m.columns else 0)
                        m_empty_p = int(df_m['空板數'].sum() if '空板數' in df_m.columns else 0)
                        multiplier = 1.2 if m_total_p >= 501 else (1.1 if m_total_p >= 451 else 1.0)
                        final_bonus = (m_total_p * 40 * multiplier) + (m_baskets * 0.5) + (m_empty_p * 3)
                        
                        st.success(f"💰 **{month} 結算預估總獎金：${int(final_bonus):,}** *(階梯倍率: {multiplier} 倍)*")

                        # --- A. 每日出勤對帳明細 ---
                        st.markdown("##### 📝 每日出勤對帳明細 (依日期排序)")
                        df_m = df_m.sort_values(by='運輸日期', ascending=True)
                        df_m['單日合計獎金'] = ((df_m['合計總板數'] * 40 * multiplier) + (df_m['空籃數'] * 0.5) + (df_m['空板數'] * 3)).astype(int)
                        df_m['加班標示'] = df_m['工時'].apply(lambda x: f"⚠️ +{x-10:.1f}H" if x > 10 else "-")
                        for c in ['合計總板數', '空籃數', '空板數']: df_m[c] = df_m[c].astype(int)
                            
                        daily_cols = ['運輸日期', '路線別', '合計總板數', '空籃數', '空板數', '單日合計獎金', '工時', '加班標示']
                        st.dataframe(df_m[daily_cols].style.format({
                            "合計總板數": "{:,}", "空籃數": "{:,}", "空板數": "{:,}", "單日合計獎金": "${:,}", "工時": "{:.1f} H"
                        }), use_container_width=True, hide_index=True)

                        # --- B. 路線 VRP 效益彙整 ---
                        st.markdown("##### 📊 路線 VRP 效益彙整")
                        agg_dict = {'運輸日期': 'count', '合計總板數': 'sum', '空籃數': 'sum', '空板數': 'sum', '工時': 'mean', '行駛里程': 'mean'}
                        if '配送板數' in df_m.columns: agg_dict['配送板數'] = 'sum'
                        if '收貨板數' in df_m.columns: agg_dict['收貨板數'] = 'sum'
                        if '總點數' in df_m.columns: agg_dict['總點數'] = 'mean'
                        
                        route_group = df_m.groupby('路線別').agg(agg_dict).reset_index()
                        route_group.rename(columns={'運輸日期': '趟數', '合計總板數': '總板數(40元)', '工時': '平均工時', '行駛里程': '平均里程', '配送板數': '總配板', '收貨板數': '總收板', '總點數': '平均點數'}, inplace=True)
                        for col in ['總配板', '總收板', '平均點數']:
                            if col not in route_group.columns: route_group[col] = 0
                        for col in ['總板數(40元)', '空籃數', '空板數']: route_group[col] = route_group[col].fillna(0).astype(int)

                        def calc_pallet_ratio(row):
                            total = row['總配板'] + row['總收板']
                            if total == 0: return "0% / 0%"
                            del_pct = int((row['總配板'] / total) * 100)
                            return f"送{del_pct}% / 收{100-del_pct}%"
                            
                        route_group['收送佔比'] = route_group.apply(calc_pallet_ratio, axis=1)
                        route_group['滿載率(%)'] = (route_group['總板數(40元)'] / (route_group['趟數'] * 28)) * 100
                        route_group['效益值(VRP)'] = route_group.apply(calc_chart_vrp, axis=1)
                        
                        route_group['路線別'] = pd.Categorical(route_group['路線別'], categories=ROUTE_ORDER, ordered=True)
                        route_group = route_group.sort_values('路線別')
                        
                        display_cols = ['路線別', '趟數', '總板數(40元)', '平均點數', '平均工時', '平均里程', '收送佔比', '滿載率(%)', '效益值(VRP)']
                        st.dataframe(route_group[display_cols].style.format({
                            "總板數(40元)": "{:,}", "平均點數": "{:.1f}", "滿載率(%)": "{:.1f}%", "平均工時": "{:.1f} H", "平均里程": "{:.1f} KM", "效益值(VRP)": "{:d} 分"
                        }), use_container_width=True, hide_index=True)
            else:
                st.error(f"找不到『合計總板數』相關欄位。目前抓到的標題為：{headers}")
        else:
            st.info("💡 試算表已連結。目前資料庫為空，請輸入第一筆紀錄。")

except Exception as e:
    st.error(f"系統異常：{e}")
