import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
from datetime import datetime, timedelta
import plotly.express as px  # 導入專業互動式圖表庫

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

# 定義標準路線排序
ROUTE_ORDER = ["中一線", "中二線", "中三線", "中四線", "中五線", "中六線", "中七線"]

# ==========================================
# 🟢 第一階段：輸入區塊 (維持原樣)
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
        # 資料清洗與預處理
        # ==========================================
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
                for col in [c for c in expected_num_cols if c in df_all.columns]:
                    df_all[col] = pd.to_numeric(df_all[col].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
                
                df_all['工時'] = df_all.apply(lambda row: calculate_work_hours(row.get('上班時間','00:00'), row.get('下班時間','00:00')), axis=1)
                
                # 計算當月專用獎金倍率
                def calc_bonus(row, m_multiplier):
                    return (row['合計總板數'] * 40 * m_multiplier) + (row['空籃數'] * 0.5) + (row['空板數'] * 3)

                current_month = datetime.today().strftime('%Y-%m')

                st.write("---")
                st.subheader("📊 戰情圖表分析 (專業版)")

                # ==========================================
                # 🟡 第二階段：專業美化圖表區 (使用 Plotly)
                # ==========================================
                # 1. 準備全年度的月統計數據
                month_group = df_all.groupby('月份').agg({'合計總板數': 'sum', '空籃數': 'sum', '空板數': 'sum'}).reset_index()
                month_group['倍率'] = month_group['合計總板數'].apply(lambda x: 1.2 if x >= 501 else (1.1 if x >= 451 else 1.0))
                month_group['預估獎金'] = (month_group['合計總板數'] * 40 * month_group['倍率']) + (month_group['空籃數'] * 0.5) + (month_group['空板數'] * 3)
                month_group['預估獎金'] = month_group['預估獎金'].astype(int)
                
                tab1, tab2 = st.tabs(["📈 產能與獎金趨勢", "🎯 當月效能與工時預警"])
                
                with tab1:
                    col_c1, col_c2 = st.columns(2)
                    with col_c1:
                        # 圖 1：每月板數圖表
                        fig1 = px.bar(month_group, x='月份', y='合計總板數', text='合計總板數', 
                                      title='🏆 每月總板數趨勢圖', color_discrete_sequence=['#4CAF50'])
                        fig1.update_traces(textposition='outside')
                        st.plotly_chart(fig1, use_container_width=True)
                        
                    with col_c2:
                        # 圖 2：獎金對比圖表
                        fig2 = px.line(month_group, x='月份', y='預估獎金', text='預估獎金', markers=True,
                                       title='💰 每月預估獎金趨勢 (含空籃/板)', color_discrete_sequence=['#FF9800'])
                        fig2.update_traces(textposition='top center', textfont_size=12)
                        st.plotly_chart(fig2, use_container_width=True)

                with tab2:
                    col_c3, col_c4 = st.columns(2)
                    if not df_all[df_all['月份'] == current_month].empty:
                        df_cm = df_all[df_all['月份'] == current_month].copy()
                        route_eff = df_cm.groupby('路線別').agg({
                            '運輸日期': 'count', '合計總板數': 'sum', '總點數': 'mean', '工時': 'mean', '行駛里程': 'mean'
                        }).reset_index().rename(columns={'運輸日期': '趟數'})
                        
                        # 圖 3：VRP 效益指標
                        def calc_chart_vrp(row):
                            p = row['合計總板數'] / row['趟數'] if row['趟數'] > 0 else 0
                            s, h, m = row['總點數'] if row['總點數'] > 0 else 1, row['工時'] if row['工時'] > 0 else 1, row['行駛里程'] if row['行駛里程'] > 0 else 1
                            raw_score = 100 * (p / (s * m * h)) / (50 / (5 * 100 * 10))
                            return int(min(100, round(raw_score, 0)))
                        
                        route_eff['效益值'] = route_eff.apply(calc_chart_vrp, axis=1)
                        route_eff['路線別'] = pd.Categorical(route_eff['路線別'], categories=ROUTE_ORDER, ordered=True)
                        route_eff = route_eff.sort_values('路線別')
                        
                        with col_c3:
                            fig3 = px.bar(route_eff, x='路線別', y='效益值', text='效益值', 
                                          title='🎯 當月 VRP 效益指標 (滿分100)', color='效益值', color_continuous_scale='Blues')
                            fig3.update_layout(coloraxis_showscale=False)
                            st.plotly_chart(fig3, use_container_width=True)

                        # 圖 4：超時加班預警
                        with col_c4:
                            df_cm['超時時數'] = df_cm['工時'].apply(lambda x: max(0, x - 10))
                            ot_group = df_cm.groupby('路線別')['超時時數'].sum().reset_index()
                            ot_group['路線別'] = pd.Categorical(ot_group['路線別'], categories=ROUTE_ORDER, ordered=True)
                            ot_group = ot_group.sort_values('路線別')
                            fig4 = px.bar(ot_group, x='路線別', y='超時時數', text='超時時數',
                                          title='⚠️ 當月各路線累計超時加班 (大於10H)', color_discrete_sequence=['#F44336'])
                            fig4.update_traces(texttemplate='%{text:.1f}H', textposition='outside')
                            st.plotly_chart(fig4, use_container_width=True)
                    else:
                        st.info("當月尚無資料可產生效益圖表")

                st.write("---")

                # ==========================================
                # 🔴 第三階段：營運報表與獎金明細
                # ==========================================
                st.markdown("### 📋 營運報表與獎金明細")
                
                # --- 1. 年度總表 ---
                current_year = datetime.today().strftime('%Y')
                with st.expander(f"🗓️ {current_year} 年度營運總結報告", expanded=False):
                    df_y = df_all[df_all['年份'] == current_year].copy()
                    if not df_y.empty:
                        y_sum = df_y.groupby('月份').agg({'合計總板數':'sum', '空籃數':'sum', '空板數':'sum', '運輸日期':'count'}).reset_index()
                        y_sum.rename(columns={'運輸日期': '總趟次', '合計總板數': '月總板數', '空籃數': '月總空籃', '空板數': '月總空板'}, inplace=True)
                        
                        # 徹底消除小數點
                        for col in ['月總板數', '月總空籃', '月總空板', '總趟次']:
                            y_sum[col] = y_sum[col].astype(int)
                            
                        def calc_y_bonus(row):
                            multi = 1.2 if row['月總板數'] >= 501 else (1.1 if row['月總板數'] >= 451 else 1.0)
                            return int((row['月總板數'] * 40 * multi) + (row['月總空籃'] * 0.5) + (row['月總空板'] * 3))
                        
                        y_sum['預估總獎金'] = y_sum.apply(calc_y_bonus, axis=1)
                        st.dataframe(y_sum[['月份', '月總板數', '月總空籃', '月總空板', '總趟次', '預估總獎金']].style.format({
                            "月總板數": "{:,}", "月總空籃": "{:,}", "月總空板": "{:,}", "總趟次": "{:,}", "預估總獎金":"${:,}"
                        }), use_container_width=True, hide_index=True)
                    else:
                        st.write("目前尚無年度數據。")

                # --- 2. 各月明細與路線彙整 ---
                unique_months = sorted([m for m in df_all['月份'].unique() if m != 'Unknown'], reverse=True)
                
                for month in unique_months:
                    is_expanded = (month == current_month)
                    with st.expander(f"📅 {month} 營運報表細節", expanded=is_expanded):
                        df_m = df_all[df_all['月份'] == month].copy()
                        
                        # 計算該月總結與倍率
                        m_tp = int(df_m['合計總板數'].sum())
                        m_b = int(df_m['空籃數'].sum() if '空籃數' in df_m.columns else 0)
                        m_e = int(df_m['空板數'].sum() if '空板數' in df_m.columns else 0)
                        m_multi = 1.2 if m_tp >= 501 else (1.1 if m_tp >= 451 else 1.0)
                        final_bonus = (m_tp * 40 * m_multi) + (m_b * 0.5) + (m_e * 3)
                        
                        st.success(f"💰 **{month} 結算預估總獎金：${int(final_bonus):,}** \n"
                                   f"*(當月倍率: {m_multi} 倍)*")

                        # 📝 A. 當月每日出勤明細 (完美排序、去里程點數、加加班標示與單日獎金)
                        st.markdown("##### 📝 每日出勤明細 (依日期排序)")
                        
                        # 計算單日預估獎金與加班
                        df_m['合計獎金'] = df_m.apply(lambda r: int(calc_bonus(r, m_multi)), axis=1)
                        df_m['加班標示'] = df_m['工時'].apply(lambda x: f"⚠️ +{x-10:.1f}H" if x > 10 else "-")
                        
                        # 依日期強制排序
                        df_m = df_m.sort_values(by='運輸日期', ascending=True)
                        
                        # 挑選您要的欄位：隱藏里程/點數，保留板數/獎金/工時
                        daily_cols = ['運輸日期', '路線別', '合計總板數', '空籃數', '空板數', '合計獎金', '工時', '加班標示']
                        # 整數化
                        for c in ['合計總板數', '空籃數', '空板數']: df_m[c] = df_m[c].astype(int)
                        
                        st.dataframe(df_m[daily_cols].style.format({
                            "合計總板數": "{:,}", "空籃數": "{:,}", "空板數": "{:,}", "合計獎金": "${:,}", "工時": "{:.1f} H"
                        }), use_container_width=True, hide_index=True)

                        # 📊 B. 路線彙整表
                        st.markdown("##### 📊 路線 VRP 效益彙整")
                        agg_dict = {'運輸日期': 'count', '合計總板數': 'sum', '工時': 'mean', '行駛里程': 'mean', '總點數': 'mean'}
                        route_group = df_m.groupby('路線別').agg(agg_dict).reset_index()
                        route_group.rename(columns={'運輸日期': '趟數'}, inplace=True)
                        
                        route_group['效益值(VRP)'] = route_group.apply(calc_chart_vrp, axis=1)
                        route_group['路線別'] = pd.Categorical(route_group['路線別'], categories=ROUTE_ORDER, ordered=True)
                        route_group = route_group.sort_values('路線別')
                        
                        display_r_cols = ['路線別', '趟數', '合計總板數', '平均點數', '平均工時', '平均里程', '效益值(VRP)']
                        st.dataframe(route_group[display_r_cols].style.format({
                            "合計總板數": "{:,.0f}", "平均點數": "{:.1f}", "平均工時": "{:.1f} H", "平均里程": "{:.1f} KM", "效益值(VRP)": "{:d} 分"
                        }), use_container_width=True, hide_index=True)

            else:
                st.error(f"找不到『合計總板數』相關欄位。目前抓到的標題為：{headers}")
        else:
            st.info("💡 試算表已連結。目前資料庫為空，請輸入第一筆紀錄。")

except Exception as e:
    st.error(f"系統異常：{e}")
