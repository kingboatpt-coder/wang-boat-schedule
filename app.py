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
#  CONSTANTS
# ─────────────────────────────────────────
INTERNAL_ZONES = ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6"]
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
    padding-top: 5px !important;
    padding-bottom: 20px !important;
    padding-left: 2px !important;
    padding-right: 2px !important;
    max-width: 500px !important; 
    margin: 0 auto !important;
}

/* ==============================================
   🎯 日曆頁面 (Month View)
   ============================================== */
h2 { margin-bottom: 0px !important; padding-bottom: 0px !important; font-size: 24px !important; }

div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) {
    display: grid !important; grid-template-columns: repeat(7, 1fr) !important;
    gap: 1px !important; width: 100% !important; margin-bottom: 2px !important;
}
div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) button {
    width: 100% !important; min-width: 0px !important; padding: 0px !important;
    aspect-ratio: 1 / 1 !important; height: auto !important;
    display: flex; align-items: center; justify-content: center;
    line-height: 1 !important; border-radius: 4px !important; border: 1px solid #ccc !important;
    font-weight: 600 !important; font-size: 14px !important;
}

/* 導航列 */
div[data-testid="stHorizontalBlock"]:has(> div:nth-child(3):last-child) {
    margin-bottom: 5px !important; gap: 0px !important; align-items: center !important; justify-content: center !important;
}
div[data-testid="stHorizontalBlock"]:has(> div:nth-child(3):last-child) button {
    height: 30px !important; border: none !important; background: transparent !important;
    font-size: 18px !important; color: #555 !important; box-shadow: none !important;
}

@media (max-width: 450px) {
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) button { font-size: 12px !important; }
    .day-header { font-size: 10px !important; }
    .nav-label { font-size: 16px !important; }
}

/* ==============================================
   🎯 排班表頁面 (Week Grid)
   ============================================== */

/* 表格樣式 */
.wk-wrap { overflow-x: auto; margin: 0 0 0 0; border-top: 2px solid #333; }
.wk-tbl { border-collapse: collapse; width: 100%; font-size: 12px; table-layout: fixed; }

.wk-tbl th { 
    border: 1px solid #333; padding: 2px; text-align: center; background: #eee; font-weight: 600;
    white-space: normal !important; word-wrap: break-word !important; vertical-align: middle; height: 35px; font-size: 11px;
}
.wk-tbl td { 
    border: 1px solid #333; padding: 2px; text-align: center; vertical-align: middle; height: 35px;
}

.wk-date-cell { background: #f5f5f5; font-weight: 700; font-size: 11px; width: 35px; }
.wk-shift-cell { background: #e8e8e8; font-size: 10px; width: 25px; font-weight: 600; writing-mode: vertical-rl; text-orientation: upright; letter-spacing: 2px;} 
.wk-filled-cell { background: #FFD700; }
.wk-empty-cell { background: #FFF; }
.wk-closed-cell { 
    background: #e0e0e0; color: #999; font-size: 10px; letter-spacing: 1px;
    background-image: repeating-linear-gradient(45deg, transparent, transparent 5px, #ccc 5px, #ccc 6px);
}
.vol-name { font-size: 13px; font-weight: 600; color: #000; display: block; line-height: 1.1; }
.sel-border { outline: 2px solid #cc0000; outline-offset: -2px; }

/* 輸入區塊壓縮 */
div[data-testid="stSelectbox"] label, div[data-testid="stTextInput"] label {
    font-size: 13px !important; margin-bottom: 0px !important; min-height: 0px !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"], div[data-testid="stTextInput"] div[data-baseweb="input"] {
    min-height: 35px !important; height: 35px !important;
}
div[data-testid="stSelectbox"], div[data-testid="stTextInput"] {
    margin-bottom: 5px !important;
}

/* 儲存/返回/導航按鈕 */
.save-btn-wrap button, .bot-exit-wrap button, .nav-week-btn button {
    height: 40px !important; font-size: 15px !important; font-weight: 700 !important; margin-top: 5px !important;
}
.save-btn-wrap button { background-color: #4ECDC4 !important; color: black !important; border: none !important; }
.bot-exit-wrap button { background: #888 !important; color: white !important; border: none !important; border-radius: 8px !important; }
.nav-week-btn button { background: white !important; color: #555 !important; border: 1px solid #ccc !important; border-radius: 8px !important; }

/* 其他通用 UI */
.day-header { text-align: center; font-size: 12px; font-weight: 700; color: #666; margin-bottom: 2px; }
.day-header.sunday { color: #cc0000; }
.nav-label { font-size: 18px; font-weight: 700; text-align: center; color: #333; white-space: nowrap; line-height: 1; margin: 0 5px; }
button:disabled { background-color: #e5e5e5 !important; color: #bbb !important; cursor: not-allowed !important; opacity: 0.6 !important; border: 1px solid #ddd !important; }
button[kind="primary"] { background-color: #ef4444 !important; color: white !important; border: none !important; }
.enter-btn-wrap { margin-top: 10px !important; margin-bottom: 10px !important; }
.enter-btn-wrap button { background-color: white !important; color: #333 !important; border: 1.5px solid #333 !important; height: 40px !important; width: 100% !important; font-size: 15px !important; font-weight: 700 !important; }
.ann-box { background: white; border: 2px solid #333; border-radius: 6px; margin-top: 5px !important; margin-bottom: 10px !important; }
.ann-title { border-bottom: 1.5px solid #333; padding: 6px; font-weight: 700; text-align: center; font-size: 15px; }
.ann-body { padding: 8px 12px; font-size: 13px; line-height: 1.5; color: #333; }
.admin-access-wrap { margin-top: 5px !important; text-align: center; }
.admin-access-wrap button { background: transparent !important; color: #aaa !important; border: none !important; font-size: 11px !important; padding: 0 !important; height: auto !important; }

.input-area {
    background-color: white; border-radius: 0 0 8px 8px; padding: 10px;
    border-left: 1px solid #ccc; border-right: 1px solid #ccc; border-bottom: 1px solid #ccc; margin-bottom: 10px;
}

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
    try:
        st.session_state.zone_names = json.loads(raw.get("SYS_ZONE_NAMES", json.dumps(DEFAULT_ZONE_NAMES)))
    except: 
        st.session_state.zone_names = DEFAULT_ZONE_NAMES

    st.session_state.announcement = raw.get("SYS_ANNOUNCEMENT","歡迎！點選週次進行排班。")
    st.session_state.page           = "calendar"
    st.session_state.month_idx      = 0
    st.session_state.sel_week_start = None
    st.session_state.sel_cell       = None 
    st.session_state.app_ready      = True

init_state()

# ─────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────
def is_open(d: date) -> bool:
    if d in st.session_state.closed_days: return False
    if d in st.session_state.open_days:   return True
    if d.weekday() == 0: return False 
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
    
    st.markdown("<h2>志工排班表</h2>", unsafe_allow_html=True)

    if not months:
        st.warning("⚠️ 暫無開放月份")
        _admin_btn(); return

    idx = min(st.session_state.month_idx, len(months)-1)
    year, month = months[idx]
    weeks = get_weeks(year, month)
    sel_start = st.session_state.sel_week_start

    c_nav = st.container()
    c1, c2, c3 = c_nav.columns([1, 3, 1]) 
    with c1:
        st.markdown('<div style="text-align: right;">', unsafe_allow_html=True)
        if st.button("◀", key="prev_m", disabled=(idx==0), use_container_width=True):
            st.session_state.month_idx = idx-1
            st.session_state.sel_week_start = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="nav-label">{MON_EN[month]} {year}</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div style="text-align: left;">', unsafe_allow_html=True)
        if st.button("▶", key="next_m", disabled=(idx>=len(months)-1), use_container_width=True):
            st.session_state.month_idx = idx+1
            st.session_state.sel_week_start = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

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
    st.markdown('<div class="admin-access-wrap">', unsafe_allow_html=True)
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
    
    # 確保不會 out of range (雖然前面有卡控)
    m_idx = min(st.session_state.month_idx, len(months)-1)
    cy, cm = months[m_idx]
    
    zone_names = st.session_state.zone_names
    sel_cell = st.session_state.get("sel_cell")

    st.markdown(f"<div class='wk-title'>志工排班表</div>", unsafe_allow_html=True)
    st.caption(f"{MON_EN[cm]} {cy}")

    # (2) 表格
    html  = '<div class="wk-wrap"><table class="wk-tbl">'
    
    # 表頭
    html += '<tr><th class="wk-hdr-zone" style="width:30px;">日期</th><th class="wk-hdr-zone" style="width:20px;"></th>'
    for z_name in zone_names: 
        html += f'<th class="wk-hdr-zone">{z_name}</th>'
    html += '</tr>'

    for day in week_days:  
        d_str  = day.strftime('%Y-%m-%d')
        closed = not is_open(day)
        lbl    = f"{day.month}/{day.day}<br>({WD[day.weekday()]})"
        
        if closed:
            # 休館日：高度 70px (35px * 2)
            html += f'<tr><td class="wk-date-cell" style="height:70px;">{lbl}</td>'
            html += f'<td class="wk-shift-cell"></td>' # 佔位
            html += f'<td colspan="{len(INTERNAL_ZONES)}" class="wk-closed-cell">休 館</td>'
            html += '</tr>'
        else:
            # (1) 同時顯示上下午：兩列
            # Row 1: 上午
            html += f'<tr><td class="wk-date-cell" rowspan="2">{lbl}</td>'
            html += f'<td class="wk-shift-cell">上午</td>'
            for i, z_id in enumerate(INTERNAL_ZONES):
                k = f"{d_str}_上午_{z_id}_1"
                v = st.session_state.bookings.get(k,"").strip()
                cls = "wk-filled-cell" if v else "wk-empty-cell"
                sc = " sel-border" if k==sel_cell else ""
                ct = f"<span class='vol-name'>{v}</span>" if v else ""
                html += f'<td class="{cls}{sc}">{ct}</td>'
            html += '</tr>'
            
            # Row 2: 下午
            html += '<tr>'
            html += f'<td class="wk-shift-cell">下午</td>'
            for i, z_id in enumerate(INTERNAL_ZONES):
                k = f"{d_str}_下午_{z_id}_1"
                v = st.session_state.bookings.get(k,"").strip()
                cls = "wk-filled-cell" if v else "wk-empty-cell"
                sc = " sel-border" if k==sel_cell else ""
                ct = f"<span class='vol-name'>{v}</span>" if v else ""
                html += f'<td class="{cls}{sc}">{ct}</td>'
            html += '</tr>'
    
    html += '</table></div>'
    st.markdown(html, unsafe_allow_html=True)

    # (3) 週間導航按鈕 (移到日曆下方)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="nav-week-btn">', unsafe_allow_html=True)
        if st.button("◀ 上一週", key="prev_w", use_container_width=True):
            st.session_state.sel_week_start -= timedelta(weeks=1)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="nav-week-btn">', unsafe_allow_html=True)
        if st.button("下一週 ▶", key="next_w", use_container_width=True):
            st.session_state.sel_week_start += timedelta(weeks=1)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # 輸入區 (依順序：日期 -> 時段 -> 區域 -> 姓名)
    open_days = [d for d in week_days if is_open(d)]
    
    if open_days:
        st.markdown('<div class="input-area">', unsafe_allow_html=True)
        st.markdown("<b>📝 登記排班</b>", unsafe_allow_html=True)
        
        # 1. 日期
        d_opts = [f"{d.month}/{d.day}({WD[d.weekday()]})" for d in open_days]
        d_idx = st.selectbox("日期", range(len(open_days)), format_func=lambda i: d_opts[i], key="pk_d")
        sel_date = open_days[d_idx]
        
        # 2. 時段 (新加入)
        shifts = ["上午", "下午"]
        s_idx = st.selectbox("時段", range(len(shifts)), format_func=lambda i: shifts[i], key="pk_s")
        sel_shift = shifts[s_idx]

        # 3. 區域
        z_idx = st.selectbox("區域", range(len(zone_names)), format_func=lambda i: zone_names[i], key="pk_z")
        sel_zone_id = INTERNAL_ZONES[z_idx]
        
        # 讀取資料 key
        key = f"{sel_date.strftime('%Y-%m-%d')}_{sel_shift}_{sel_zone_id}_1"
        val = st.session_state.bookings.get(key, "")

        # 4. 姓名輸入
        st.markdown("<div style='margin-top:2px;'><b>輸入或刪除名字</b></div>", unsafe_allow_html=True)
        new_n = st.text_input("志工姓名", val, key="in_n", placeholder="輸入名字", label_visibility="collapsed")

        # 儲存
        st.markdown('<div class="save-btn-wrap">', unsafe_allow_html=True)
        if st.button("儲存", key="save_entry", use_container_width=True):
            st.session_state.bookings[key] = new_n
            save_data(key, new_n)
            st.session_state.sel_cell = key # 讓紅框定位
            st.success("已儲存！")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("本週全部休館")

    st.markdown('<div class="bot-exit-wrap">', unsafe_allow_html=True)
    if st.button("返回", key="exit_g", use_container_width=True):
        st.session_state.page = "calendar"
        st.session_state.sel_cell = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────
#  ADMIN PAGES (略，維持原樣)
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
    btns = [("管理開放月份","admin_months"),("休館設定","admin_holidays"),("公告修改","admin_ann"),("區域名稱設定","admin_zones")]
    for label, dest in btns:
        st.markdown('<div class="admin-big-btn">', unsafe_allow_html=True)
        if st.button(label, key=f"ab_{dest}", use_container_width=True): nav(dest)
        st.markdown('</div><div style="height:5px"></div>', unsafe_allow_html=True)
    st.markdown('</div><div style="height:20px"></div><div class="admin-back-btn">', unsafe_allow_html=True)
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
    for i in range(6):
        val = st.text_input(f"區域 {i+1} 名稱", value=current_names[i], key=f"zn_{i}")
        new_names.append(val)
    if st.button("✅ 儲存區域名稱", type="primary"):
        st.session_state.zone_names = new_names
        save_data("SYS_ZONE_NAMES", json.dumps(new_names))
        st.success("已更新區域名稱！"); st.rerun()
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
