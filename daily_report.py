import streamlit as st
import gspread
# ... (前面的 import 維持不變) ...

# 1. 頁面配置
st.set_page_config(page_title="運輸管理系統", page_icon="🚚", layout="centered")

# --- 核心美化指令：隱藏右上貓咪與右下標誌 ---
st.markdown("""
    <style>
    /* 1. 隱藏右上角的 GitHub 貓咪與選單按鈕 */
    header {visibility: hidden;}
    
    /* 2. 隱藏右下角的 Streamlit 選單按鈕 (大紅色或藍色的那個) */
    .stDeployButton {display:none;}
    #MainMenu {visibility: hidden;}
    
    /* 3. 隱藏頁尾文字 (Made with Streamlit) */
    footer {visibility: hidden;}
    
    /* 4. 移除頂部多餘的空白，讓填報區塊上移 */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📝 運輸日報表")
# ... (後面的填報與獎金統計程式碼維持不變) ...
