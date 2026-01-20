import streamlit as st
import gspread
import pandas as pd
import json
from datetime import datetime, date
from google.oauth2.service_account import Credentials

# --- 1. 頁面設定 ---
st.set_page_config(page_title="運輸日報表 Pro", page_icon="🚚", layout="wide")
st.title("🚚 運輸日報表 Pro")

# --- 2. 連線設定 ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

try:
    with open("service_account.json", "r", encoding="utf-8") as f:
        key_dict = json.load(f)
    
    creds = Credentials.from_service_account_info(key_dict, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open("Transport_System_2026").worksheet("data")
    
except Exception as e:
    st.error(f"❌ 連線錯誤：{e}")
    st.stop()

# --- 3. 核心功能函式 ---
def save_data(data):
    try:
        sheet.append_row(data)
        return True
    except Exception as e:
        st.error(f"寫入失敗: {e}")
        return False

def load_data():
    try:
        all_records = sheet.get_all_records()
        return pd.DataFrame(all_records)
    except Exception as e:
        return None

# --- 4. 輸入區 (這裡加上了 clear_on_submit=True 自動清空功能) ---
with st.form("entry_form", clear_on_submit=True):
    
    st.subheader("👤 駕駛與日期")
    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
    with col_d1:
        driver_name = st.selectbox("駕駛姓名", ["胡英季"])
    with col_d2:
        input_date = st.date_input("配送日期", date.today())
    with col_d3:
        time_options = ["03:30", "04:00", "04:30", "05:00", "05:30", "06:00", "06:30", "07:00", "07:30", "08:00"]
        start_time = st.selectbox("上班時間", time_options)
    with col_d4:
        end_time = st.time_input("下班時間", datetime.now().time())

    st.markdown("---")

    st.subheader("🚚 里程與明細")
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        # 修改點：min_value=0 (整數), step=1 (每次跳1), format="%d" (只顯示整數)
        m_start = st.number_input("里程起", min_value=0, step=1, value=None, placeholder="輸入起數...", format="%d")
    with col_m2:
        m_end = st.number_input("里程迄", min_value=0, step=1, value=None, placeholder="輸入迄數...", format="%d")
    with col_m3:
        # 即時顯示預估里程
        s = m_start if m_start is not None else 0
        e = m_end if m_end is not None else 0
        dist = e - s if (e >= s and e > 0) else 0
        st.metric("預估里程", f"{dist} km")

    st.caption("👇 請輸入各客戶板數：")
    
    default_data = {
        "客戶名稱": [f"客戶 {i}" for i in range(1, 11)],
        "送貨板數": [0] * 10,
        "收貨板數": [0] * 10
    }
    
    edited_df = st.data_editor(
        pd.DataFrame(default_data),
        num_rows="fixed",
        hide_index=True,
        use_container_width=True
    )

    total_send = int(edited_df["送貨板數"].sum())
    total_recv = int(edited_df["收貨板數"].sum())
    total_all = total_send + total_recv
    
    st.markdown("---")

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        basket_count = st.number_input("♻️ 空籃回收 (個)", min_value=0, step=1, format="%d")
    with col_b2:
        pallet_empty_count = st.number_input("🪵 空板回收 (個)", min_value=0, step=1, format="%d")

    money_delivery = int(total_all * 40)
    money_basket = int(basket_count / 2)
    money_pallet = int(pallet_empty_count * 3)
    money_total = money_delivery + money_basket + money_pallet

    st.info(f"💰 本趟預估收入： ${money_total}  (板費 ${money_delivery} + 籃獎 ${money_basket} + 板獎 ${money_pallet})")

    submitted = st.form_submit_button("🚀 確認送出", use_container_width=True)

    if submitted:
        if m_start is None or m_end is None:
            st.error("⚠️ 請輸入完整的里程數據！")
        elif m_end < m_start:
            st.error("⚠️ 里程錯誤：迄數不能小於起數")
        else:
            real_km = m_end - m_start
            
            details = []
            for index, row in edited_df.iterrows():
                if row["送貨板數"] > 0 or row["收貨板數"] > 0:
                    details.append(f"{row['客戶名稱']}(送{row['送貨板數']}/收{row['收貨板數']})")
            details_str = " | ".join(details) if details else ""

            row_data = [
                str(input_date), str(start_time), str(end_time),
                m_start, m_end, real_km,
                total_send, total_recv, total_all,
                basket_count, pallet_empty_count, details_str,
                money_delivery,
                money_basket,
                money_pallet,
                money_total
            ]
            
            with st.spinner("資料上傳中..."):
                if save_data(row_data):
                    st.success(f"✅ 資料已上傳！")
                    st.balloons()
                    # 注意：因為開啟了 clear_on_submit，所以表單欄位會自動清空，方便您輸入下一筆

# --- 5. 運量概況儀表板 ---
st.divider()
st.header("📅 本月運量概況")

df = load_data()

if df is not None and not df.empty:
    try:
        df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
        current_month = date.today().month
        current_year = date.today().year
        month_df = df[
            (df['日期'].dt.month == current_month) & 
            (df['日期'].dt.year == current_year)
        ]

        if not month_df.empty:
            numeric_cols = ['實際里程', '合計收送板數', '配送津貼', '空籃獎金', '空板獎金', '當日運量收入', '空籃回收', '空板回收']
            for c in numeric_cols:
                if c in month_df.columns:
                    month_df[c] = pd.to_numeric(month_df[c], errors='coerce').fillna(0)

            sum_km = month_df['實際里程'].sum()
            sum_pallets = month_df['合計收送板數'].sum()
            sum_money = month_df['當日運量收入'].sum() if '當日運量收入' in month_df.columns else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("本月總里程", f"{int(sum_km)} km") # 這裡也改成整數顯示
            c2.metric("本月總板數", f"{int(sum_pallets)} 板")
            c3.metric("本月總獎金", f"${int(sum_money):,}") 

            st.subheader("📝 詳細紀錄")
            
            display_df = month_df.copy()
            display_df['日期'] = display_df['日期'].dt.strftime('%m/%d')
            
            if '配送津貼' in display_df.columns:
                display_df['配送資訊'] = display_df.apply(lambda x: f"{int(x['合計收送板數'])}板 (${int(x['配送津貼'])})", axis=1)
            
            if '空籃獎金' in display_df.columns:
                display_df['空籃資訊'] = display_df.apply(lambda x: f"{int(x['空籃回收'])}個 (${int(x['空籃獎金'])})", axis=1)
                
            if '空板獎金' in display_df.columns:
                display_df['空板資訊'] = display_df.apply(lambda x: f"{int(x['空板回收'])}個 (${int(x['空板獎金'])})", axis=1)

            if '當日運量收入' in display_df.columns:
                display_df['配送獎金'] = display_df['當日運量收入'].apply(lambda x: f"${int(x)}")

            final_cols = ['日期', '上班時間', '實際里程', '配送資訊', '空籃資訊', '空板資訊', '配送獎金']
            available_cols = [c for c in final_cols if c in display_df.columns]
            
            st.dataframe(
                display_df[available_cols], 
                use_container_width=True, 
                hide_index=True
            )

        else:
            st.info("💡 這個月還沒有資料，快去送出第一筆吧！")
    except Exception as e:
        st.warning(f"資料讀取顯示時發生小問題: {e}")
else:
    st.info("尚無資料庫紀錄")