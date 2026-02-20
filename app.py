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
/* ── Layout ─────────────────────────────── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"],
[data-testid="stElementToolbar"] { display: none !important; }
section[data-testid="stSidebar"]  { display: none !important; }
.block-container {
    padding: 0.6rem 0.8rem 4rem 0.8rem !important;
    max-width: 520px !important;
    margin: 0 auto !important;
}
.stApp { background-color: #e8e3d8; }

/* ── Typography ──────────────────────────── */
html, body, [class*="css"] { font-family: -apple-system, "PingFang TC", "Noto Sans TC", sans-serif; }

/* ── Calendar card ───────────────────────── */
.cal-card {
    background: white;
    border-radius: 14px;
    padding: 14px 10px 18px 10px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.10);
    margin-bottom: 14px;
}
.cal-month-title {
    font-size: 22px; font-weight: 700;
    text-align: center; margin: 0 0 10px 0;
    letter-spacing: -0.5px;
}
.cal-weekday {
    text-align: center; font-size: 11px;
    font-weight: 600; padding: 3px 0 6px 0;
}
.day-gray {
    width: 38px; height: 38px; border-radius: 50%;
    background: #e5e5e5; color: #b0b0b0;
    display: flex; align-items: center; justify-content: center;
    margin: 3px auto; font-size: 16px;
}
.day-today-gray {
    width: 38px; height: 38px; border-radius: 50%;
    background: #e5e5e5; color: #888;
    border: 2.5px solid #777;
    display: flex; align-items: center; justify-content: center;
    margin: 3px auto; font-size: 16px; box-sizing: border-box;
}
.day-pad { text-align:center; color:#ccc; font-size:16px; padding:10px 0; }

/* ── Calendar day buttons ─────────────────── */
div[data-testid="stButton"] > button {
    border-radius: 50% !important;
    width: 38px !important; height: 38px !important;
    min-width: 0 !important; min-height: 0 !important;
    padding: 0 !important;
    font-size: 15px !important;
    font-weight: 500 !important;
    transition: all 0.15s ease;
}
div[data-testid="stButton"] > button[kind="primary"] {
    background-color: #222 !important;
    color: white !important;
    border: none !important;
}
div[data-testid="stButton"] > button[kind="secondary"] {
    background-color: white !important;
    color: #222 !important;
    border: 1.5px solid #ddd !important;
}

/* ── Week highlight border ───────────────── */
.week-sel-bar {
    border-top: 2.5px solid #d00;
    margin-top: -2px; margin-bottom: 4px;
}

/* ── Announcement box ────────────────────── */
.ann-box {
    background: white;
    border: 2px solid #333;
    border-radius: 4px;
    margin-top: 14px;
}
.ann-title {
    border-bottom: 1.5px solid #333;
    padding: 8px 14px;
    font-weight: 700; font-size: 16px;
    text-align: center;
}
.ann-body {
    padding: 14px;
    min-height: 70px;
    font-size: 14px;
    white-space: pre-wrap;
    line-height: 1.6;
}

/* ── Admin hidden button ─────────────────── */
.admin-access-btn > div > button {
    background: #c8c8c8 !important;
    color: #444 !important;
    border-radius: 10px !important;
    font-size: 12px !important;
    height: 52px !important;
    width: 180px !important;
    border: none !important;
    box-shadow: none !important;
}

/* ── Grid table ──────────────────────────── */
.wk-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; margin-bottom: 6px; }
.wk-tbl { border-collapse: collapse; font-size: 10px; }
.wk-tbl th, .wk-tbl td {
    border: 1.5px solid #333;
    padding: 2px 1px;
    text-align: center;
    vertical-align: middle;
}
.wk-hdr1 { background:#bbb; font-size:13px; font-weight:700; padding:5px 8px; }
.wk-hdr2 { background:#d8d8d8; font-size:9px; font-weight:600; min-width:40px; }
.wk-date { background:#f8f8f8; font-size:10px; min-width:30px; }
.wk-y-empty { background:#FFE033; min-width:40px; height:18px; }
.wk-y-filled { background:#FFD700; min-width:40px; font-size:9px; }
.wk-closed { background:#ddd; color:#aaa; min-width:40px; }
.wk-sel { outline:3px solid #cc0000 !important; outline-offset:-2px; }

/* ── Bottom bar ──────────────────────────── */
.bot-join {
    background: #4ECDC4;
    border-radius: 10px;
    padding: 13px 10px;
    text-align: center;
    font-size: 14px;
    font-weight: 600;
    line-height: 1.4;
}
.bot-exit > div > button {
    background: #888 !important;
    color: white !important;
    border-radius: 10px !important;
    border: none !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    height: 52px !important;
}

/* ── Edit row ────────────────────────────── */
.edit-bar {
    background: #f0f0f0;
    border-radius: 8px;
    padding: 10px;
    margin: 8px 0;
}
.edit-label { font-weight: 700; font-size: 13px; margin-bottom: 4px; }

/* ── Admin page ──────────────────────────── */
.admin-card {
    background: white;
    border-radius: 14px;
    padding: 28px 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.10);
    max-width: 400px;
    margin: 0 auto;
}
.admin-title { color: #e53e3e; text-align: center; font-size: 24px; font-weight: 700; margin-bottom: 28px; }
.admin-big-btn > div > button {
    background: #4ECDC4 !important;
    color: #111 !important;
    font-size: 18px !important;
    font-weight: 600 !important;
    height: 64px !important;
    border-radius: 10px !important;
    border: none !important;
    margin-bottom: 8px !important;
    box-shadow: 0 2px 8px rgba(78,205,196,0.25) !important;
}
.admin-back-btn > div > button {
    background: #c8c8c8 !important;
    color: #444 !important;
    font-size: 16px !important;
    border-radius: 10px !important;
    height: 50px !important;
    border: none !important;
}

/* ── Sync button ─────────────────────────── */
.sync-btn > div > button {
    background: transparent !important;
    border: 1px solid #999 !important;
    border-radius: 20px !important;
    font-size: 13px !important;
    color: #555 !important;
    height: 32px !important;
    padding: 0 12px !important;
    min-width: 0 !important;
    width: auto !important;
}

/* hide all default Streamlit button width forcing */
div[data-testid="column"] div[data-testid="stButton"] {
    display: flex; justify-content: center;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────
ZONES = ["1F-沉浸室劇場", "1F-手扶梯驗票", "2F展區、特展", "3F-展區", "4F-展區", "5F-閱讀區"]
ZONES_SHORT = ["1F沉浸", "1F驗票", "2F特展", "3F展", "4F展", "5F閱"]
ADMIN_PASSWORD = "1234"
MAX_SLOTS = 2
WD = {0:"一", 1:"二", 2:"三", 3:"四", 4:"五", 5:"六", 6:"日"}
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

    try: st.session_state.open_months_list = [(m[0],m[1]) for m in json.loads(raw.get("SYS_OPEN_MONTHS","[[2026,3]]"))]
    except: st.session_state.open_months_list = [(2026,3)]

    try: st.session_state.closed_days = [datetime.strptime(d,"%Y-%m-%d").date() for d in json.loads(raw.get("SYS_CLOSED_DAYS","[]"))]
    except: st.session_state.closed_days = []

    try: st.session_state.open_days = [datetime.strptime(d,"%Y-%m-%d").date() for d in json.loads(raw.get("SYS_OPEN_DAYS","[]"))]
    except: st.session_state.open_days = []

    st.session_state.announcement = raw.get("SYS_ANNOUNCEMENT","歡迎！點選日期週次進行排班。")
    st.session_state.page = "calendar"
    st.session_state.month_idx = 0
    st.session_state.selected_week_sun = None   # Sunday of selected week
    st.session_state.selected_cell = None       # booking key string
    st.session_state.grid_shift = "上午"
    st.session_state.app_ready = True

init_state()

# ─────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────
def is_open(d: date) -> bool:
    if d in st.session_state.closed_days: return False
    if d in st.session_state.open_days: return True
    if d.weekday() == 0: return False  # Monday = default closed
    return True

def week_sunday(d: date) -> date:
    """Return the Sunday on-or-before d (Sun=0 in display)"""
    return d - timedelta(days=(d.weekday() + 1) % 7)

def nav(page: str):
    st.session_state.page = page
    st.rerun()

# ─────────────────────────────────────────
#  PAGE: CALENDAR  (Image 1)
# ─────────────────────────────────────────
def page_calendar():
    months = sorted(st.session_state.open_months_list)
    today = date.today()

    # ── Title bar ──────────────────────────
    r1c1, r1c2 = st.columns([4, 1])
    r1c1.markdown("## 志工排班表")
    with r1c2:
        st.markdown('<div class="sync-btn">', unsafe_allow_html=True)
        if st.button("🔄 同步", key="sync"):
            st.cache_resource.clear()
            del st.session_state["app_ready"]
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    if not months:
        st.warning("⚠️ 暫無開放月份，請管理員登入設定。")
        _admin_btn()
        return

    idx = min(st.session_state.month_idx, len(months)-1)
    year, month = months[idx]

    # ── Calendar card ───────────────────────
    st.markdown('<div class="cal-card">', unsafe_allow_html=True)

    # Month navigation
    mc1, mc2, mc3 = st.columns([1, 4, 1])
    with mc1:
        if st.button("◀", key="prev_m", disabled=(idx==0)):
            st.session_state.month_idx = idx - 1
            st.rerun()
    mc2.markdown(f"<p class='cal-month-title'>{MON_EN[month]} {year}</p>", unsafe_allow_html=True)
    with mc3:
        if st.button("▶", key="next_m", disabled=(idx>=len(months)-1)):
            st.session_state.month_idx = idx + 1
            st.rerun()

    # Weekday header row  Sun Mon Tue Wed Thu Fri Sat
    day_names = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]
    day_colors = ["#c44","#888","#888","#888","#888","#888","#888"]
    hcols = st.columns(7)
    for i,(n,c) in enumerate(zip(day_names, day_colors)):
        hcols[i].markdown(f"<div class='cal-weekday' style='color:{c};'>{n}</div>", unsafe_allow_html=True)

    # Build Sun-first weeks
    first = date(year, month, 1)
    last  = date(year, month, calendar.monthrange(year,month)[1])
    # first sunday on-or-before first
    cur_sun = first - timedelta(days=(first.weekday()+1)%7)

    sel_ws = st.session_state.selected_week_sun

    while cur_sun <= last:
        week = [cur_sun + timedelta(days=i) for i in range(7)]
        wcols = st.columns(7)
        is_sel_wk = (sel_ws == cur_sun)

        for i, day in enumerate(week):
            with wcols[i]:
                if day.month != month:
                    st.markdown(f"<div class='day-pad'>{day.day}</div>", unsafe_allow_html=True)
                    continue

                is_sun_sat = (i == 0 or i == 6)
                closed = not is_open(day) or is_sun_sat

                if closed:
                    cls = "day-today-gray" if day==today else "day-gray"
                    st.markdown(f"<div class='{cls}'>{day.day}</div>", unsafe_allow_html=True)
                else:
                    btn_t = "primary" if is_sel_wk else "secondary"
                    if st.button(str(day.day), key=f"d_{day}", type=btn_t, use_container_width=True):
                        st.session_state.selected_week_sun = cur_sun
                        st.session_state.page = "week_grid"
                        st.session_state.selected_cell = None
                        st.rerun()

        if is_sel_wk:
            st.markdown("<div class='week-sel-bar'></div>", unsafe_allow_html=True)

        cur_sun += timedelta(weeks=1)

    st.markdown('</div>', unsafe_allow_html=True)  # end cal-card

    # ── Announcement ───────────────────────
    st.markdown(f"""
    <div class="ann-box">
        <div class="ann-title">公告</div>
        <div class="ann-body">{st.session_state.announcement}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    _admin_btn()

def _admin_btn():
    st.markdown('<div class="admin-access-btn">', unsafe_allow_html=True)
    if st.button("管理員隱藏控制板登入\n(點擊後輸入密碼)", key="admin_acc"):
        nav("admin_login")
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────
#  PAGE: WEEK GRID  (Image 2)
# ─────────────────────────────────────────
def page_week_grid():
    ws = st.session_state.selected_week_sun
    if ws is None:
        nav("calendar"); return

    week_days = [ws + timedelta(days=i) for i in range(7)]
    months = sorted(st.session_state.open_months_list)
    cy, cm = months[min(st.session_state.month_idx, len(months)-1)]

    sel_cell = st.session_state.selected_cell

    # ── Month title ─────────────────────────
    st.markdown(f"<h3 style='margin:0 0 8px 0;'>{MON_EN[cm]} {cy}</h3>", unsafe_allow_html=True)

    # ── AM / PM shift toggle ────────────────
    shift_toggle = st.session_state.grid_shift
    tc1, tc2 = st.columns(2)
    with tc1:
        am_type = "primary" if shift_toggle=="上午" else "secondary"
        if st.button("🌞 上午 09:00-12:00", key="tog_am", use_container_width=True, type=am_type):
            st.session_state.grid_shift = "上午"
            st.rerun()
    with tc2:
        pm_type = "primary" if shift_toggle=="下午" else "secondary"
        if st.button("🌤️ 下午 14:00-17:00", key="tog_pm", use_container_width=True, type=pm_type):
            st.session_state.grid_shift = "下午"
            st.rerun()

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # ── Build HTML grid ─────────────────────
    shift = st.session_state.grid_shift

    html = '<div class="wk-wrap"><table class="wk-tbl">'
    html += f'<tr><th class="wk-hdr1" colspan="7">{shift}（09:00-12:00）' if shift=="上午" else f'<tr><th class="wk-hdr1" colspan="7">{shift}（14:00-17:00）'
    html += '</th></tr><tr><th class="wk-hdr2">日期</th>'
    for zs in ZONES_SHORT:
        html += f'<th class="wk-hdr2">{zs}</th>'
    html += '</tr>'

    for day in week_days:
        closed = not is_open(day)
        d_str = day.strftime('%Y-%m-%d')
        wday = WD[day.weekday()]
        label = f"{day.month}/{day.day}<br>({wday})"
        if closed: label += "<br><span style='color:#c00;font-size:8px;'>休</span>"

        date_cell_bg = "#e8e8e8" if closed else "#f9f9f9"

        # Slot 1 row
        html += f'<tr><td rowspan="2" class="wk-date" style="background:{date_cell_bg};">{label}</td>'
        for z_full in ZONES:
            k = f"{d_str}_{shift}_{z_full}_1"
            v = st.session_state.bookings.get(k,"").strip()
            if closed:
                html += '<td class="wk-closed"></td>'
            else:
                is_s = (k == sel_cell)
                cls = "wk-y-filled" if v else "wk-y-empty"
                sel_cls = " wk-sel" if is_s else ""
                disp = f"<small>1.{v}</small>" if v else ""
                html += f'<td class="{cls}{sel_cls}">{disp}</td>'
        html += '</tr>'

        # Slot 2 row
        html += '<tr>'
        for z_full in ZONES:
            k = f"{d_str}_{shift}_{z_full}_2"
            v = st.session_state.bookings.get(k,"").strip()
            if closed:
                html += '<td class="wk-closed"></td>'
            else:
                is_s = (k == sel_cell)
                cls = "wk-y-filled" if v else "wk-y-empty"
                sel_cls = " wk-sel" if is_s else ""
                disp = f"<small>2.{v}</small>" if v else ""
                html += f'<td class="{cls}{sel_cls}">{disp}</td>'
        html += '</tr>'

    html += '</table></div>'
    st.markdown(html, unsafe_allow_html=True)

    # ── Edit bar (when cell selected) ───────
    if sel_cell:
        parts = sel_cell.split("_")
        # key format: YYYY-MM-DD_shift_zone_slot
        # zone doesn't have "_", so parts = [date, shift, zone, slot]
        cur_val = st.session_state.bookings.get(sel_cell,"")
        try:
            d_obj = datetime.strptime(parts[0], "%Y-%m-%d").date()
            slot_num = parts[-1]
            zone_name = "_".join(parts[2:-1])
            shift_name = parts[1]
            d_label = f"{parts[0]} ({WD[d_obj.weekday()]}) {shift_name} {zone_name} 志工{slot_num}"
        except:
            d_label = sel_cell

        st.markdown(f"""
        <div class="edit-bar">
            <div class="edit-label">📍 {d_label}</div>
            <div style="font-size:11px;color:#666;">清空姓名後儲存 = 取消排班</div>
        </div>
        """, unsafe_allow_html=True)

        ec1, ec2, ec3 = st.columns([2, 4, 1])
        ec1.markdown("<div style='padding-top:6px;font-weight:700;'>輸入姓名</div>", unsafe_allow_html=True)
        new_name = ec2.text_input("姓名", cur_val, key=f"name_input_{sel_cell}",
                                   label_visibility="collapsed", placeholder="輸入姓名（空白=取消）")
        with ec3:
            if st.button("儲存", key="save_cell", type="primary"):
                fresh = load_data()
                cloud = fresh.get(sel_cell,"")
                old   = st.session_state.bookings.get(sel_cell,"")
                if cloud.strip() and cloud != old:
                    st.error(f"⚠️ 此格已被「{cloud}」搶先排班！")
                    st.session_state.bookings[sel_cell] = cloud
                    st.rerun()
                else:
                    st.session_state.bookings[sel_cell] = new_name
                    save_data(sel_cell, new_name)
                    if new_name.strip():
                        st.success("✅ 排班已儲存！")
                    else:
                        st.success("✅ 已取消此格排班。")
                    st.session_state.selected_cell = None
                    st.rerun()

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ── Cell selector (expander) ────────────
    open_days = [d for d in week_days if is_open(d)]
    with st.expander("📝 點選想要登記的格子", expanded=True):
        if not open_days:
            st.info("本週全部休館")
        else:
            d_labels = [f"{d.month}/{d.day}({WD[d.weekday()]})" for d in open_days]
            sc1, sc2 = st.columns(2)
            di = sc1.selectbox("日期", range(len(open_days)), format_func=lambda i: d_labels[i], key="sel_day")
            zn = sc2.selectbox("區域", range(len(ZONES)), format_func=lambda i: ZONES_SHORT[i], key="sel_zone")
            sc3, sc4 = st.columns(2)
            sf = sc3.selectbox("時段", ["上午","下午"], index=0 if shift=="上午" else 1, key="sel_sf")
            sl = sc4.selectbox("名額", ["1","2"], format_func=lambda s: f"志工{s}", key="sel_slot")

            if st.button("📌 選取此格", key="pick_cell", type="primary", use_container_width=True):
                k = f"{open_days[di].strftime('%Y-%m-%d')}_{sf}_{ZONES[zn]}_{sl}"
                st.session_state.selected_cell = k
                st.session_state.grid_shift = sf
                st.rerun()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Bottom bar ──────────────────────────
    bc1, bc2 = st.columns([3, 2])
    bc1.markdown('<div class="bot-join">加入或取消值班<br><small>（點選想要的格子）</small></div>', unsafe_allow_html=True)
    with bc2:
        st.markdown('<div class="bot-exit">', unsafe_allow_html=True)
        if st.button("退出畫面", key="exit_grid", use_container_width=True):
            st.session_state.page = "calendar"
            st.session_state.selected_cell = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────
#  PAGE: ADMIN LOGIN
# ─────────────────────────────────────────
def page_admin_login():
    st.markdown("""
    <div style='background:white;border-radius:14px;padding:28px 24px;max-width:400px;margin:0 auto;box-shadow:0 2px 12px rgba(0,0,0,0.10);'>
        <h2 style='color:#e53e3e;text-align:center;'>管理員登入</h2>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    pwd = st.text_input("密碼", type="password", key="pwd_in", placeholder="請輸入管理員密碼")
    lc1, lc2 = st.columns(2)
    with lc1:
        if st.button("登入", key="do_login", type="primary", use_container_width=True):
            if pwd == ADMIN_PASSWORD:
                nav("admin")
            else:
                st.error("密碼錯誤")
    with lc2:
        if st.button("返回", key="cancel_login", use_container_width=True):
            nav("calendar")

# ─────────────────────────────────────────
#  PAGE: ADMIN MAIN  (Image 3)
# ─────────────────────────────────────────
def page_admin():
    st.markdown("""
    <div class="admin-card">
        <div class="admin-title">管理員後台</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    btn_pages = [
        ("管理開放月份", "admin_months"),
        ("休館設定",     "admin_holidays"),
        ("公告修改",     "admin_announcement"),
    ]
    for label, dest in btn_pages:
        st.markdown('<div class="admin-big-btn">', unsafe_allow_html=True)
        if st.button(label, key=f"ab_{dest}", use_container_width=True):
            nav(dest)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)

    bk1, _, bk3 = st.columns([2,2,1])
    with bk1:
        st.markdown('<div class="admin-back-btn">', unsafe_allow_html=True)
        if st.button("退回", key="admin_back", use_container_width=True):
            nav("calendar")
        st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────
#  PAGE: ADMIN → MONTHS
# ─────────────────────────────────────────
def page_admin_months():
    st.markdown("<h2 style='color:#e53e3e;'>管理開放月份</h2>", unsafe_allow_html=True)

    cur = sorted(st.session_state.open_months_list)
    if cur: st.info("目前開放：" + "、".join([f"{y}年{m}月" for y,m in cur]))
    else:   st.warning("目前無開放月份")

    st.markdown("#### ➕ 新增月份")
    c1,c2,c3 = st.columns(3)
    ay = c1.number_input("年",2025,2030,2026,key="am_y")
    am = c2.selectbox("月",range(1,13),2,key="am_m")
    if c3.button("新增",key="do_add_m"):
        t=(ay,am)
        if t not in st.session_state.open_months_list:
            st.session_state.open_months_list.append(t)
            save_data("SYS_OPEN_MONTHS",json.dumps(st.session_state.open_months_list))
            st.success(f"✅ 已新增 {ay}年{am}月"); st.rerun()

    st.markdown("#### 🗑️ 刪除月份")
    opts=[f"{y}年{m}月" for y,m in cur]
    rm=st.multiselect("選擇要刪除",opts,key="rm_m")
    if st.button("刪除選取",key="do_rm_m"):
        for s in rm:
            y2,m2=s.replace("月","").split("年")
            t=(int(y2),int(m2))
            if t in st.session_state.open_months_list:
                st.session_state.open_months_list.remove(t)
        save_data("SYS_OPEN_MONTHS",json.dumps(st.session_state.open_months_list))
        st.rerun()

    if st.button("← 返回管理後台",key="bk_months"): nav("admin")

# ─────────────────────────────────────────
#  PAGE: ADMIN → HOLIDAYS
# ─────────────────────────────────────────
def page_admin_holidays():
    st.markdown("<h2 style='color:#e53e3e;'>休館設定</h2>", unsafe_allow_html=True)
    st.caption("預設週一休館，可用下方設定額外休館或開館日。")

    di = st.date_input("選擇日期", min_value=date(2025,1,1), key="hol_date")
    hc1,hc2=st.columns(2)
    if hc1.button("❌ 設為休館",key="set_closed",type="primary"):
        if di in st.session_state.open_days: st.session_state.open_days.remove(di)
        if di not in st.session_state.closed_days: st.session_state.closed_days.append(di)
        save_data("SYS_CLOSED_DAYS",json.dumps([d.strftime("%Y-%m-%d") for d in st.session_state.closed_days]))
        save_data("SYS_OPEN_DAYS",  json.dumps([d.strftime("%Y-%m-%d") for d in st.session_state.open_days]))
        st.success("✅ 已設為休館"); st.rerun()
    if hc2.button("🟢 設為開館",key="set_open"):
        if di in st.session_state.closed_days: st.session_state.closed_days.remove(di)
        if di not in st.session_state.open_days: st.session_state.open_days.append(di)
        save_data("SYS_CLOSED_DAYS",json.dumps([d.strftime("%Y-%m-%d") for d in st.session_state.closed_days]))
        save_data("SYS_OPEN_DAYS",  json.dumps([d.strftime("%Y-%m-%d") for d in st.session_state.open_days]))
        st.success("✅ 已設為開館"); st.rerun()

    if st.session_state.closed_days:
        st.markdown("**特別休館日：**")
        for d in sorted(st.session_state.closed_days):
            st.markdown(f"- {d.strftime('%Y-%m-%d')} (週{WD[d.weekday()]})")
    if st.session_state.open_days:
        st.markdown("**特別開館日（原休館）：**")
        for d in sorted(st.session_state.open_days):
            st.markdown(f"- {d.strftime('%Y-%m-%d')} (週{WD[d.weekday()]})")

    if st.button("← 返回管理後台",key="bk_hol"): nav("admin")

# ─────────────────────────────────────────
#  PAGE: ADMIN → ANNOUNCEMENT
# ─────────────────────────────────────────
def page_admin_announcement():
    st.markdown("<h2 style='color:#e53e3e;'>公告修改</h2>", unsafe_allow_html=True)
    ann = st.text_area("公告內容",st.session_state.announcement,height=160,key="ann_ta")
    if st.button("✅ 更新公告",key="upd_ann",type="primary"):
        st.session_state.announcement=ann
        save_data("SYS_ANNOUNCEMENT",ann)
        st.success("已更新！"); st.rerun()

    if st.button("← 返回管理後台",key="bk_ann"): nav("admin")

# ─────────────────────────────────────────
#  ROUTER
# ─────────────────────────────────────────
_page = st.session_state.get("page","calendar")
{
    "calendar":            page_calendar,
    "week_grid":           page_week_grid,
    "admin_login":         page_admin_login,
    "admin":               page_admin,
    "admin_months":        page_admin_months,
    "admin_holidays":      page_admin_holidays,
    "admin_announcement":  page_admin_announcement,
}.get(_page, page_calendar)()
