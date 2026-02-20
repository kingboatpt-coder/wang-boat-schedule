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
st.set_page_config(page_title="志工排班表", page_icon="🚢", layout="wide")

st.markdown("""
<style>
/* ── Reset Streamlit chrome ─── */
#MainMenu,footer,header{visibility:hidden;}
[data-testid="stToolbar"],[data-testid="stElementToolbar"],[data-testid="stDecoration"]{display:none!important;}
section[data-testid="stSidebar"]{display:none!important;}

/* ── Global ─── */
.stApp{background:#e8e3d8!important;}
.block-container{padding:12px 10px 60px 10px!important;max-width:500px!important;margin:0 auto!important;}
html,body,[class*="css"]{font-family:-apple-system,"PingFang TC","Noto Sans TC",sans-serif;}

/* ── All buttons base ─── */
div[data-testid="stButton"]>button{width:100%!important;min-width:0!important;}

/* ─────────────── CALENDAR ─────────────── */
.cal-card{background:white;border-radius:14px;padding:14px 10px 12px 10px;box-shadow:0 2px 12px rgba(0,0,0,.10);margin-bottom:10px;}

/* Month nav – force single horizontal row */
.mnav-wrap>div[data-testid="stHorizontalBlock"]{
    display:flex!important;flex-wrap:nowrap!important;
    align-items:center!important;gap:0!important;}
.mnav-wrap>div[data-testid="stHorizontalBlock"]>div[data-testid="column"]{
    flex:0 0 auto!important;min-width:0!important;}
.mnav-wrap>div[data-testid="stHorizontalBlock"]>div[data-testid="column"]:nth-child(2){
    flex:1 1 auto!important;}
.mnav-wrap div[data-testid="stButton"]>button{
    background:none!important;border:none!important;box-shadow:none!important;
    color:#888!important;font-size:22px!important;padding:0!important;
    height:36px!important;width:38px!important;min-width:38px!important;}

/* Weekday header HTML */
.cal-wdhdr{display:grid;grid-template-columns:repeat(7,1fr);margin:6px 0 4px 0;}
.cal-wdhdr span{text-align:center;font-size:11px;font-weight:600;color:#888;padding:2px 0;}
.cal-wdhdr span.sun{color:#cc0000;}

/* Week-row buttons (each week = 1 button, shows dates as text) */
.week-row-wrap{margin:2px 0;}
.week-row-wrap div[data-testid="stButton"]>button{
    background:white!important;border:2px solid #ddd!important;
    border-radius:12px!important;height:44px!important;
    font-size:14px!important;font-weight:500!important;
    color:#333!important;letter-spacing:1px!important;
    font-family:"Courier New",monospace!important;}
.week-row-sel div[data-testid="stButton"]>button{
    background:white!important;border:2.5px solid #cc0000!important;
    border-radius:12px!important;height:44px!important;
    font-size:14px!important;font-weight:700!important;color:#222!important;
    font-family:"Courier New",monospace!important;}

/* Announcement */
.ann-box{background:white;border:2px solid #333;border-radius:6px;margin:12px 0;}
.ann-title{border-bottom:1.5px solid #333;padding:8px 16px;font-weight:700;font-size:16px;text-align:center;}
.ann-body{padding:12px 16px;min-height:50px;font-size:14px;white-space:pre-wrap;line-height:1.7;color:#333;}

/* Admin button */
.admin-btn-wrap div[data-testid="stButton"]>button{
    background:#c8c8c8!important;color:#555!important;border:none!important;
    border-radius:10px!important;font-size:14px!important;height:50px!important;}

/* ─────────────── WEEK GRID ─────────────── */
.wk-title{font-size:22px;font-weight:700;margin-bottom:2px;}

/* AM/PM toggle group – no gap, joined */
.shift-grp-wrap>div[data-testid="stHorizontalBlock"]{
    display:flex!important;flex-wrap:nowrap!important;gap:0!important;}
.shift-grp-wrap>div[data-testid="stHorizontalBlock"]>div[data-testid="column"]{
    flex:1 1 50%!important;min-width:0!important;}
.shift-am-on div[data-testid="stButton"]>button{
    background:#222!important;color:white!important;border:2px solid #222!important;
    border-radius:8px 0 0 8px!important;height:44px!important;font-size:15px!important;font-weight:700!important;}
.shift-am-off div[data-testid="stButton"]>button{
    background:white!important;color:#666!important;border:2px solid #ccc!important;
    border-right:1px solid #ccc!important;border-radius:8px 0 0 8px!important;
    height:44px!important;font-size:15px!important;}
.shift-pm-on div[data-testid="stButton"]>button{
    background:#222!important;color:white!important;border:2px solid #222!important;
    border-radius:0 8px 8px 0!important;height:44px!important;font-size:15px!important;font-weight:700!important;}
.shift-pm-off div[data-testid="stButton"]>button{
    background:white!important;color:#666!important;border:2px solid #ccc!important;
    border-left:1px solid #ccc!important;border-radius:0 8px 8px 0!important;
    height:44px!important;font-size:15px!important;}

/* Grid table */
.wk-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:8px 0;}
.wk-tbl{border-collapse:collapse;font-size:10px;width:100%;}
.wk-tbl th,.wk-tbl td{border:1.5px solid #333;padding:1px;text-align:center;vertical-align:middle;}
.wk-hdr-s{background:#aaa;font-size:14px;font-weight:700;padding:5px 2px;letter-spacing:1px;}
.wk-hdr-z{background:#ccc;font-size:9px;font-weight:600;padding:3px 1px;}
.wk-date{background:#f5f5f5;font-size:10px;line-height:1.3;padding:3px 2px;}
/* closed: remove line between row1/row2 */
.wk-cl-t{background:#ddd;height:14px;border-bottom:none!important;}
.wk-cl-b{background:#ddd;height:14px;border-top:none!important;}
/* open cells */
.wk-em{background:#FFE033;height:14px;}
.wk-fl{background:#FFD700;font-size:9px;padding:1px;line-height:1.2;}
.wk-sel{outline:2.5px solid #cc0000!important;outline-offset:-2px;}

/* Cell picker expander */
div[data-testid="stExpander"]{border-radius:10px!important;background:white!important;}
div[data-testid="stExpander"] summary{font-size:15px!important;font-weight:600!important;}
.picker-save div[data-testid="stButton"]>button{
    background:#222!important;color:white!important;border:none!important;
    border-radius:8px!important;height:48px!important;font-size:16px!important;font-weight:700!important;}

/* Back button */
.back-btn div[data-testid="stButton"]>button{
    background:#888!important;color:white!important;border:none!important;
    border-radius:10px!important;height:50px!important;font-size:15px!important;font-weight:600!important;}

/* ─────────────── ADMIN ─────────────── */
.admin-card{background:white;border-radius:14px;padding:28px 20px 20px;box-shadow:0 2px 14px rgba(0,0,0,.10);}
.admin-title{color:#e53e3e;text-align:center;font-size:26px;font-weight:700;margin-bottom:24px;}
.admin-big div[data-testid="stButton"]>button{
    background:#4ECDC4!important;color:#111!important;border:none!important;
    border-radius:10px!important;height:64px!important;font-size:18px!important;font-weight:600!important;
    box-shadow:0 2px 8px rgba(78,205,196,.3)!important;}
.admin-back div[data-testid="stButton"]>button{
    background:#c8c8c8!important;color:#444!important;border:none!important;
    border-radius:10px!important;height:48px!important;font-size:15px!important;}

/* ─────────────── MINI CAL (休館設定) ─── */
.mini-cal-card{background:white;border-radius:10px;padding:12px 8px;margin:12px 0;box-shadow:0 1px 6px rgba(0,0,0,.08);}
.mini-cal-title{text-align:center;font-weight:700;font-size:14px;margin-bottom:8px;}
.mini-cal-tbl{width:100%;border-collapse:collapse;table-layout:fixed;}
.mini-cal-tbl th{text-align:center;font-size:10px;color:#888;font-weight:600;padding:1px 0 4px;}
.mini-cal-tbl th.mc-sun{color:#cc0000;}
.mini-cal-tbl td{text-align:center;padding:2px 0;}
.mc-day{width:28px;height:28px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:500;}
.mc-open{color:#222;}
.mc-closed{background:#ddd;color:#999;}
.mc-sp-open{background:#4ECDC4;color:white;}
.mc-pad{color:#ddd;font-size:12px;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────
ZONES    = ["1F-沉浸室劇場","1F-手扶梯驗票","2F展區、特展","3F-展區","4F-展區","5F-閱讀區"]
ZONES_S  = ["1F沉浸","1F驗票","2F特展","3F展","4F展","5F閱"]
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
        df = pd.DataFrame(sheet.get_all_records())
        d = {}
        if not df.empty:
            df.columns = [str(c).lower() for c in df.columns]
            if "key" in df.columns and "value" in df.columns:
                for _,row in df.iterrows(): d[str(row["key"])]=str(row["value"])
        return d
    except: return {}

def save_data(key, value):
    try:
        client = init_connection()
        if client is None: return
        sheet = client.open("volunteer_db").sheet1
        try:
            cell = sheet.find(key); sheet.update_cell(cell.row,2,value)
        except: sheet.append_row([key,value])
    except Exception as e: st.error(f"❌ 存檔失敗: {e}")

# ─────────────────────────────────────────
#  STATE INIT
# ─────────────────────────────────────────
def init_state():
    if "app_ready" in st.session_state: return
    raw = load_data()
    st.session_state.bookings = raw
    try: st.session_state.open_months_list = [(m[0],m[1]) for m in json.loads(raw.get("SYS_OPEN_MONTHS","[[2026,3]]"))]
    except: st.session_state.open_months_list = [(2026,3)]
    try: st.session_state.closed_days = [datetime.strptime(d,"%Y-%m-%d").date() for d in json.loads(raw.get("SYS_CLOSED_DAYS","[]"))]
    except: st.session_state.closed_days = []
    try: st.session_state.open_days = [datetime.strptime(d,"%Y-%m-%d").date() for d in json.loads(raw.get("SYS_OPEN_DAYS","[]"))]
    except: st.session_state.open_days = []
    st.session_state.announcement = raw.get("SYS_ANNOUNCEMENT","歡迎！點選週次進行排班。")
    st.session_state.page         = "calendar"
    st.session_state.month_idx    = 0
    st.session_state.sel_week_sun = None
    st.session_state.grid_shift   = "上午"
    st.session_state.app_ready    = True

init_state()

# ─────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────
def is_open(d: date) -> bool:
    if d in st.session_state.closed_days: return False
    if d in st.session_state.open_days:   return True
    if d.weekday() == 0: return False  # Monday default closed
    return True

def nav(page):
    st.session_state.page = page
    st.rerun()

def week_mon(d: date) -> date:
    """Return Monday of d's week."""
    return d - timedelta(days=d.weekday())

def get_weeks(year, month):
    """Weeks starting Monday. Each = (monday, [mon..sun])."""
    first = date(year, month, 1)
    last  = date(year, month, calendar.monthrange(year,month)[1])
    mon = week_mon(first)
    weeks = []
    while mon <= last:
        weeks.append((mon, [mon+timedelta(days=i) for i in range(7)]))
        mon += timedelta(weeks=1)
    return weeks

def fmt_week_btn(days, month):
    """Format 7 days as a compact text string for button label."""
    parts = []
    for d in days:
        if d.month != month:
            parts.append("  ")
        elif not is_open(d) or d.weekday() == 6:  # closed or Sunday
            parts.append(f"({d.day})")
        else:
            parts.append(f" {d.day} " if d.day < 10 else f"{d.day} ")
    return "  ".join(parts)

# ─────────────────────────────────────────
#  MINI CALENDAR (for 休館設定)
# ─────────────────────────────────────────
def render_mini_cal(year, month):
    weeks = get_weeks(year, month)
    html = f'<div class="mini-cal-card"><div class="mini-cal-title">{year}年{month}月</div>'
    html += '<table class="mini-cal-tbl"><tr>'
    for h in ["一","二","三","四","五","六"]:
        html += f'<th>{h}</th>'
    html += '<th class="mc-sun">日</th></tr>'
    for _, days in weeks:
        html += '<tr>'
        for d in days:
            if d.month != month:
                html += f'<td><span class="mc-pad">{d.day}</span></td>'
            else:
                # Determine status
                if d in st.session_state.closed_days:
                    cls = "mc-day mc-closed"
                    html += f'<td><span class="{cls}">{d.day}</span></td>'
                elif d in st.session_state.open_days:
                    cls = "mc-day mc-sp-open"
                    html += f'<td><span class="{cls}">{d.day}</span></td>'
                elif d.weekday() == 0:  # default Monday closed
                    cls = "mc-day mc-closed"
                    html += f'<td><span class="{cls}">{d.day}</span></td>'
                elif d.weekday() == 6:  # Sunday
                    cls = "mc-day mc-closed"
                    html += f'<td><span class="{cls}">{d.day}</span></td>'
                else:
                    cls = "mc-day mc-open"
                    html += f'<td><span class="{cls}">{d.day}</span></td>'
        html += '</tr>'
    html += '</table></div>'
    return html

# ─────────────────────────────────────────
#  PAGE: CALENDAR  (+ inline week grid)
# ─────────────────────────────────────────
def page_calendar():
    months = sorted(st.session_state.open_months_list)
    today  = date.today()

    st.markdown("## 志工排班表")

    if not months:
        st.warning("⚠️ 暫無開放月份")
        _admin_btn(); return

    idx = min(st.session_state.month_idx, len(months)-1)
    year, month = months[idx]
    weeks = get_weeks(year, month)
    sel_ws = st.session_state.sel_week_sun

    # ── Calendar card ────────────────────
    st.markdown('<div class="cal-card">', unsafe_allow_html=True)

    # Month nav – forced single-row via CSS
    st.markdown('<div class="mnav-wrap">', unsafe_allow_html=True)
    nc1, nc2, nc3 = st.columns([1,6,1])
    with nc1:
        if st.button("◀", key="prev_m", disabled=(idx==0)):
            st.session_state.month_idx = idx-1
            st.session_state.sel_week_sun = None
            st.rerun()
    nc2.markdown(
        f"<div style='text-align:center;font-size:21px;font-weight:700;line-height:36px;'>"
        f"{MON_EN[month]} {year}</div>", unsafe_allow_html=True)
    with nc3:
        if st.button("▶", key="next_m", disabled=(idx>=len(months)-1)):
            st.session_state.month_idx = idx+1
            st.session_state.sel_week_sun = None
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Weekday header: Mon Tue Wed Thu Fri Sat Sun
    st.markdown("""
    <div class="cal-wdhdr">
      <span>Mon</span><span>Tue</span><span>Wed</span>
      <span>Thu</span><span>Fri</span><span>Sat</span>
      <span class="sun">Sun</span>
    </div>""", unsafe_allow_html=True)

    # Each week = one button showing all 7 dates
    for ws, days in weeks:
        # Only show weeks that have at least one in-month day
        if not any(d.month == month for d in days): continue

        is_sel = (sel_ws == ws)
        label  = fmt_week_btn(days, month)
        div_cls = "week-row-sel" if is_sel else "week-row-wrap"
        st.markdown(f'<div class="{div_cls}">', unsafe_allow_html=True)
        if st.button(label, key=f"wk_{ws}", use_container_width=True):
            st.session_state.sel_week_sun = ws
            st.session_state.grid_shift   = "上午"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # close cal-card

    # ── If a week is selected, show grid below ────
    if sel_ws is not None:
        _render_week_grid(sel_ws, year, month)
        return  # Don't show announcement + admin when grid is visible

    # ── Announcement ────────────────────
    ann = st.session_state.announcement.replace("<","&lt;").replace(">","&gt;")
    st.markdown(f'<div class="ann-box"><div class="ann-title">公告</div>'
                f'<div class="ann-body">{ann}</div></div>', unsafe_allow_html=True)

    _admin_btn()


def _admin_btn():
    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="admin-btn-wrap">', unsafe_allow_html=True)
    if st.button("管理員登入", key="admin_access", use_container_width=True):
        nav("admin_login")
    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────
#  WEEK GRID (rendered inline below calendar)
# ─────────────────────────────────────────
def _render_week_grid(ws, cal_year, cal_month):
    week_days = [ws + timedelta(days=i) for i in range(7)]  # Mon–Sun
    shift     = st.session_state.grid_shift

    st.markdown(f"<div style='height:12px'></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='wk-title'>志工排班表</div>", unsafe_allow_html=True)
    st.caption(f"{MON_EN[cal_month]} {cal_year}　可切換上下午查看排班狀況 ↓")

    # ── AM/PM joined toggle ──────────────
    st.markdown('<div class="shift-grp-wrap">', unsafe_allow_html=True)
    tc1, tc2 = st.columns(2)
    with tc1:
        cls = "shift-am-on" if shift=="上午" else "shift-am-off"
        st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
        if st.button("🌞 上午", key="tog_am", use_container_width=True):
            st.session_state.grid_shift = "上午"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with tc2:
        cls = "shift-pm-on" if shift=="下午" else "shift-pm-off"
        st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
        if st.button("🌤️ 下午", key="tog_pm", use_container_width=True):
            st.session_state.grid_shift = "下午"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Grid HTML ────────────────────────
    time_lbl = "09:00-12:00" if shift=="上午" else "14:00-17:00"
    html  = '<div class="wk-wrap"><table class="wk-tbl">'
    html += f'<tr><th class="wk-hdr-s" colspan="7">{shift}（{time_lbl}）</th></tr>'
    html += '<tr><th class="wk-hdr-z">日期</th>'
    for zs in ZONES_S: html += f'<th class="wk-hdr-z">{zs}</th>'
    html += '</tr>'

    # Mon(0) to Sat(5) = week_days[0..5], skip Sun(6)
    for day in week_days[:6]:
        d_str  = day.strftime('%Y-%m-%d')
        closed = not is_open(day)
        lbl    = f"{day.month}/{day.day}<br>({WD[day.weekday()]})"
        if closed: lbl += '<br><span style="color:#c00;font-size:8px;">休</span>'

        if closed:
            # Single visual row (2 rows but no line between them)
            html += f'<tr><td class="wk-date" rowspan="2">{lbl}</td>'
            for _ in ZONES: html += '<td class="wk-cl-t"></td>'
            html += '</tr><tr>'
            for _ in ZONES: html += '<td class="wk-cl-b"></td>'
            html += '</tr>'
        else:
            # Slot 1
            html += f'<tr><td class="wk-date" rowspan="2">{lbl}</td>'
            for z in ZONES:
                k = f"{d_str}_{shift}_{z}_1"
                v = st.session_state.bookings.get(k,"").strip()
                cls = "wk-fl" if v else "wk-em"
                ct  = f"<small>1.{v}</small>" if v else ""
                html += f'<td class="{cls}">{ct}</td>'
            html += '</tr><tr>'
            # Slot 2
            for z in ZONES:
                k = f"{d_str}_{shift}_{z}_2"
                v = st.session_state.bookings.get(k,"").strip()
                cls = "wk-fl" if v else "wk-em"
                ct  = f"<small>2.{v}</small>" if v else ""
                html += f'<td class="{cls}">{ct}</td>'
            html += '</tr>'

    html += '</table></div>'
    st.markdown(html, unsafe_allow_html=True)

    # ── Simplified cell picker ───────────
    open_days = [d for d in week_days[:6] if is_open(d)]
    with st.expander("📝 點選想要登記的格子", expanded=True):
        if not open_days:
            st.info("本週全部休館")
        else:
            d_opts  = [f"{d.month}/{d.day}({WD[d.weekday()]})" for d in open_days]
            sf_opts = ["上午","下午"]

            di = st.selectbox("日期", range(len(open_days)), format_func=lambda i:d_opts[i], key="pk_d")
            zn = st.selectbox("區域", range(len(ZONES)), format_func=lambda i:ZONES_S[i], key="pk_z")
            sf = st.selectbox("時段", sf_opts, index=sf_opts.index(shift), key="pk_sf")
            nm = st.text_input("姓名", key="pk_nm", placeholder="輸入姓名；清空後儲存 = 取消排班")

            st.markdown('<div class="picker-save">', unsafe_allow_html=True)
            if st.button("💾 儲存", key="picker_save", use_container_width=True):
                chosen_day = open_days[di]
                d_str_pk   = chosen_day.strftime('%Y-%m-%d')
                z_full     = ZONES[zn]

                # Auto-assign slot
                fresh  = load_data()
                k1 = f"{d_str_pk}_{sf}_{z_full}_1"
                k2 = f"{d_str_pk}_{sf}_{z_full}_2"
                v1 = fresh.get(k1,"").strip()
                v2 = fresh.get(k2,"").strip()

                if nm.strip():
                    # Adding a name: find empty slot
                    if not v1:
                        target_key = k1
                    elif not v2:
                        target_key = k2
                    else:
                        st.error("⚠️ 此時段此區域已額滿（2名志工）！")
                        target_key = None
                else:
                    # Clearing: find slot with current user's name to remove
                    # Or just clear slot1 if user doesn't specify
                    target_key = k1  # clear first slot

                if target_key:
                    # Check for conflict
                    old = st.session_state.bookings.get(target_key,"")
                    cloud = fresh.get(target_key,"")
                    if nm.strip() and cloud.strip() and cloud != old:
                        st.error(f"⚠️ 此格已被「{cloud}」搶先！")
                        st.session_state.bookings[target_key] = cloud
                    else:
                        st.session_state.bookings[target_key] = nm.strip()
                        save_data(target_key, nm.strip())
                        if nm.strip():
                            st.success(f"✅ 已儲存！{d_opts[di]} {sf} {ZONES_S[zn]}")
                        else:
                            st.success("✅ 已取消排班。")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # ── Back button ──────────────────────
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="back-btn">', unsafe_allow_html=True)
    if st.button("⬆ 回到前一頁", key="go_back", use_container_width=True):
        st.session_state.sel_week_sun = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────
#  ADMIN PAGES
# ─────────────────────────────────────────
def page_admin_login():
    st.markdown("<h2>管理員登入</h2>", unsafe_allow_html=True)
    pwd = st.text_input("密碼", type="password", key="pwd_in", placeholder="請輸入管理員密碼")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("登入", key="do_login", type="primary", use_container_width=True):
            if pwd==ADMIN_PW: nav("admin")
            else: st.error("密碼錯誤")
    with c2:
        if st.button("返回", key="cancel_login", use_container_width=True): nav("calendar")


def page_admin():
    st.markdown('<div class="admin-card">', unsafe_allow_html=True)
    st.markdown('<div class="admin-title">管理員後台</div>', unsafe_allow_html=True)
    for label,dest in [("管理開放月份","admin_months"),("休館設定","admin_holidays"),("公告修改","admin_ann")]:
        st.markdown('<div class="admin-big">', unsafe_allow_html=True)
        if st.button(label, key=f"ab_{dest}", use_container_width=True): nav(dest)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="admin-back">', unsafe_allow_html=True)
    if st.button("退回", key="admin_back", use_container_width=True): nav("calendar")
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
    st.caption("預設週一及週日休館，可額外設定特別休館/開館日。")

    # ── Visual mini-calendars ────────────
    months_to_show = sorted(st.session_state.open_months_list)[:2]
    if months_to_show:
        legend_html = """
        <div style='display:flex;gap:16px;margin:6px 0 10px;font-size:12px;align-items:center;'>
          <span><span style='display:inline-block;width:16px;height:16px;border-radius:50%;background:#ddd;vertical-align:middle;margin-right:4px;'></span>休館</span>
          <span><span style='display:inline-block;width:16px;height:16px;border-radius:50%;background:#4ECDC4;vertical-align:middle;margin-right:4px;'></span>特別開館（週一）</span>
          <span><span style='display:inline-block;width:16px;height:16px;border-radius:50%;background:white;border:1px solid #ccc;vertical-align:middle;margin-right:4px;'></span>正常開館</span>
        </div>"""
        st.markdown(legend_html, unsafe_allow_html=True)
        for y,m in months_to_show:
            st.markdown(render_mini_cal(y, m), unsafe_allow_html=True)

    st.markdown("---")
    di = st.date_input("選擇日期",min_value=date(2025,1,1),key="hol_d")
    h1,h2 = st.columns(2)
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
    "admin_login":    page_admin_login,
    "admin":          page_admin,
    "admin_months":   page_admin_months,
    "admin_holidays": page_admin_holidays,
    "admin_ann":      page_admin_ann,
}.get(st.session_state.get("page","calendar"), page_calendar)()
