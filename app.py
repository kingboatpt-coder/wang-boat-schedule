import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import calendar
import json

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    HAS_GSHEETS = True
except ImportError:
    HAS_GSHEETS = False

# ─────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────
st.set_page_config(page_title="志工排班表", page_icon="🚢", layout="wide")

# ─────────────────────────────────────────
#  CONSTANTS (內部鍵值，不可變動以免資料遺失)
# ─────────────────────────────────────────
# 這些是資料庫存檔用的 ID，不會隨後台修改而變動
INTERNAL_ZONES = ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6"]
# 預設顯示名稱
DEFAULT_ZONE_NAMES = ["1F-沉浸室劇場", "1F-手扶梯驗票", "2F展區、特展", "3F-展區", "4F-展區", "5F-閱讀區"]

ADMIN_PW = "1234"
WD = {0:"一",1:"二",2:"三",3:"四",4:"五",5:"六",6:"日"}
MON_EN = ["","January","February","March","April","May","June",
           "July","August","September","October","November","December"]

# ─────────────────────────────────────────
#  GLOBAL CSS
# ─────────────────────────────────────────
st.markdown("""
<style>
/* 1. 基礎清理 */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"], [data-testid="stDecoration"], section[data-testid="stSidebar"] { display: none !important; }

/* 2. 背景與主容器 */
.stApp { background-color: #e8e3d8 !important; }
.block-container {
    padding-top: 10px !important;
    padding-bottom: 30px !important;
    padding-left: 4px !important;
    padding-right: 4px !important;
    max-width: 500px !important; 
    margin: 0 auto !important;
}

/* ==============================================
   🎯 日曆頁面樣式
   ============================================== */
div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) {
    display: grid !important;
    grid-template-columns: repeat(7, 1fr) !important;
    gap: 2px !important;
    width: 100% !important;
    margin-bottom: 5px !important;
}
div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) > div[data-testid="column"] {
    min-width: 0px !important; width: auto !important; padding: 0 !important; margin: 0 !important;
    display: flex; justify-content: center;
}
div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) button {
    width: 100% !important; min-width: 0px !important; padding: 0px !important;
    aspect-ratio: 1 / 1 !important; height: auto !important;
    display: flex; align-items: center; justify-content: center;
    line-height: 1 !important; border-radius: 4px !important; border: 1px solid #ccc !important;
    font-weight: 600 !important;
}

/* 導航列 */
div[data-testid="stHorizontalBlock"]:has(> div:nth-child(3):last-child) {
    display: flex !important; align-items: center !important; justify-content: space-between !important;
}
div[data-testid="stHorizontalBlock"]:has(> div:nth-child(3):last-child) button {
    border: none !important; background: transparent !important;
    font-size: 20px !important; color: #555 !important; box-shadow: none !important;
}

@media (max-width: 450px) {
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) button { font-size: 13px !important; }
    .day-header { font-size: 11px !important; }
    .nav-label { font-size: 18px !important; }
}

/* ==============================================
   🎯 排班表頁面樣式
   ============================================== */
.shift-toggle-wrap {
    display: flex; gap: 0px; margin-bottom: 10px; background: white;
    border-radius: 8px; padding: 2px; border: 1px solid #ccc;
}

/* 表格優化：自動換行 */
.wk-wrap { overflow-x: auto; margin: 0 0 10px 0; }
.wk-tbl { border-collapse: collapse; width: 100%; font-size: 12px; table-layout: fixed; }

.wk-tbl th { 
    border: 1px solid #333; padding: 2px; text-align: center; background: #eee; font-weight: 600;
    white-space: normal !important; /* 允許換行 */
    word-wrap: break-word !important; /* 強制長字換行 */
    vertical-align: middle; height: 40px; font-size: 11px;
}

.wk-tbl td { 
    border: 1px solid #333; padding: 2px; text-align: center; vertical-align: middle; height: 45px;
}

.wk-date-cell { background: #f5f5f5; font-weight: 700; font-size: 11px; width: 35px; }
.wk-filled-cell { background: #FFD700; }
.wk-empty-cell { background: #FFF; }
.wk-closed-cell { 
    background: #e0e0e0; color: #999; font-size: 10px; letter-spacing: 1px;
    background-image: repeating-linear-gradient(45deg, transparent, transparent 5px, #ccc 5px, #ccc 6px);
}
.vol-name { font-size: 14px; font-weight: 600; color: #000; display: block; line-height: 1.2; }
.sel-border { outline: 2px solid #cc0000; outline-offset: -2px; }

/* 其他通用 UI */
.day-header { text-align: center; font-size: 13px; font-weight: 700; color: #666; margin-bottom: 2px; }
.day-header.sunday { color: #cc0000; }
.nav-label { font-size: 20px; font-weight: 700; text-align: center; color: #333; white-space: nowrap; line-height: 40px; }
button:disabled { background-color: #e5e5e5 !important; color: #bbb !important; cursor: not-allowed !important; opacity: 0.6 !important; border: 1px solid #ddd !important; }
button[kind="primary"] { background-color: #ef4444 !important; color: white !important; border: none !important; }

/* 進入/儲存/返回按鈕 */
.enter-btn-wrap button, .save-btn-wrap button { 
    background-color: white !important; color: #333 !important; 
    border: 1.5px solid #333 !important; margin-top: 15px !important; 
    height: 48px !important; width: 100% !important; font-size: 16px !important; font-weight: 700 !important;
}
.save-btn-wrap button {
    background-color: #4ECDC4 !important; border: none !important; color: black !important;
}

.ann-box { background: white; border: 2px solid #333; border-radius: 6px; margin: 15px 0; }
.ann-title { border-bottom: 1.5px solid #333; padding: 8px; font-weight: 700; text-align: center; }
.ann-body { padding: 12px; font-size: 14px; color: #333; line-height: 1.6; }
.edit-bar { background: #f0f0f0; border-radius: 8px; padding: 15px; margin: 10px 0; border: 1px solid #ccc; }
.bot-exit-wrap button { background: #888 !important; color: white !important; border: none !important; border-radius: 10px !important; height: 50px !important; font-size: 16px !important; font-weight: 600 !important; }
.admin-access-wrap button { background: transparent !important; color: #aaa !important; border: none !important; font-size: 12px !important; }

</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
#  GOOGLE SHEETS
# ─────────────────────────────────────────
@st.cache_resource
def init_connection():
    if not HAS_GSHEETS: return None
    if "textkey" not in st.secrets: return None
    key_dict = st.secrets["textkey"]
    scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    return gspread.authorize(creds)

def load_data():
    try:
        client = init_connection()
        if client is None: return {}
        sheet = client.open("volunteer_db").sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        d = {}
        if not df.empty:
            df.columns = [str(c).lower() for c in df.columns]
            if "key" in df.columns and "value" in df.columns:
                for _, row in df.iterrows():
                    d[str(row["key"])] = str(row["value"])
        return d
    except: return {}

def save_data(key, value):
    try:
        client = init_connection()
        if client is None: return
        sheet = client.open("volunteer_db").sheet1
        try:
            cell = sheet.find(key)
            sheet.update_cell(cell.row, 2, value)
        except:
            sheet.append_row([key, value])
    except Exception as e:
        st.error(f"❌ 存檔失敗: {e}")

# ─────────────────────────────────────────
#  STATE INIT
# ─────────────────────────────────────────
def init_state():
    if "app_ready" in st.session_state: return
    raw = load_data()
    st.session_state.bookings = raw
    try:
        st.session_state.open_months_list = [(m[0],m[1]) for m in json.loads(raw.get("SYS_OPEN_MONTHS","[[2026,3]]"))]
    except: st.session_state.open_months_list = [(2026,3)]
    try:
        st.session_state.closed_days = [datetime.strptime(d,"%Y-%m-%d").date() for d in json.loads(raw.get("SYS_CLOSED_DAYS","[]"))]
    except: st.session_state.closed_days = []
    try:
        st.session_state.open_days = [datetime.strptime(d,"%Y-%m-%d").date() for d in json.loads(raw.get("SYS_OPEN_DAYS","[]"))]
    except: st.session_state.open_days = []
    
    # Load Zone Names (Dynamic)
    try:
        st.session_state.zone_names = json.loads(raw.get("SYS_ZONE_NAMES", json.dumps(DEFAULT_ZONE_NAMES)))
    except: 
        st.session_state.zone_names = DEFAULT_ZONE_NAMES

    st.session_state.announcement = raw.get("SYS_ANNOUNCEMENT","歡迎！點選週次進行排班。")
    st.session_state.page           = "calendar"
    st.session_state.month_idx      = 0
    st.session_state.sel_week_start = None
    st.session_state.sel_cell       = None # Used for highlight only
    st.session_state.grid_shift     = "上午"
    st.session_state.app_ready      = True

init_state()

# ─────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────
def is_open(d: date) -> bool:
    if d in st.session_state.closed_days: return False
    if d in st.session_state.open_days:   return True
    if d.weekday() == 0: return False # Monday Closed
    return True

def nav(page):
    st.session_state.page = page
    st.rerun()

def get_week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())

def get_weeks(year, month):
    first = date(year, month, 1)
    last  = date(year, month, calendar.monthrange(year, month)[1])
    start = get_week_start(first)
    weeks = []
    while start <= last:
        weeks.append((start, [start + timedelta(days=i) for i in range(7)]))
        start += timedelta(weeks=1)
    return weeks

# ─────────────────────────────────────────
#  PAGE: CALENDAR
# ─────────────────────────────────────────
def page_calendar():
    months = sorted(st.session_state.open_months_list)
    
    st.markdown("## 志工排班表")

    if not months:
        st.warning("⚠️ 暫無開放月份")
        _admin_btn(); return

    idx = min(st.session_state.month_idx, len(months)-1)
    year, month = months[idx]
    weeks = get_weeks(year, month)
    sel_start = st.session_state.sel_week_start

    # Month Nav
    c_nav = st.container()
    c1, c2, c3 = c_nav.columns([1, 5, 1]) 
    with c1:
        if st.button("◀", key="prev_m", disabled=(idx==0), use_container_width=True):
            st.session_state.month_idx = idx-1
            st.session_state.sel_week_start = None
            st.rerun()
    with c2:
        st.markdown(f'<div class="nav-label">{MON_EN[month]} {year}</div>', unsafe_allow_html=True)
    with c3:
        if st.button("▶", key="next_m", disabled=(idx>=len(months)-1), use_container_width=True):
            st.session_state.month_idx = idx+1
            st.session_state.sel_week_start = None
            st.rerun()

    st.write("") 

    # Calendar Grid
    with st.container():
        header_cols = st.columns(7)
        days_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, label in enumerate(days_labels):
            cls = "day-header sunday" if i == 6 else "day-header"
            header_cols[i].markdown(f'<div class="{cls}">{label}</div>', unsafe_allow_html=True)

        for ws, days in weeks:
            is_selected = (sel_start == ws)
            btn_type = "primary" if is_selected else "secondary"
            dcols = st.columns(7)
            for i, d in enumerate(days):
                with dcols[i]:
                    if d.month != month:
                        st.empty() 
                    else:
                        is_closed = not is_open(d)
                        label = str(d.day)
                        if st.button(label, key=f"btn_{d}", type=btn_type, disabled=is_closed, use_container_width=True):
                            st.session_state.sel_week_start = ws
                            st.rerun()

    if sel_start:
        w_end = sel_start + timedelta(days=6)
        lbl = f"進入排班 ({sel_start.month}/{sel_start.day} ～ {w_end.month}/{w_end.day})"
        st.markdown('<div class="enter-btn-wrap">', unsafe_allow_html=True)
        if st.button(lbl, key="enter_grid", use_container_width=True):
            st.session_state.page = "week_grid"
            st.session_state.sel_week_sun = sel_start
            st.session_state.sel_cell = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    ann = st.session_state.announcement.replace("<","&lt;").replace(">","&gt;")
    st.markdown(f'<div class="ann-box"><div class="ann-title">公告</div><div class="ann-body">{ann}</div></div>', unsafe_allow_html=True)
    _admin_btn()

def _admin_btn():
    st.markdown('<div class="admin-access-wrap" style="text-align:center;">', unsafe_allow_html=True)
    if st.button("管理員登入", key="admin_access"):
        nav("admin_login")
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────
#  PAGE: WEEK GRID (修正版)
# ─────────────────────────────────────────
def page_week_grid():
    ws = st.session_state.get("sel_week_start") 
    if not ws: ws = st.session_state.get("sel_week_sun")
    if ws is None: nav("calendar"); return

    week_days = [ws + timedelta(days=i) for i in range(7)]
    months = sorted(st.session_state.open_months_list)
    cy, cm = months[min(st.session_state.month_idx, len(months)-1)]
    shift    = st.session_state.grid_shift
    
    # 取得目前的區域名稱
    zone_names = st.session_state.zone_names

    st.markdown(f"<div class='wk-title'>志工排班表</div>", unsafe_allow_html=True)
    st.caption(f"{MON_EN[cm]} {cy}")

    # 上下午按鈕
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🌞 上午", key="t_am", use_container_width=True, type="primary" if shift=="上午" else "secondary"):
            st.session_state.grid_shift = "上午"; st.rerun()
    with c2:
        if st.button("🌤️ 下午", key="t_pm", use_container_width=True, type="primary" if shift=="下午" else "secondary"):
            st.session_state.grid_shift = "下午"; st.rerun()

    # Grid HTML
    time_lbl = "09:00-12:00" if shift=="上午" else "14:00-17:00"
    html  = '<div class="wk-wrap"><table class="wk-tbl">'
    html += f'<tr><th colspan="7" style="background:#ddd;font-size:12px;padding:4px;">{shift}（{time_lbl}）</th></tr>'
    
    # 表頭：日期 + 動態區域名稱
    html += '<tr><th class="wk-hdr-zone" style="width:35px;">日期</th>'
    for z_name in zone_names: 
        html += f'<th class="wk-hdr-zone">{z_name}</th>'
    html += '</tr>'

    for day in week_days:  
        d_str  = day.strftime('%Y-%m-%d')
        closed = not is_open(day)
        lbl    = f"{day.month}/{day.day}<br>({WD[day.weekday()]})"
        if closed: lbl += '<br><span style="color:#c00;font-size:8px;">休</span>'

        if closed:
            html += f'<tr><td class="wk-date-cell" style="height:90px;">{lbl}</td>'
            html += f'<td colspan="{len(INTERNAL_ZONES)}" class="wk-closed-cell">休 館</td>'
            html += '</tr>'
        else:
            # Slot 1
            html += f'<tr><td class="wk-date-cell" rowspan="2">{lbl}</td>'
            for i, z_id in enumerate(INTERNAL_ZONES):
                k = f"{d_str}_{shift}_{z_id}_1"
                v = st.session_state.bookings.get(k,"").strip()
                cls = "wk-filled-cell" if v else "wk-empty-cell"
                ct = f"<span class='vol-name'>{v}</span>" if v else ""
                html += f'<td class="{cls}">{ct}</td>'
            html += '</tr>'
            # Slot 2
            html += '<tr>'
            for i, z_id in enumerate(INTERNAL_ZONES):
                k = f"{d_str}_{shift}_{z_id}_2"
                v = st.session_state.bookings.get(k,"").strip()
                cls = "wk-filled-cell" if v else "wk-empty-cell"
                ct = f"<span class='vol-name'>{v}</span>" if v else ""
                html += f'<td class="{cls}">{ct}</td>'
            html += '</tr>'
    
    html += '</table></div>'
    st.markdown(html, unsafe_allow_html=True)

    # Input Area (取代原本的選擇器)
    open_days = [d for d in week_days if is_open(d)]
    with st.expander("📝 點選想要登記的格子", expanded=True):
        if not open_days:
            st.info("本週全部休館")
        else:
            # 1. 選擇日期
            d_opts = [f"{d.month}/{d.day}({WD[d.weekday()]})" for d in open_days]
            d_idx = st.selectbox("日期", range(len(open_days)), format_func=lambda i: d_opts[i], key="pk_d")
            sel_date = open_days[d_idx]
            
            # 2. 選擇區域 (使用顯示名稱)
            z_idx = st.selectbox("區域", range(len(zone_names)), format_func=lambda i: zone_names[i], key="pk_z")
            sel_zone_id = INTERNAL_ZONES[z_idx]
            
            # 3. 顯示時段 (唯讀，跟隨上方 tab)
            st.markdown(f"<div style='font-size:14px;color:#666;margin-bottom:4px;'>時段：{shift}</div>", unsafe_allow_html=True)

            # 4. 讀取現有資料
            k1 = f"{sel_date.strftime('%Y-%m-%d')}_{shift}_{sel_zone_id}_1"
            k2 = f"{sel_date.strftime('%Y-%m-%d')}_{shift}_{sel_zone_id}_2"
            v1 = st.session_state.bookings.get(k1, "")
            v2 = st.session_state.bookings.get(k2, "")

            # 5. 輸入框 (直接編輯)
            st.markdown("<div style='margin-top:10px;'><b>輸入或刪除名字</b></div>", unsafe_allow_html=True)
            new_n1 = st.text_input("志工 1", v1, key="in_n1", placeholder="輸入名字")
            new_n2 = st.text_input("志工 2", v2, key="in_n2", placeholder="輸入名字")

            # 6. 儲存按鈕
            st.markdown('<div class="save-btn-wrap">', unsafe_allow_html=True)
            if st.button("儲存", key="save_entry", use_container_width=True):
                # Save both slots
                st.session_state.bookings[k1] = new_n1
                st.session_state.bookings[k2] = new_n2
                save_data(k1, new_n1)
                save_data(k2, new_n2)
                st.success("已儲存！")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # Bottom bar (Return)
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="bot-exit-wrap">', unsafe_allow_html=True)
    if st.button("返回", key="exit_g", use_container_width=True):
        st.session_state.page = "calendar"
        st.session_state.sel_cell = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────
#  ADMIN PAGES
# ─────────────────────────────────────────
def page_admin_login():
    st.markdown("<h2>管理員登入</h2>", unsafe_allow_html=True)
    pwd = st.text_input("密碼", type="password", key="pwd_in", placeholder="請輸入管理員密碼")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("登入", key="do_login", type="primary", use_container_width=True):
            if pwd == ADMIN_PW: nav("admin")
            else: st.error("密碼錯誤")
    with c2:
        if st.button("返回", key="cancel_login", use_container_width=True): nav("calendar")

def page_admin():
    st.markdown('<div class="admin-card"><div class="admin-title">管理員後台</div>', unsafe_allow_html=True)
    # 新增按鈕：管理區域名稱
    btns = [("管理開放月份","admin_months"),("休館設定","admin_holidays"),("公告修改","admin_ann"),("區域名稱設定","admin_zones")]
    for label, dest in btns:
        st.markdown('<div class="admin-big-btn">', unsafe_allow_html=True)
        if st.button(label, key=f"ab_{dest}", use_container_width=True): nav(dest)
        st.markdown('</div><div style="height:8px"></div>', unsafe_allow_html=True)
    st.markdown('</div><div style="height:30px"></div><div class="admin-back-btn">', unsafe_allow_html=True)
    if st.button("退回", key="admin_back"): nav("calendar")
    st.markdown('</div>', unsafe_allow_html=True)

def page_admin_months():
    st.markdown("## 管理開放月份")
    cur = sorted(st.session_state.open_months_list)
    if cur: st.info("目前開放：" + "、".join([f"{y}年{m}月" for y,m in cur]))
    else:   st.warning("目前無開放月份")
    c1,c2,c3 = st.columns(3)
    ay = c1.number_input("年",2025,2030,2026,key="am_y")
    am = c2.selectbox("月",range(1,13),2,key="am_m")
    if c3.button("新增",key="add_m"):
        t=(ay,am)
        if t not in st.session_state.open_months_list:
            st.session_state.open_months_list.append(t)
            save_data("SYS_OPEN_MONTHS",json.dumps(st.session_state.open_months_list))
            st.success("✅ 已新增"); st.rerun()
    rm = st.multiselect("刪除月份",[f"{y}年{m}月" for y,m in cur])
    if st.button("🗑️ 刪除",key="rm_m"):
        for s in rm:
            y2,m2=s.replace("月","").split("年")
            t=(int(y2),int(m2))
            if t in st.session_state.open_months_list: st.session_state.open_months_list.remove(t)
        save_data("SYS_OPEN_MONTHS",json.dumps(st.session_state.open_months_list)); st.rerun()
    if st.button("← 返回",key="bk_m"): nav("admin")

def page_admin_holidays():
    st.markdown("## 休館設定")
    st.caption("預設週一休館，可額外設定特別休館/開館日。")
    di = st.date_input("選擇日期",min_value=date(2025,1,1),key="hol_d")
    h1,h2=st.columns(2)
    if h1.button("❌ 設為休館",key="set_cl",type="primary"):
        if di in st.session_state.open_days: st.session_state.open_days.remove(di)
        if di not in st.session_state.closed_days: st.session_state.closed_days.append(di)
        save_data("SYS_CLOSED_DAYS",json.dumps([d.strftime("%Y-%m-%d") for d in st.session_state.closed_days]))
        save_data("SYS_OPEN_DAYS",json.dumps([d.strftime("%Y-%m-%d") for d in st.session_state.open_days]))
        st.success("✅ 已設為休館"); st.rerun()
    if h2.button("🟢 設為開館",key="set_op"):
        if di in st.session_state.closed_days: st.session_state.closed_days.remove(di)
        if di not in st.session_state.open_days: st.session_state.open_days.append(di)
        save_data("SYS_CLOSED_DAYS",json.dumps([d.strftime("%Y-%m-%d") for d in st.session_state.closed_days]))
        save_data("SYS_OPEN_DAYS",json.dumps([d.strftime("%Y-%m-%d") for d in st.session_state.open_days]))
        st.success("✅ 已設為開館"); st.rerun()
    if st.session_state.closed_days: st.markdown("**特別休館日：** " + "、".join([f"{d}(週{WD[d.weekday()]})" for d in sorted(st.session_state.closed_days)]))
    if st.session_state.open_days:   st.markdown("**特別開館日：** " + "、".join([f"{d}(週{WD[d.weekday()]})" for d in sorted(st.session_state.open_days)]))
    if st.button("← 返回",key="bk_h"): nav("admin")

def page_admin_ann():
    st.markdown("## 公告修改")
    ann = st.text_area("公告內容",st.session_state.announcement,height=160,key="ann_ta")
    if st.button("✅ 更新公告",key="upd_ann",type="primary"):
        st.session_state.announcement=ann
        save_data("SYS_ANNOUNCEMENT",ann)
        st.success("已更新！"); st.rerun()
    if st.button("← 返回",key="bk_ann"): nav("admin")

def page_admin_zones():
    st.markdown("## 區域名稱設定")
    st.caption("修改表格上方的標題名稱。")
    
    current_names = st.session_state.zone_names
    new_names = []
    
    # 產生 6 個輸入框
    for i in range(6):
        val = st.text_input(f"區域 {i+1} 名稱", value=current_names[i], key=f"zn_{i}")
        new_names.append(val)
        
    if st.button("✅ 儲存區域名稱", type="primary"):
        st.session_state.zone_names = new_names
        save_data("SYS_ZONE_NAMES", json.dumps(new_names))
        st.success("已更新區域名稱！")
        st.rerun()
        
    if st.button("← 返回", key="bk_zn"): nav("admin")

# ─────────────────────────────────────────
#  ROUTER
# ─────────────────────────────────────────
{
    "calendar":       page_calendar,
    "week_grid":      page_week_grid,
    "admin_login":    page_admin_login,
    "admin":          page_admin,
    "admin_months":   page_admin_months,
    "admin_holidays": page_admin_holidays,
    "admin_ann":      page_admin_ann,
    "admin_zones":    page_admin_zones,
}.get(st.session_state.get("page","calendar"), page_calendar)()
