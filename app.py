import streamlit as st
import pandas as pd
from datetime import date, datetime
import calendar
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- 1. 頁面設定 ---
st.set_page_config(page_title="王船文化館排班系統", page_icon="🚢", layout="wide")

# ==========================================
# 🌟 [終極 CSS 魔法] 使用 Grid 網格系統，保證絕對不爆框！
# ==========================================
st.markdown("""
<style>
@media (max-width: 576px) {
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) {
        display: grid !important;
        grid-template-columns: repeat(7, minmax(0, 1fr)) !important;
        gap: 2px !important;
        width: 100% !important;
        padding: 0 !important;
    }
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) > div[data-testid="column"] {
        width: 100% !important;
        min-width: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) button,
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) div[style*="background"] {
        width: 100% !important;
        min-width: 0 !important;
        padding: 4px 0px !important;
        margin: 0 !important;
        box-sizing: border-box !important;
    }
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) button {
        min-height: 38px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) p,
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) strong {
        font-size: 13px !important;
        line-height: 1.1 !important;
    }
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) small {
        font-size: 9px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) div[style*="font-weight:bold"] {
        font-size: 11px !important;
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

# --- 3. 初始化參數與從雲端讀取系統設定 ---
ZONES = ["1F-沉浸室劇場", "1F-手扶梯驗票", "2F展區、特展", "3F-展區", "4F-展區", "5F-閱讀區"]
ADMIN_PASSWORD = "1234"  # ⚠️ 記得把這裡改成您自己的專屬密碼！
MAX_SLOTS = 2

if 'bookings' not in st.session_state:
    raw_data = load_data()
    st.session_state.bookings = raw_data
    
    if "SYS_OPEN_MONTHS" in raw_data:
        try: 
            loaded_m = json.loads(raw_data["SYS_OPEN_MONTHS"])
            st.session_state.open_months_list = [(m[0], m[1]) for m in loaded_m]
        except: st.session_state.open_months_list = [(2026, 3)]
    else: st.session_state.open_months_list = [(2026, 3)]
        
    if "SYS_CLOSED_DAYS" in raw_data:
        try: st.session_state.closed_days = [datetime.strptime(d, "%Y-%m-%d").date() for d in json.loads(raw_data["SYS_CLOSED_DAYS"])]
        except: st.session_state.closed_days = []
    else: st.session_state.closed_days = []
        
    if "SYS_OPEN_DAYS" in raw_data:
        try: st.session_state.open_days = [datetime.strptime(d, "%Y-%m-%d").date() for d in json.loads(raw_data["SYS_OPEN_DAYS"])]
        except: st.session_state.open_days = []
    else: st.session_state.open_days = []
        
    st.session_state.announcement = raw_data.get("SYS_ANNOUNCEMENT", "歡迎！請點擊上方分頁切換月份進行登記。")

if 'last_updated' not in st.session_state:
    st.session_state.last_updated = datetime.now().strftime("%H:%M:%S")

if 'selected_date' not in st.session_state:
    st.session_state.selected_date = None

# --- 4. 側邊欄 ---
with st.sidebar:
    st.header("🚢 功能選單")
    st.caption(f"上次更新: {st.session_state.last_updated}")
    
    if st.button("🔄 強制同步資料", type="primary"):
        st.cache_resource.clear()
        new_data = load_data()
        st.session_state.bookings = new_data
        
        if "SYS_OPEN_MONTHS" in new_data:
            try: st.session_state.open_months_list = [(m[0], m[1]) for m in json.loads(new_data["SYS_OPEN_MONTHS"])]
            except: pass
        if "SYS_CLOSED_DAYS" in new_data:
            try: st.session_state.closed_days = [datetime.strptime(d, "%Y-%m-%d").date() for d in json.loads(new_data["SYS_CLOSED_DAYS"])]
            except: pass
        if "SYS_OPEN_DAYS" in new_data:
            try: st.session_state.open_days = [datetime.strptime(d, "%Y-%m-%d").date() for d in json.loads(new_data["SYS_OPEN_DAYS"])]
            except: pass
        if "SYS_ANNOUNCEMENT" in new_data:
            st.session_state.announcement = new_data["SYS_ANNOUNCEMENT"]
            
        for db_key, db_val in new_data.items():
            if not str(db_key).startswith("SYS_"): 
                st.session_state[f"in_{db_key}"] = db_val
        st.session_state.last_updated = datetime.now().strftime("%H:%M:%S")
        st.toast("✅ 資料已同步")
        st.rerun()

    st.divider()
    
    st.header("⚙️ 管理員後台")
    password = st.text_input("輸入密碼登入", type="password")
    if password == ADMIN_PASSWORD:
        st.success("✅ 已登入")
        
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
                    save_data("SYS_OPEN_MONTHS", json.dumps(st.session_state.open_months_list))
                    st.rerun()

            opts = [f"{y}年{m}月" for y, m in current_list]
            rm_sel = st.multiselect("刪除月份", opts)
            if st.button("🗑️ 刪除"):
                for s in rm_sel:
                    y, m = s.replace("月","").split("年")
                    target = (int(y), int(m))
                    if target in st.session_state.open_months_list:
                        st.session_state.open_months_list.remove(target)
                save_data("SYS_OPEN_MONTHS", json.dumps(st.session_state.open_months_list))
                st.rerun()

        with st.expander("⛔ 休館設定"):
            d_input = st.date_input("日期", min_value=date(2025,1,1))
            c1, c2 = st.columns(2)
            if c1.button("休館 ❌"):
                if d_input in st.session_state.open_days: 
                    st.session_state.open_days.remove(d_input)
                if d_input not in st.session_state.closed_days:
                    st.session_state.closed_days.append(d_input)
                save_data("SYS_CLOSED_DAYS", json.dumps([d.strftime("%Y-%m-%d") for d in st.session_state.closed_days]))
                save_data("SYS_OPEN_DAYS", json.dumps([d.strftime("%Y-%m-%d") for d in st.session_state.open_days]))
                st.rerun()
                
            if c2.button("開館 🟢"):
                if d_input in st.session_state.closed_days: 
                    st.session_state.closed_days.remove(d_input)
                if d_input not in st.session_state.open_days:
                    st.session_state.open_days.append(d_input)
                save_data("SYS_CLOSED_DAYS", json.dumps([d.strftime("%Y-%m-%d") for d in st.session_state.closed_days]))
                save_data("SYS_OPEN_DAYS", json.dumps([d.strftime("%Y-%m-%d") for d in st.session_state.open_days]))
                st.rerun()
                
        with st.expander("📢 公告"):
            ann = st.text_area("內容", st.session_state.announcement)
            if st.button("更新公告"): 
                st.session_state.announcement = ann
                save_data("SYS_ANNOUNCEMENT", ann)
                st.rerun()
        
        with st.expander("📥 下載每月排班表 (Excel專用)"):
            st.write("系統會自動將資料整理成完美排版的表格。")
            dl_opts = [f"{y}年{m:02d}月" for y, m in sorted(st.session_state.open_months_list)]
            if dl_opts:
                dl_sel = st.selectbox("請選擇要下載的月份", dl_opts)
                
                y_str, m_str = dl_sel.replace("月","").split("年")
                target_prefix = f"{y_str}-{m_str}"
                
                data_list = []
                for k, v in st.session_state.bookings.items():
                    if v.strip() and not str(k).startswith("SYS_"):
                        if k.startswith(target_prefix): 
                            parts = k.split("_")
                            if len(parts) >= 4:
                                data_list.append({
                                    "日期": parts[0], 
                                    "時段": parts[1], 
                                    "區域": parts[2], 
                                    "志工姓名": v
                                })
                
                if data_list:
                    df_dl = pd.DataFrame(data_list)
                    df_dl = df_dl.sort_values(by=["日期", "時段", "區域"])
                    csv_bytes = df_dl.to_csv(index=False).encode('utf-8-sig')
                    
                    st.download_button(
                        label=f"💾 點此下載 {dl_sel} 班表",
                        data=csv_bytes,
                        file_name=f"王船文化館排班表_{dl_sel}.csv",
                        mime="text/csv",
                        type="primary"
                    )
                else:
                    st.info("⚠️ 該月份目前尚無志工排班資料。")

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
            # ==========================================
            # 🌟 新增：個人班表查詢功能 (放在日曆上方)
            # ==========================================
            with st.expander("🔍 點此查詢本月個人班表", expanded=False):
                search_name = st.text_input("輸入姓名查詢：", key=f"search_{year}_{month}", placeholder="例如：陳大明")
                if search_name.strip():
                    target_prefix = f"{year}-{month:02d}"
                    found_shifts = []
                    
                    # 搜尋符合該月份且包含該姓名的資料
                    for k, v in st.session_state.bookings.items():
                        if v.strip() and (search_name in v) and k.startswith(target_prefix) and not str(k).startswith("SYS_"):
                            parts = k.split("_")
                            if len(parts) >= 4:
                                found_shifts.append({
                                    "日期": parts[0],
                                    "時段": parts[1],
                                    "區域": parts[2]
                                })
                                
                    if found_shifts:
                        st.success(f"🎉 找到 **{search_name}** 在本月的排班共 **{len(found_shifts)}** 筆：")
                        # 排序：日期由小到大 -> 上午優先於下午 -> 區域
                        df_search = pd.DataFrame(found_shifts).sort_values(by=["日期", "時段", "區域"])
                        
                        # 漂亮的逐行顯示
                        for _, row in df_search.iterrows():
                            st.markdown(f"- 📅 **{row['日期']}** ({row['時段']}) 📍 {row['區域']}")
                    else:
                        st.warning(f"本月沒有找到「{search_name}」的排班記錄喔！")
            
            st.write("---")
            # ==========================================
            
            cols = st.columns(7)
            for i, n in enumerate(["週一","週二","週三","週四","週五","週六","週日"]):
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
                            nv = st.text_input(f"志工{k+1}", val, key=widget_key, label_visibility="collapsed", placeholder=f"輸入姓名 (志工{k+1})")
                            
                            if nv != val:
                                if st.button("💾 確認儲存", key=f"btn_{key}", type="primary", use_container_width=True):
                                    st.session_state.bookings[key] = nv
                                    save_data(key, nv)
                                    st.toast(f"✅ 已成功為 {nv} 登記排班！")
                                    st.rerun()
                    st.divider()
        render_form("上午", t1)
        render_form("下午", t2)
