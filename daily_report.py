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
        # 安全取得金鑰
        creds_dict = st.secrets.get("service_account")
        if not creds_dict:
            st.error("找不到金鑰設定 (st.secrets)")
            return None
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        sheet_url = "https://docs.google.com/spreadsheets/d/1VzyglFpEC3yS11aIoU1YJclw-6Moaewyf8DTR-j7HDc/edit?gid=0#gid=0"
        return client.open_by_url(sheet_url).sheet1
    except Exception as e:
        st.error(f"連線失敗: {e}")
        return None

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
                t_stops, d_p, r_p = total_stops or 0, p_del_pallets or 0, p_pick_pallets or 0
                baskets, empty_p = p_baskets or 0, p_empty_pallets or 0
                total_p = d_p + r_p
                mileage_diff = end_mileage - start_mileage
                row_data = [str(date), start_time, end_time, route, start_mileage, end_mileage, mileage_diff, t_stops, d_p, r_p, total_p, baskets, empty_p]
                sheet.append_row(row_data)
                st.success(f"✅ 成功寫入！本趟 {route} 共 {total_p} 板。")
                time.sleep(1.5)
                st.rerun()

    # ==========================================
    # 🟡 數據讀取與清洗
    # ==========================================
    try:
        all_raw = sheet.get_all_values()
        actual_data = [row for row in all_raw if any(str(cell).strip() for cell in row)]
        
        if len(actual_data) > 1:
            headers = [str(h).strip() for h in actual_data[0]]
            df_all = pd.DataFrame(actual_data[1:], columns=headers)
            
            # 轉換數值欄位，避免 KeyError 或運算錯誤
            df_all['年份'] = df_all['運輸日期'].astype(str).str[:4]
            df_all['月份'] = df_all['運輸日期'].astype(str).str[:7]
            num_cols = ['行駛里程', '合計總板數', '空籃數', '空板數', '總點數', '配送板數', '收貨板數']
            for col in num_cols:
                if col in df_all.columns:
                    df_all[col] = pd.to_numeric(df_all[col].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
            
            df_all['工時'] = df_all.apply(lambda row: calculate_work_hours(row.get('上班時間','00:00'), row.get('下班時間','00:00')), axis=1)

            st.write("---")
            st.subheader("📊 營運數據分析與指標")
            
            # ==========================================
            # 🟡 第二階段：營運圖表區
            # ==========================================
            c_chart1, c_chart2 = st.columns(2)
            with c_chart1:
                st.caption("🏆 年度每月總板數趨勢")
                month_stats = df_all.groupby('月份')['合計總板數'].sum()
                st.bar_chart(month_stats)
            
            with c_chart2:
                st.caption("🎯 當月各路線效益指標 (VRP基準)")
                current_m = datetime.today().strftime('%Y-%m')
                df_cm = df_all[df_all['月份'] == current_m]
                if not df_cm.empty:
                    route_eff = df_cm.groupby('路線別').agg({'合計總板數':'mean','總點數':'mean','工時':'mean','行駛里程':'mean'}).reset_index()
                    # 效益值公式：基準 100分
                    route_eff['效益值'] = route_eff.apply(lambda r: round((r['合計總板數']/50)*(5/(r['總點數'] or 1))*(10/(r['工時'] or 1))*(100/(r['行駛里程'] or 1))*100, 1), axis=1)
                    st.bar_chart(route_eff.set_index('路線別')['效益值'])
                else:
                    st.info("當月尚無資料")

            # ==========================================
            # 🔴 第三階段：明細展開區 (年度總表 + 每月明細)
            # ==========================================
            st.write("---")
            st.subheader("📋 營運報表明細")
            
            # 1. 年度總表 (1-12月彙整)
            current_year = datetime.today().strftime('%Y')
            with st.expander(f"🗓️ {current_year} 年度營運總結報告", expanded=False):
                df_y = df_all[df_all['年份'] == current_year].copy()
                if not df_y.empty:
                    y_sum = df_y.groupby('月份').agg({'合計總板數':'sum', '空籃數':'sum', '空板數':'sum', '行駛里程':'sum', '運輸日期':'count'}).reset_index()
                    y_sum.columns = ['月份', '總板數', '總空籃', '總空板', '總里程', '趟數']
                    
                    def calc_y_bonus(row):
                        base = (row['總板數']*40) + (row['總空籃']*0.5) + (row['總空板']*3)
                        multi = 1.2 if row['總板數']>=501 else (1.1 if row['總板數']>=451 else 1.0)
                        return int(base * multi)
                    
                    y_sum['預估獎金'] = y_sum.apply(calc_y_bonus, axis=1)
                    st.dataframe(y_sum.style.format({"預估獎金":"${:,}", "總板數":"{:,.0f}"}), use_container_width=True, hide_index=True)
                else:
                    st.write("尚無年度數據")

            # 2. 月度明細 (恢復原本的每月展開式)
            unique_months = sorted([m for m in df_all['月份'].unique() if m != 'Unknown'], reverse=True)
            for month in unique_months:
                is_this_month = (month == datetime.today().strftime('%Y-%m'))
                with st.expander(f"📅 {month} 報表細節", expanded=is_this_month):
                    df_m = df_all[df_all['月份'] == month].copy()
                    
                    # 獎金計算
                    m_tp = df_m['合計總板數'].sum()
                    m_b, m_e = df_m['空籃數'].sum(), df_m['空板數'].sum()
                    base_b = (m_tp * 40) + (m_b * 0.5) + (m_e * 3)
                    multi = 1.2 if m_tp >= 501 else (1.1 if m_tp >= 451 else 1.0)
                    
                    st.success(f"💰 **{month} 預估總獎金：${int(base_b * multi):,}** (總板數: {int(m_tp)} / 階梯: {multi}倍)")
                    
                    # 路線指標表格
                    rg = df_m.groupby('路線別').agg({'運輸日期':'count', '合計總板數':'sum', '配送板數':'sum', '收貨板數':'sum', '總點數':'mean', '工時':'mean', '行駛里程':'mean'}).reset_index()
                    rg.columns = ['路線別', '趟數', '總板數', '總配板', '總收板', '平均點數', '平均工時', '平均里程']
                    
                    # 佔比計算
                    rg['收送佔比'] = rg.apply(lambda r: f"送{int(r['總配板']/(r['總配板']+r['總收板'])*100)}% / 收{100-int(r['總配板']/(r['總配板']+r['總收板'])*100)}%" if (r['總配板']+r['總收板'])>0 else "0/0", axis=1)
                    rg['滿載率(%)'] = (rg['總板數'] / (rg['趟數'] * 28)) * 100
                    # 效益值
                    rg['效益值'] = rg.apply(lambda r: round(((r['總板數']/r['趟數'])/50)*(5/(r['平均點數'] or 1))*(10/(r['平均工時'] or 1))*(100/(r['平均里程'] or 1))*100, 1), axis=1)
                    
                    st.dataframe(rg[['路線別', '趟數', '總板數', '收送佔比', '滿載率(%)', '平均里程', '效益值']].style.format({"滿載率(%)":"{:.1f}%"}), use_container_width=True, hide_index=True)

        else:
            st.error("找不到欄位標題，請確認試算表格式。")
    except Exception as e:
        st.error(f"數據處理異常: {e}")
else:
    st.info("💡 試算表已連結。目前資料庫為空。")
