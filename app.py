import streamlit as st
import pandas as pd
from datetime import date, datetime
import calendar
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. 頁面設定 ---
st.set_page_config(page_title="王船文化館排班系統", page_icon="🚢", layout="wide")

# ==========================================
# 🌟 [新增 CSS 魔法] 強制手機顯示 7 格日曆模式
# ==========================================
st.markdown("""
<style>
@media (max-width: 576px) {
    /* 1. 找到剛好有 7 個欄位（日曆）的區塊，強制橫向排列 */
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) {
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        overflow-x: hidden !important;
    }
    /* 2. 把每個格子硬性規定佔據 1/7 (約 14.28%) 的寬度，並消除多餘留白 */
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) > div[data-testid="column"] {
        width: 14.28% !important;
        flex: 1 1 14.28% !important;
        min-width: 0 !important;
        padding: 1px !important;
    }
    /* 3. 縮小日曆按鈕的字體與高度，避免手機上破版 */
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) button {
        padding: 5px 0px !important;
        font-size: 14px !important;
        min-height: 40px !important;
    }
    /* 4. 縮小「休館」、「特休」等文字標籤 */
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) div {
        font-size: 12px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) small {
        font-size: 10px !important;
    }
}
</style>
""", unsafe_allow_html=True)
# ==========================================

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
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        booking_dict = {}
        if not df.empty:
            df.columns = [str(c).lower() for c in df.columns]
            if "key" in df.columns and "value" in df.columns:
                for index, row in df.iterrows():
                    booking_dict[str(row["key"])] = str(row["value"])
        return booking_dict
    except Exception as e:
        return {}

# 儲存資料
def save_data(key, value):
    try:
        client = init_connection()
        sheet = client.open("volunteer_db").sheet1
        try:
            cell = sheet.find(key)
            sheet.update_cell(cell.row, 2, value)
        except:
            sheet.append_row([key, value])
    except Exception as e:
        st.error(f"❌ 存檔失敗: {e}")

# 初始化 Session State
if 'bookings' not in st.session_state:
    st.session_state.bookings = load_data()

if 'last_updated' not in st.session_state:
    st.session_state.last_updated = datetime.now().strftime("%H:%M:%S")

# --- 3. 參數與初始化 ---
ZONES = ["1F-沉浸室劇場", "1F-手扶梯驗票", "2F展區、特展", "3F-展區", "4F-展區", "5F-閱讀區"]
ADMIN_PASSWORD = "1234"  # ⚠️ 記得把這裡改成您自己的專屬密碼！
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
    
    if st.button("🔄 強制同步資料", type="primary"):
        st.cache_resource.clear()
        new_data = load_data()
        st.session_state.bookings = new_data
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
        
        if st.button("🧪 測試 Google Sheet 連線"):
            try:
                client = init_connection()
                sheet = client.open("volunteer_db").sheet1
                st.success(f"連線成功！讀取到 {len(sheet.get_all_values())} 行資料。")
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
                st.download_button("下載 CSV", pd.DataFrame(data_list).to_csv(index=False, encoding="utf_8_sig"), "schedule.csv", "text/csv")
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
                # 給星期標題加上一點樣式，確保手機上也置中
                cols[i].markdown(f"<div style='text-align:center;color:#666;font-size:12px;font-weight:bold;'>{n}</div>", unsafe_allow_html=True)
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
                                st.markdown(f"<div style='background:#f0f0f0;color:#aaa;text-align:center;padding:5px 0px;border-radius:4px;'><strong>{d}</strong><br><small>休</small></div>", unsafe_allow_html=True)
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
                            widget_key = f"in_{key}"
                            nv = st.text_input(f"志工{k+1}", val, key=widget_key, label_visibility="collapsed")
                            if nv != val:
                                st.session_state.bookings[key] = nv
                                save_data(key, nv)
                                st.toast(f"✅ 已儲存：{nv}")
                    st.divider()
        render_form("上午", t1)
        render_form("下午", t2)
