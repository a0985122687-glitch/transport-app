# 1. 在介面增加司機選擇
driver_name = st.selectbox("👤 選擇填報人", ["請選擇", "司機A", "司機B", "車號001"])

# 2. 修改送出按鈕的內容
if st.button("🚀 確認送出資料", use_container_width=True):
    if driver_name == "請選擇":
        st.error("請先選擇司機姓名！")
    else:
        actual_dist = m_end - m_start
        # 這裡的順序要跟您的 Excel 欄位一模一樣 (假設司機在最後一欄 M)
        new_row = [
            str(input_date), input_time, "", m_start, m_end, 
            actual_dist, p_sent, p_recv, (p_sent + p_recv), 
            basket_back, plate_back, detail_content, input_remark, driver_name
        ]
        sheet.append_row(new_row)
        st.success(f"存檔成功！({driver_name})")
        st.rerun()
