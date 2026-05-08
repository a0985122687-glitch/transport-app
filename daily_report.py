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
# 🟢 第一階段：輸入區塊 (維持原狀)
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
                except: st.error("⚠️ 儲存失敗。")

    # ==========================================
    # 🔴 資料處理與第三階段優化
    # ==========================================
    try:
        all_raw = sheet.get_all_values()
        if len(all_raw) > 1:
            headers = [str(h).replace(' ', '').strip() for h in all_raw[0]]
            df = pd.DataFrame(all_raw[1:], columns=headers)
            
            # 欄位容錯
            rename_map = {'日期': '運輸日期', '合計': '合計總板數', '總板數': '合計總板數', '里程數': '行駛里程', '點數': '總點數'}
            df.rename(columns=rename_map, inplace=True)
            
            core_cols = ['行駛里程', '合計總板數', '空籃數', '空板數', '總點數', '配送板數', '收貨板數']
            for c in core_cols:
                if c not in df.columns: df[c] = 0
                df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

            df['月份'] = df['運輸日期'].apply(extract_month)
            df['工時'] = df.apply(lambda r: calculate_work_hours(r.get('上班時間','0'), r.get('下班時間','0')), axis=1)

            st.write("---")
            st.subheader("📋 營運報表明細與效益分析")

            # --- 1. 年度總表 (依要求對調順序與欄位) ---
            current_year = datetime.today().strftime('%Y')
            with st.expander(f"🗓️ {current_year} 年度營運總結報告", expanded=False):
                df_y = df[df['運輸日期'].astype(str).str.contains(current_year)].copy()
                if not df_y.empty:
                    y_sum = df_y.groupby('月份').agg({'合計總板數':'sum', '空籃數':'sum', '空板數':'sum', '運輸日期':'count'}).reset_index()
                    y_sum.rename(columns={'運輸日期': '總趟次', '合計總板數': '月總板數(40元)', '空籃數': '月總空籃(0.5元)', '空板數': '月總空板(3元)'}, inplace=True)
                    y_sum['趟次平均板數'] = (y_sum['月總板數(40元)'] / y_sum['總趟次']).round(1)
                    
                    def calc_y_bonus(row):
                        multi = 1.2 if row['月總板數(40元)'] >= 501 else (1.1 if row['月總板數(40元)'] >= 451 else 1.0)
                        return int((row['月總板數(40元)'] * 40 * multi) + (row['月總空籃(0.5元)'] * 0.5) + (row['月總空板(3元)'] * 3))
                    
                    y_sum['預估總獎金'] = y_sum.apply(calc_y_bonus, axis=1)
                    # 重新排列：總趟次移前，平均板數移後
                    display_y = ['月份', '月總板數(40元)', '月總空籃(0.5元)', '月總空板(3元)', '總趟次', '趟次平均板數', '預估總獎金']
                    st.dataframe(y_sum[display_y].style.format({"預估總獎金":"${:,}"}), use_container_width=True, hide_index=True)

            # --- 2. 月度展開 (含每日明細與彙整) ---
            unique_months = sorted([m for m in df['月份'].unique() if m != 'Unknown'], reverse=True)
            for month in unique_months:
                with st.expander(f"📅 {month} 報表細節", expanded=(month == datetime.today().strftime('%Y-%m'))):
                    df_m = df[df['月份'] == month].copy()
                    
                    # 每日紀錄表格
                    st.markdown("##### 📝 當月每日出勤明細")
                    st.dataframe(df_m[['運輸日期', '路線別', '行駛里程', '總點數', '合計總板數', '工時']].sort_values('運輸日期'), use_container_width=True, hide_index=True)

                    # 路線彙整表
                    st.markdown("##### 📊 路線彙整與相對效能分析")
                    agg_cols = {'運輸日期':'count', '合計總板數':'sum', '總點數':'mean', '工時':'mean', '行駛里程':'mean', '配送板數':'sum', '收貨板數':'sum'}
                    rg = df_m.groupby('路線別').agg(agg_cols).reset_index()
                    rg.columns = ['路線別', '趟數', '總板數', '平均點數', '平均工時', '平均里程', '配', '收']
                    
                    # 箭頭佔比邏輯
                    def get_ratio_arrow(r):
                        total = r['配'] + r['收']
                        if total == 0: return "0%/0% ➖"
                        p_pct, r_pct = int(r['配']/total*100), 100-int(r['配']/total*100)
                        arrow = "🔼" if p_pct > r_pct else ("🔽" if r_pct > p_pct else "➖")
                        return f"送{p_pct}%/收{r_pct}% {arrow}"
                    
                    rg['收送佔比'] = rg.apply(get_ratio_arrow, axis=1)
                    rg['滿載率%'] = (rg['總板數'] / (rg['趟數'] * 28)) * 100
                    
                    # 相對效能指標 (放大基數以便觀察對比)
                    rg['效能指標'] = rg.apply(lambda r: round(((r['總板數']/r['趟數'])/( (r['平均點數'] or 1)*(r['平均里程'] or 1)*(r['平均工時'] or 1) )) * 10000, 1), axis=1)
                    
                    rg['路線別'] = pd.Categorical(rg['路線別'], categories=ROUTE_ORDER, ordered=True)
                    rg = rg.sort_values('路線別').reset_index(drop=True)
                    
                    # 全月統計列
                    avg_row = pd.DataFrame([{
                        '路線別': '【全月總計/平均】', '趟數': rg['趟數'].sum(), '總板數': rg['總板數'].sum(),
                        '平均點數': rg['平均點數'].mean(), '平均工時': rg['平均工時'].mean(), '平均里程': rg['平均里程'].mean(),
                        '收送佔比': '-', '滿載率%': rg['滿載率%'].mean(), '效能指標': rg['效能指標'].mean()
                    }])
                    st.dataframe(pd.concat([rg, avg_row], ignore_index=True)[['路線別', '趟數', '總板數', '平均點數', '平均工時', '平均里程', '收送佔比', '滿載率%', '效能指標']].style.format({"滿載率%":"{:.1f}%"}), use_container_width=True, hide_index=True)

    except Exception as e: st.error(f"系統異常：{e}")
