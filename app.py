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
#  GLOBAL CSS
# ─────────────────────────────────────────
st.markdown("""
<style>
/* ── Hide Streamlit chrome ─── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"],
[data-testid="stElementToolbar"],
[data-testid="stDecoration"] { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }

/* ── Page layout ─── */
.stApp { background-color: #e8e3d8 !important; }
.block-container {
    padding: 12px 10px 60px 10px !important;
    max-width: 500px !important;
    margin: 0 auto !important;
}

/* ── Font ─── */
html, body, [class*="css"] {
    font-family: -apple-system, "PingFang TC", "Noto Sans TC", "Helvetica Neue", sans-serif;
}

/* ── Calendar card ─── */
.cal-card {
    background: white;
    border-radius: 14px;
    padding: 16px 12px 20px 12px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.10);
    margin-bottom: 14px;
}

/* ── Calendar HTML table ─── */
.cal-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
}
.cal-table th {
    text-align: center;
    font-size: 12px;
    font-weight: 600;
    color: #888;
    padding: 2px 0 8px 0;
}
.cal-table th.sun-hdr { color: #cc0000; }
.cal-table td {
    text-align: center;
    padding: 3px 0;
    vertical-align: middle;
}
.cal-day-circle {
    width: 36px; height: 36px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    font-weight: 500;
}
.cal-day-normal { color: #222; }
.cal-day-gray   { background: #e5e5ea; color: #aaa; }
.cal-day-today  { border: 2px solid #888; color: #444; background: #e5e5ea; }
.cal-day-pad    { color: #ccc; font-size: 15px; }

/* ── Announcement ─── */
.ann-box {
    background: white;
    border: 2px solid #333;
    border-radius: 6px;
    margin-top: 16px;
    margin-bottom: 14px;
}
.ann-title {
    border-bottom: 1.5px solid #333;
    padding: 9px 16px;
    font-weight: 700; font-size: 16px;
    text-align: center;
}
.ann-body {
    padding: 14px 16px;
    min-height: 60px;
    font-size: 14px;
    white-space: pre-wrap;
    line-height: 1.7;
    color: #333;
}

/* ── ALL Streamlit buttons base reset ─── */
div[data-testid="stButton"] > button {
    width: 100% !important;
    min-width: 0 !important;
}

/* Month nav arrows */
.nav-col div[data-testid="stButton"] > button {
    background: none !important;
    border: none !important;
    box-shadow: none !important;
    color: #888 !important;
    font-size: 22px !important;
    padding: 0 !important;
    height: 36px !important;
}

/* Sync button */
.sync-wrap div[data-testid="stButton"] > button {
    background: transparent !important;
    border: 1.5px solid #999 !important;
    border-radius: 20px !important;
    color: #555 !important;
    font-size: 13px !important;
    height: 30px !important;
    width: 90px !important;
}

/* Week selection buttons */
.week-btn-inactive div[data-testid="stButton"] > button {
    background: white !important;
    border: 1.5px solid #bbb !important;
    border-radius: 22px !important;
    color: #444 !important;
    font-size: 13px !important;
    height: 36px !important;
    margin-bottom: 4px !important;
}
.week-btn-active div[data-testid="stButton"] > button {
    background: #cc0000 !important;
    border: 1.5px solid #cc0000 !important;
    border-radius: 22px !important;
    color: white !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    height: 36px !important;
    margin-bottom: 4px !important;
}

/* Admin hidden btn */
.admin-access-wrap div[data-testid="stButton"] > button {
    background: #c8c8c8 !important;
    color: #555 !important;
    border-radius: 10px !important;
    font-size: 12px !important;
    border: none !important;
    width: 200px !important;
    height: 52px !important;
    line-height: 1.4 !important;
}

/* ── Week grid page ─── */
.wk-title { font-size: 22px; font-weight: 700; margin-bottom: 4px; }

/* Shift toggle */
.shift-active div[data-testid="stButton"] > button {
    background: #222 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    height: 44px !important;
    font-size: 15px !important;
    font-weight: 700 !important;
}
.shift-inactive div[data-testid="stButton"] > button {
    background: white !important;
    color: #555 !important;
    border: 1.5px solid #ccc !important;
    border-radius: 8px !important;
    height: 44px !important;
    font-size: 15px !important;
}

/* Grid table */
.wk-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; margin: 8px 0; }
.wk-tbl {
    border-collapse: collapse;
    font-size: 10px;
    width: 100%;
}
.wk-tbl th, .wk-tbl td {
    border: 1.5px solid #333;
    padding: 2px 1px;
    text-align: center;
    vertical-align: middle;
}
.wk-hdr-shift {
    background: #aaa; font-size: 14px; font-weight: 700;
    padding: 6px 4px; letter-spacing: 1px;
}
.wk-hdr-zone {
    background: #ccc; font-size: 9px; font-weight: 600;
    padding: 3px 1px;
}
.wk-date-cell {
    background: #f5f5f5; font-size: 10px;
    line-height: 1.3; padding: 3px 2px;
    min-width: 30px;
}
.wk-closed-cell { background: #ddd; height: 16px; }
.wk-empty-cell  { background: #FFE033; height: 16px; }
.wk-filled-cell {
    background: #FFD700;
    font-size: 9px; padding: 1px;
    line-height: 1.2;
}
.wk-sel-cell { outline: 2.5px solid #cc0000 !important; outline-offset: -2px; }

/* Edit bar */
.edit-bar {
    background: #f0f0f0; border-radius: 8px;
    padding: 10px 12px; margin: 6px 0;
}
.edit-bar div[data-testid="stButton"] > button {
    background: #222 !important; color: white !important;
    border-radius: 6px !important; height: 40px !important;
    border: none !important; font-size: 13px !important;
}

/* Bottom action bar */
.bot-join {
    background: #4ECDC4;
    border-radius: 10px;
    padding: 14px 10px;
    text-align: center;
    font-size: 14px; font-weight: 600;
    line-height: 1.5; color: #111;
    height: 56px;
    display: flex; align-items: center; justify-content: center;
    flex-direction: column;
}
.bot-exit-wrap div[data-testid="stButton"] > button {
    background: #888 !important; color: white !important;
    border: none !important; border-radius: 10px !important;
    height: 56px !important; font-size: 15px !important;
    font-weight: 600 !important;
}

/* Expander */
div[data-testid="stExpander"] {
    border-radius: 10px !important;
    background: white !important;
}
div[data-testid="stExpander"] div[data-testid="stButton"] > button {
    background: #222 !important; color: white !important;
    border: none !important; border-radius: 8px !important;
    height: 44px !important; font-size: 14px !important;
    font-weight: 600 !important;
}

/* Admin page */
.admin-card {
    background: white; border-radius: 14px;
    padding: 30px 20px 20px 20px;
    box-shadow: 0 2px 14px rgba(0,0,0,0.10);
}
.admin-title {
    color: #e53e3e; text-align: center;
    font-size: 26px; font-weight: 700; margin-bottom: 28px;
}
.admin-big-btn div[data-testid="stButton"] > button {
    background: #4ECDC4 !important; color: #111 !important;
    border: none !important; border-radius: 10px !important;
    height: 64px !important; font-size: 18px !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 8px rgba(78,205,196,0.3) !important;
    margin-bottom: 2px !important;
}
.admin-back-btn div[data-testid="stButton"] > button {
    background: #c8c8c8 !important; color: #444 !important;
    border: none !important; border-radius: 10px !important;
    height: 50px !important; font-size: 15px !important;
    width: 140px !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────
ZONES   = ["1F-沉浸室劇場","1F-手扶梯驗票","2F展區、特展","3F-展區","4F-展區","5F-閱讀區"]
ZONES_S = ["1F沉浸","1F驗票","2F特展","3F展","4F展","5F閱"]
ADMIN_PW = "1234"
MAX_SLOTS = 2
WD = {0:"一",1:"二",2:"三",3:"四",4:"五",5:"六",6:"日"}
MON_EN = ["","January","February","March","April","May","June",
           "July","August","September","October","November","December"]

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
    st.session_state.announcement = raw.get("SYS_ANNOUNCEMENT","歡迎！點選週次進行排班。")
    st.session_state.page         = "calendar"
    st.session_state.month_idx    = 0
    st.session_state.sel_week_sun = None
    st.session_state.sel_cell     = None
    st.session_state.grid_shift   = "上午"
    st.session_state.app_ready    = True

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

def week_sun(d: date) -> date:
    return d - timedelta(days=(d.weekday()+1) % 7)

def get_weeks(year, month):
    first = date(year, month, 1)
    last  = date(year, month, calendar.monthrange(year, month)[1])
    sun = week_sun(first)
    weeks = []
    while sun <= last:
        weeks.append((sun, [sun + timedelta(days=i) for i in range(7)]))
        sun += timedelta(weeks=1)
    return weeks

# ─────────────────────────────────────────
#  PAGE: CALENDAR
# ─────────────────────────────────────────
def page_calendar():
    months = sorted(st.session_state.open_months_list)
    today  = date.today()

    # Title + sync
    h1, h2 = st.columns([5, 1])
    h1.markdown("## 志工排班表")
    with h2:
        st.markdown('<div class="sync-wrap">', unsafe_allow_html=True)
        if st.button("🔄 同步", key="sync"):
            st.cache_resource.clear()
            del st.session_state["app_ready"]
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    if not months:
        st.warning("⚠️ 暫無開放月份，請管理員設定。")
        _admin_btn(); return

    idx = min(st.session_state.month_idx, len(months)-1)
    year, month = months[idx]
    weeks = get_weeks(year, month)
    sel_ws = st.session_state.sel_week_sun

    # ── Calendar card (HTML only) ────────
    st.markdown('<div class="cal-card">', unsafe_allow_html=True)

    # Month nav: use 3 columns
    nc1, nc2, nc3 = st.columns([1, 6, 1])
    with nc1:
        st.markdown('<div class="nav-col">', unsafe_allow_html=True)
        if st.button("◀", key="prev_m", disabled=(idx==0)):
            st.session_state.month_idx = idx-1
            st.session_state.sel_week_sun = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    nc2.markdown(
        f"<div style='text-align:center;font-size:22px;font-weight:700;padding:4px 0;'>"
        f"{MON_EN[month]} {year}</div>", unsafe_allow_html=True)
    with nc3:
        st.markdown('<div class="nav-col">', unsafe_allow_html=True)
        if st.button("▶", key="next_m", disabled=(idx>=len(months)-1)):
            st.session_state.month_idx = idx+1
            st.session_state.sel_week_sun = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Pure HTML calendar (no Streamlit buttons inside)
    html = '<table class="cal-table"><tr>'
    html += '<th class="sun-hdr">Sun</th>'
    for h in ["Mon","Tue","Wed","Thu","Fri","Sat"]:
        html += f'<th>{h}</th>'
    html += '</tr>'

    for ws, days in weeks:
        is_sel = (sel_ws == ws)
        # Build week row with red border via inline style if selected
        if is_sel:
            # Highlight each cell with top/bottom red border, and outer cells with side borders
            html += '<tr>'
            for i, d in enumerate(days):
                border_style = "border-top:3px solid #cc0000;border-bottom:3px solid #cc0000;"
                if i == 0: border_style += "border-left:3px solid #cc0000;"
                if i == 6: border_style += "border-right:3px solid #cc0000;"
                if d.month != month:
                    html += f'<td style="{border_style}"><span class="cal-day-pad">{d.day}</span></td>'
                else:
                    closed = not is_open(d) or d.weekday() == 6
                    if closed:
                        cls = "cal-day-today" if d==today else "cal-day-gray"
                        html += f'<td style="{border_style}"><span class="cal-day-circle {cls}">{d.day}</span></td>'
                    else:
                        # Selected + open: dark circle
                        html += f'<td style="{border_style}"><span class="cal-day-circle" style="background:#222;color:white;">{d.day}</span></td>'
            html += '</tr>'
        else:
            html += '<tr>'
            for d in days:
                if d.month != month:
                    html += f'<td><span class="cal-day-pad">{d.day}</span></td>'
                else:
                    closed = not is_open(d) or d.weekday() == 6
                    if closed:
                        cls = "cal-day-today" if d==today else "cal-day-gray"
                        html += f'<td><span class="cal-day-circle {cls}">{d.day}</span></td>'
                    else:
                        cls = "cal-day-today" if d==today else "cal-day-normal"
                        html += f'<td><span class="cal-day-circle {cls}">{d.day}</span></td>'
            html += '</tr>'

    html += '</table>'
    st.markdown(html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)  # close cal-card

    # ── Week buttons (below calendar) ────
    st.markdown("<div style='margin:10px 0 4px 0;font-weight:600;'>📅 點選週次進入排班：</div>", unsafe_allow_html=True)
    workable = [(ws,days) for ws,days in weeks
                if any(d.month==month and is_open(d) for d in days[1:7])]

    for wi, (ws, days) in enumerate(workable):
        open_d = [d for d in days[1:7] if d.month==month and is_open(d)]
        if not open_d: continue
        label = f"{open_d[0].month}/{open_d[0].day}({WD[open_d[0].weekday()]})～{open_d[-1].month}/{open_d[-1].day}({WD[open_d[-1].weekday()]})"
        is_s = (sel_ws == ws)
        div_cls = "week-btn-active" if is_s else "week-btn-inactive"
        prefix  = "✅ " if is_s else ""
        st.markdown(f'<div class="{div_cls}">', unsafe_allow_html=True)
        if st.button(f"{prefix}第{wi+1}週：{label}", key=f"wk_{ws}", use_container_width=True):
            st.session_state.sel_week_sun = ws
            st.session_state.page = "week_grid"
            st.session_state.sel_cell = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Announcement ────────────────────
    ann = st.session_state.announcement.replace("<","&lt;").replace(">","&gt;")
    st.markdown(f'<div class="ann-box"><div class="ann-title">公告</div><div class="ann-body">{ann}</div></div>', unsafe_allow_html=True)

    _admin_btn()


def _admin_btn():
    st.markdown('<div class="admin-access-wrap" style="margin-top:20px;">', unsafe_allow_html=True)
    if st.button("管理員隱藏控制板登入\n(點擊後輸入密碼)", key="admin_access"):
        nav("admin_login")
    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────
#  PAGE: WEEK GRID
# ─────────────────────────────────────────
def page_week_grid():
    ws = st.session_state.sel_week_sun
    if ws is None: nav("calendar"); return

    week_days = [ws + timedelta(days=i) for i in range(7)]
    months = sorted(st.session_state.open_months_list)
    cy, cm = months[min(st.session_state.month_idx, len(months)-1)]
    shift    = st.session_state.grid_shift
    sel_cell = st.session_state.sel_cell

    st.markdown(f"<div class='wk-title'>志工排班表</div>", unsafe_allow_html=True)
    st.caption(f"{MON_EN[cm]} {cy}　可切換上下午查看排班狀況 ↓")

    # AM / PM toggle
    tc1, tc2 = st.columns(2)
    with tc1:
        cls = "shift-active" if shift=="上午" else "shift-inactive"
        st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
        if st.button("🌞 上午", key="tog_am", use_container_width=True):
            st.session_state.grid_shift = "上午"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with tc2:
        cls = "shift-active" if shift=="下午" else "shift-inactive"
        st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
        if st.button("🌤️ 下午", key="tog_pm", use_container_width=True):
            st.session_state.grid_shift = "下午"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Grid HTML table
    time_lbl = "09:00-12:00" if shift=="上午" else "14:00-17:00"
    html  = '<div class="wk-wrap"><table class="wk-tbl">'
    html += f'<tr><th class="wk-hdr-shift" colspan="7">{shift}（{time_lbl}）</th></tr>'
    html += '<tr><th class="wk-hdr-zone">日期</th>'
    for zs in ZONES_S:
        html += f'<th class="wk-hdr-zone">{zs}</th>'
    html += '</tr>'

    for day in week_days[1:7]:  # Mon(1) to Sat(6)
        d_str  = day.strftime('%Y-%m-%d')
        closed = not is_open(day)
        lbl    = f"{day.month}/{day.day}<br>({WD[day.weekday()]})"
        if closed: lbl += '<br><span style="color:#c00;font-size:8px;">休</span>'

        # Slot 1
        html += f'<tr><td class="wk-date-cell" rowspan="2">{lbl}</td>'
        for z in ZONES:
            k = f"{d_str}_{shift}_{z}_1"
            v = st.session_state.bookings.get(k,"").strip()
            if closed:
                html += '<td class="wk-closed-cell"></td>'
            else:
                sc  = " wk-sel-cell" if k==sel_cell else ""
                cls = "wk-filled-cell" if v else "wk-empty-cell"
                ct  = f"<small>1.{v}</small>" if v else ""
                html += f'<td class="{cls}{sc}">{ct}</td>'
        html += '</tr><tr>'
        # Slot 2
        for z in ZONES:
            k = f"{d_str}_{shift}_{z}_2"
            v = st.session_state.bookings.get(k,"").strip()
            if closed:
                html += '<td class="wk-closed-cell"></td>'
            else:
                sc  = " wk-sel-cell" if k==sel_cell else ""
                cls = "wk-filled-cell" if v else "wk-empty-cell"
                ct  = f"<small>2.{v}</small>" if v else ""
                html += f'<td class="{cls}{sc}">{ct}</td>'
        html += '</tr>'

    html += '</table></div>'
    st.markdown(html, unsafe_allow_html=True)

    # Edit bar
    if sel_cell:
        parts   = sel_cell.split("_")
        cur_val = st.session_state.bookings.get(sel_cell,"")
        try:
            d_obj = datetime.strptime(parts[0],"%Y-%m-%d").date()
            lbl   = f"{parts[0]}({WD[d_obj.weekday()]}) {parts[1]} {'_'.join(parts[2:-1])} 志工{parts[-1]}"
        except: lbl = sel_cell

        st.markdown('<div class="edit-bar">', unsafe_allow_html=True)
        st.markdown(f"<b>📍 {lbl}</b><br><small style='color:#666'>↓ 也可以刪除已輸入的名字後儲存取消排班</small>", unsafe_allow_html=True)
        ei1, ei2, ei3 = st.columns([2,4,1])
        ei1.markdown("<div style='padding-top:8px;font-weight:700;font-size:13px;'>輸入姓名</div>", unsafe_allow_html=True)
        new_nm = ei2.text_input("姓名", cur_val, key=f"nm_{sel_cell}",
                                 label_visibility="collapsed", placeholder="輸入姓名")
        with ei3:
            if st.button("儲存", key="save_c", type="primary"):
                fresh = load_data()
                cloud = fresh.get(sel_cell,"")
                old   = st.session_state.bookings.get(sel_cell,"")
                if cloud.strip() and cloud != old:
                    st.error(f"⚠️ 此格已被「{cloud}」先排班！")
                    st.session_state.bookings[sel_cell] = cloud
                    st.rerun()
                else:
                    st.session_state.bookings[sel_cell] = new_nm
                    save_data(sel_cell, new_nm)
                    st.session_state.sel_cell = None
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Cell picker
    open_days = [d for d in week_days[1:7] if is_open(d)]
    with st.expander("📝 點選想要登記的格子", expanded=True):
        if not open_days:
            st.info("本週全部休館")
        else:
            d_opts = [f"{d.month}/{d.day}({WD[d.weekday()]})" for d in open_days]
            di = st.selectbox("日期", range(len(open_days)), format_func=lambda i: d_opts[i], key="pk_d")
            zn = st.selectbox("區域", range(len(ZONES)), format_func=lambda i: ZONES_S[i], key="pk_z")
            sf_opts = ["上午","下午"]
            sf = st.selectbox("時段", sf_opts, index=sf_opts.index(shift), key="pk_sf")
            sl = st.selectbox("名額", ["1","2"], format_func=lambda s: f"志工{s}", key="pk_sl")
            if st.button("📌 選取此格", key="pick", type="primary", use_container_width=True):
                k = f"{open_days[di].strftime('%Y-%m-%d')}_{sf}_{ZONES[zn]}_{sl}"
                st.session_state.sel_cell   = k
                st.session_state.grid_shift = sf
                st.rerun()

    # Bottom bar
    bc1, bc2 = st.columns([3,2])
    bc1.markdown('<div class="bot-join">加入或取消值班<br><small>（點選想要的格子）</small></div>', unsafe_allow_html=True)
    with bc2:
        st.markdown('<div class="bot-exit-wrap">', unsafe_allow_html=True)
        if st.button("退出畫面", key="exit_g", use_container_width=True):
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
        if st.button("返回", key="cancel_login", use_container_width=True):
            nav("calendar")


def page_admin():
    st.markdown('<div class="admin-card">', unsafe_allow_html=True)
    st.markdown('<div class="admin-title">管理員後台</div>', unsafe_allow_html=True)
    for label, dest in [("管理開放月份","admin_months"),("休館設定","admin_holidays"),("公告修改","admin_ann")]:
        st.markdown('<div class="admin-big-btn">', unsafe_allow_html=True)
        if st.button(label, key=f"ab_{dest}", use_container_width=True): nav(dest)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="admin-back-btn">', unsafe_allow_html=True)
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
    if st.session_state.closed_days:
        st.markdown("**特別休館日：** " + "、".join([f"{d}(週{WD[d.weekday()]})" for d in sorted(st.session_state.closed_days)]))
    if st.session_state.open_days:
        st.markdown("**特別開館日：** " + "、".join([f"{d}(週{WD[d.weekday()]})" for d in sorted(st.session_state.open_days)]))
    if st.button("← 返回",key="bk_h"): nav("admin")


def page_admin_ann():
    st.markdown("## 公告修改")
    ann = st.text_area("公告內容",st.session_state.announcement,height=160,key="ann_ta")
    if st.button("✅ 更新公告",key="upd_ann",type="primary"):
        st.session_state.announcement=ann
        save_data("SYS_ANNOUNCEMENT",ann)
        st.success("已更新！"); st.rerun()
    if st.button("← 返回",key="bk_ann"): nav("admin")


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
}.get(st.session_state.get("page","calendar"), page_calendar)()
