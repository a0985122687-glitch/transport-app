# --- 終極版統計區 (補齊明細顯示) ---
st.divider()
if st.button("📊 查看當月獎金與統計 (點擊載入)"):
    with st.spinner('正在核算獎金與明細...'):
        try:
            _, df = get_sheet_and_data()
            if not df.empty:
                df['日期'] = df['日期'].astype(str).str.replace('/', '-', regex=True)
                this_month = datetime.now().strftime("%Y-%m")
                month_data = df[df['日期'].str.contains(this_month)].copy()
                
                if not month_data.empty:
                    # 強制數字化處理
                    for c in ['實際里程', '合計收送板數', '空籃回收', '空板回收']:
                        if c in month_data.columns:
                            month_data[c] = pd.to_numeric(month_data[c], errors='coerce').fillna(0)

                    # 獎金計算 (1元/2元)
                    month_data['空籃獎金'] = month_data['空籃回收'] * 1
                    month_data['空板獎金'] = month_data['空板回收'] * 2
                    month_data['合計獎金'] = month_data['空籃獎金'] + month_data['空板獎金']

                    # 頂部儀表板
                    st.subheader(f"📅 {this_month} 累計概況")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("當月趟數", f"{len(month_data)} 趟")
                    c2.metric("當月總里程", f"{int(month_data['實際里程'].sum())} km")
                    c3.metric("累計總板數", f"{int(month_data['合計收送板數'].sum())} 板")

                    st.success(f"💰 當月預估獎金合計：{int(month_data['合計獎金'].sum())} 元")

                    # 下方明細表格 (補上空籃與空板獎金欄位)
                    st.write("📋 詳細統計明細：")
                    # 這裡是關鍵：將 '空籃獎金', '空板獎金' 加入顯示清單
                    cols_to_show = ['日期', '司機', '路線別', '實際里程', '空籃獎金', '空板獎金', '合計獎金']
                    # 確保這些欄位在 DataFrame 中都存在
                    existing_cols = [c for c in cols_to_show if c in month_data.columns]
                    st.dataframe(month_data[existing_cols].tail(10), use_container_width=True, hide_index=True)
                else:
                    st.warning("本月尚無紀錄。")
        except Exception as e:
            st.error(f"核算失敗：{e}")
