# --- 底部統計區 (加強日期比對與錯誤排除) ---
st.divider()
if st.button("📊 查看今日填報統計 (點擊載入)"):
    with st.spinner('正在從雲端抓取最新數據...'):
        try:
            # 重新強制連線抓取，不使用緩存
            scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
            client = gspread.authorize(creds)
            temp_df = pd.DataFrame(client.open("Transport_System_2026").get_worksheet(0).get_all_records())
            
            if not temp_df.empty:
                # 統一日期格式進行比對 (不管 Excel 裡是 - 還是 /)
                today_str = datetime.now().strftime("%Y-%m-%d")
                temp_df['日期'] = temp_df['日期'].astype(str).replace('/', '-', regex=True)
                
                # 過濾出今天的資料
                today_data = temp_df[temp_df['日期'].str.contains(today_str)]
                
                if not today_data.empty:
                    # 顯示統計卡片
                    st.success(f"✅ 已找到今日 {len(today_data)} 筆紀錄")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("今日趟數", len(today_data))
                    
                    # 檢查欄位是否存在並計算
                    if '實際里程' in today_data.columns:
                        c2.metric("總里程", f"{pd.to_numeric(today_data['實際里程']).sum()} km")
                    if '合計收送板數' in today_data.columns:
                        c3.metric("總板數", f"{pd.to_numeric(today_data['合計收送板數']).sum()} 板")
                    
                    # 顯示簡化報表供確認
                    st.write("🔍 最近填報明細：")
                    show_cols = [c for c in ['司機', '路線別', '實際里程', '合計收送板數'] if c in today_data.columns]
                    st.dataframe(today_data[show_cols].tail(5), use_container_width=True, hide_index=True)
                else:
                    st.warning(f"查無今日 ({today_str}) 資料，請確認試算表日期格格式。")
            else:
                st.info("試算表目前是空的。")
        except Exception as e:
            st.error(f"讀取失敗：{e} (這通常是 API 頻繁讀取限制，請等一分鐘後再試)")
