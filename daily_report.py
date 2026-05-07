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
try:
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
                    sheet.append_row(row_data)
                    st.success("✅ 儲存成功！"); time.sleep(1); st.rerun()

        # ==========================================
        # 資料處理與第三階段優化
        # ==========================================
        all_raw = sheet.get_all_values()
        if len(all_raw) > 1:
            df = pd.DataFrame(all_raw[1:], columns=[h.strip() for h in all_raw[0]])
            df['年份'], df['月份'] = df['運輸日期'].astype(str).str[:4], df['運輸日期'].apply(extract_month)
            num_cols = ['行駛里程', '合計總板數', '空籃數', '空板數', '總點數', '配送板數', '收貨板數']
            for col in num_cols: df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            df['工時'] = df.apply(lambda r: calculate_work_hours(r.get('上班時間','0'), r.get('下班時間','0')), axis=1)

            st.write("---")
            st.subheader("📋 營運報表明細")

            unique_months = sorted([m for m in df['月份'].unique() if m != 'Unknown'], reverse=True)
            for month in unique_months:
                with st.expander(f"📅 {month} 報表細節", expanded=(month == datetime.today().strftime('%Y-%m'))):
                    df_m = df[df['月份'] == month].copy()
                    
                    # 獎金橫幅
                    m_tp, m_b, m_e = df_m['合計總板數'].sum(), df_m['空籃數'].sum(), df_m['空板數'].sum()
                    multi = 1.2 if m_tp >= 501 else (1.1 if m_tp >= 451 else 1.0)
                    st.success(f"💰 預估獎金：${int((m_tp*40*multi)+(m_b*0.5)+(m_e*3)):,} (板數:{int(m_tp)} / {multi}倍)")

                    # 路線彙整計算
                    rg = df_m.groupby('路線別').agg({'運輸日期':'count', '合計總板數':'sum', '總點數':'mean', '工時':'mean', '行駛里程':'mean', '配送板數':'sum', '收貨板數':'sum'}).reset_index()
                    rg.columns = ['路線別', '趟數', '總板數', '平均點數', '平均工時', '平均里程', '配板', '收板']
                    
                    # 100% 對齊 Excel 效益值公式
                    def calc_vrp_final(r):
                        p = r['總板數'] / r['趟數']
                        s, h, m = r['平均點數'] or 1, r['平均工時'] or 1, r['平均里程'] or 1
                        # 邏輯: 100 * (實際效益 / 基準效益) -> 基準效益 = 50/(5*100*10) = 0.01
                        score = 100 * (p / (s * m * h)) / 0.01
                        return int(min(100, round(score, 0)))

                    rg['效益值(VRP)'] = rg.apply(calc_vrp_final, axis=1)
                    rg['滿載率%'] = (rg['總板數'] / (rg['趟數'] * 28)) * 100
                    rg['收送佔比'] = rg.apply(lambda r: f"{int(r['配板']/(r['配板']+r['收板'])*100)}%/{100-int(r['配板']/(r['配板']+r['收板'])*100)}%" if (r['配板']+r['收板'])>0 else "0/0", axis=1)
                    
                    # 排序並整理
                    rg['路線別'] = pd.Categorical(rg['路線別'], categories=ROUTE_ORDER, ordered=True)
                    rg = rg.sort_values('路線別').reset_index(drop=True)
                    
                    # 新增「平均值」列
                    avg_row = pd.DataFrame([{
                        '路線別': '【全月平均】',
                        '趟數': rg['趟數'].sum(),
                        '總板數': rg['總板數'].mean(),
                        '平均點數': rg['平均點數'].mean(),
                        '平均工時': rg['平均工時'].mean(),
                        '平均里程': rg['平均里程'].mean(),
                        '效益值(VRP)': rg['效益值(VRP)'].mean(),
                        '滿載率%': rg['滿載率%'].mean(),
                        '收送佔比': '-'
                    }])
                    final_table = pd.concat([rg, avg_row], ignore_index=True)

                    st.dataframe(final_table[['路線別', '趟數', '總板數', '平均點數', '平均工時', '平均里程', '收送佔比', '滿載率%', '效益值(VRP)']].style.format({
                        "總板數": "{:.0f}", "平均點數": "{:.1f}", "平均工時": "{:.1f}H", "平均里程": "{:.1f}K", "滿載率%": "{:.1f}%", "效益值(VRP)": "{:.0f}分"
                    }), use_container_width=True, hide_index=True)

    else: st.info("資料庫連線中...")
except Exception as e: st.error(f"系統異常：{e}")
