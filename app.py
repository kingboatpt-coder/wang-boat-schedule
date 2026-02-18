import streamlit as st
import pandas as pd
from datetime import date, datetime
import calendar
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import CellNotFound # 確保引入這個錯誤類型

# --- 1. 頁面設定 ---
st.set_page_config(page_title="王船文化館排班系統", page_icon="🚢", layout="wide")

# --- 2. 連接 Google Sheets 資料庫 ---
@st.cache_resource
def init_connection():
    if "textkey" not in st.secrets:
        st.error("❌ 錯誤：找不到 Secrets 設定。")
        st.stop()
    
    key_dict = st.secrets["textkey"]
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    client = gspread.authorize(creds)
    return client

# 讀取資料
def load_data():
    try:
        client = init_connection()
        sheet = client.open("volunteer_db").sheet1 
        # 這裡會讀取所有資料，如果第一行沒有 key/value，可能會回傳空
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        booking_dict = {}
        # 寬容模式：只要 DataFrame 不為空，就試著轉換
        if not df.empty:
            # 強制將欄位名稱轉小寫以防萬一
            df.columns = [c.lower() for c in df.columns]
            if "key" in df.columns and "value" in df.columns:
                for index, row in df.iterrows():
                    booking_dict[str(row["key"])] = str(row["value"])
        return booking_dict
    except Exception as e:
        # 這裡不顯示錯誤，避免干擾畫面，回傳空字典即可
        print(f"Read Error: {e}")
        return {}

# 儲存資料 (除錯強化版)
def save_data(key, value):
    try:
        client = init_connection()
        sheet = client.open("volunteer_db").sheet1
        
        # 嘗試尋找該 Key 是否存在
        try:
            cell = sheet.find(key)
            # 找到就更新 (第2欄)
            sheet.update_cell(cell.row, 2, value)
        except CellNotFound:
            # 沒找到就新增一行
            sheet.append_row([key, value])
            
    except Exception as e:
        # ⚠️ 這裡會直接把錯誤噴在畫面上，讓我們知道發生什麼事
        st.error(f"❌ 存檔失敗 (Critical Error): {e}")

# 初始化 Session State
if 'bookings' not in st.session_state:
    st.session_state.bookings = load_data()

# 更新時間戳記
if 'last_updated' not in st.session_state:
    st.session_state.last_updated = datetime.now().strftime("%H:%M:%S")

# --- 3. 參數與初始化 ---
ZONES = ["1F-沉浸室劇場", "1F-手扶梯驗票", "2F展區、特展", "3F-展區", "4F-展區", "5F-閱讀區"]
ADMIN_PASSWORD = "1234"
MAX_SLOTS = 2

if 'announcement' not in st.session_state:
    st.session_state.announcement = "歡迎！請點擊上方分頁切換月份進行登記。"
if 'closed_days' not in st.session_state:
    st.session_state.closed_days = []
if 'open_days' not in st.session_state:
    st.session_state.open_days = []
if 'selected_date' not in st.session_state:
    st.session_state.selected_date = None
if 'open_months_list' not in st.session_state:
    st.session_state.open_months_list = [(2026, 3)]

# --- 4. 側邊欄 ---
with st.sidebar:
    st.header("🚢 功能選單")
    st.caption(f"上次更新: {st.session_state.last_updated}")
    
    # 手動更新按鈕
    if st.button("🔄 強制同步資料", type="primary"):
        st.cache_resource.clear()
        new_data = load_data()
        st.session_state.bookings = new_data
        # 強制更新輸入框狀態
        for db_key, db_val in new_data.items():
            st.session_state[f"in_{db_key}"] = db_val
            
        st.session_state.last_updated = datetime.now().strftime("%H:%M:%S")
        st.toast("✅ 資料已同步")
        st.rerun()

    st.divider()
    
    st.header("⚙️ 管理員後台")
    password = st.text_input("輸入密碼登入", type="password")
    if password == ADMIN_PASSWORD:
        st.success("✅ 已登入")
        
        # 測試連線按鈕 (新增)
        if st.button("🧪 測試 Google Sheet 連線"):
            try:
                client = init_connection()
                sheet = client.open("volunteer_db").sheet1
                st.write(f"連線成功！目前試算表有 {len(sheet.get_all_values())} 行資料。")
                st.write(f"標題欄: {sheet.row_values(1)}")
            except Exception as e:
                st.error(f"連線失敗: {e}")

        with st.expander("📅 管理開放月份"):
            current_list = sorted(st.session_state.open_months_list)
            if not current_list: st.warning("未開放月份")
            else: st.write("、".join([f"{y}年{m}月" for y, m in current_list]))
            
            c1, c2, c3 = st.columns([2,2,2])
            add_y = c1.number_input("年", 2025, 2030, 2026)
            add_m = c2.selectbox("月", range(1,13), 2)
            if c3.button("➕ 新增"):
                target = (add_y, add_m)
                if target not in st.session_state.open_months_list:
                    st.session_state.open_months_list.append(target)
                    st.rerun()

            opts = [f"{y}年{m}月" for y, m in current_list]
            rm_sel = st.multiselect("刪除月份", opts)
            if st.button("🗑️ 刪除"):
                for s in rm_sel:
                    y, m = s.replace("月","").split("年")
                    if (int(y), int(m)) in st.session_state.open_months_list:
                        st.session_state.open_months_list.remove((int(y), int(m)))
                st.rerun()

        with st.expander("⛔ 休館設定"):
            d_input = st.date_input("日期", min_value=date(2025,1,1))
            c1, c2 = st.columns(2)
            if c1.button("休館 ❌"):
                if d_input in st.session_state.open_days: st.session_state.open_days.remove(d_input)
                st.session_state.closed_days.append(d_input)
                st.rerun()
            if c2.button("開館 🟢"):
                if d_input in st.session_state.closed_days: st.session_state.closed_days.remove(d_input)
                st.session_state.open_days.append(d_input)
                st.rerun()
                
        with st.expander("📢 公告"):
            ann = st.text_area("內容", st.session_state.announcement)
            if st.button("更新"): 
                st.session_state.announcement = ann
                st.rerun()
        
        st.divider()
        if st.button("💾 下載最新資料"):
            latest_data = load_data()
            data_list = []
            for k, v in latest_data.items():
                if v.strip():
                    parts = k.split("_")
                    if len(parts) >= 4:
                        data_list.append({"日期": parts[0], "時段": parts[1], "區域": parts[2], "志工": v})
            if data_list:
                st.download_button("下載 CSV", pd.DataFrame(data_list).to_csv(index=False), "schedule.csv", "text/csv")
            else:
                st.warning("目前沒有資料可下載")

# --- 5. 主畫面 ---
st.title("🚢 王船文化館 - 志工排班")
st.info(st.session_state.announcement)

sorted_months = sorted(st.session_state.open_months_list)
if not sorted_months:
    st.warning("⚠️ 暫無開放月份")
else:
    tabs = st.tabs([f"{y}年 {m}月" for y, m in sorted_months])
    
    def render_cal(year, month, ctr):
        with ctr:
            cols = st.columns(7)
            for i, n in enumerate(["週一","週二","週三","週四","週五","週六","週日"]):
                cols[i].markdown(f"<div style='text-align:center;color:#666;'>{n}</div>", unsafe_allow_html=True)
            st.write("---")
            for week in calendar.monthcalendar(year, month):
                cols = st.columns(7)
                for i, d in enumerate(week):
                    with cols[i]:
                        if d != 0:
                            curr = date(year, month, d)
                            status = "open"
                            if curr in st.session_state.closed_days: status = "closed"
                            elif curr in st.session_state.open_days: status = "open"
                            elif i == 0: status = "closed"
                            
                            if status == "closed":
                                st.markdown(f"<div style='background:#f0f0f0;color:#aaa;text-align:center;padding:10px;'>{d}<br><small>休</small></div>", unsafe_allow_html=True)
                            else:
                                is_sel = (st.session_state.selected_date == curr)
                                if st.button(f"{d}", key=f"b_{year}_{month}_{d}", type="primary" if is_sel else "secondary", use_container_width=True):
                                    st.session_state.selected_date = curr
                                    st.rerun()

    for i, (yy, mm) in enumerate(sorted_months):
        render_cal(yy, mm, tabs[i])

    if st.session_state.selected_date and (st.session_state.selected_date.year, st.session_state.selected_date.month) in sorted_months:
        d = st.session_state.selected_date
        st.divider()
        st.subheader(f"✍️ {d.strftime('%Y-%m-%d')}")
        
        t1, t2 = st.tabs(["🌞 上午", "🌤️ 下午"])
        
        def render_form(shift, ctr):
            with ctr:
                for z in ZONES:
                    st.markdown(f"**📍 {z}**")
                    cc = st.columns(MAX_SLOTS)
                    for k in range(MAX_SLOTS):
                        key = f"{d.strftime('%Y-%m-%d')}_{shift}_{z}_{k+1}"
                        val = st.session_state.bookings.get(key, "")
                        
                        with cc[k]:
                            # on_change 沒有設，改用檢查值變更
                            widget_key = f"in_{key}"
                            nv = st.text_input(f"志工{k+1}", val, key=widget_key, label_visibility="collapsed")
                            if nv != val:
                                st.session_state.bookings[key] = nv
                                save_data(key, nv) # 這裡如果失敗會跳紅字
                                st.toast(f"已儲存：{nv}")
                    st.divider()
        render_form("上午", t1)
        render_form("下午", t2)
