# 設定權限範圍
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# 判斷是在雲端 (Streamlit Cloud) 還是本機 (Local)
if "gcp_service_account" in st.secrets:
    # 如果在雲端，從 Secrets 讀取鑰匙
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
else:
    # 如果在本機，讀取檔案
    creds = Credentials.from_service_account_file("service_account.json", scopes=scopes)

# 連接 Google Sheets
client = gspread.authorize(creds)