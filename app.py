import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import calendar
import json
import io

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    HAS_GSHEETS = True
except ImportError:
    HAS_GSHEETS = False

st.set_page_config(page_title="志工排班表", page_icon="🚢", layout="wide")

INTERNAL_ZONES     = ["Z1","Z2","Z3","Z4","Z5","Z6"]
DEFAULT_ZONE_NAMES = ["1F-沉浸室劇場","1F-手扶梯驗票","2F展區、特展","3F-展區","4F-展區","5F-閱讀區"]
ADMIN_PW = "1234"
WD = {0:"一",1:"二",2:"三",3:"四",4:"五",5:"六",6:"日"}
MON_EN = ["","January","February","March","April","May","June",
           "July","August","September","October","November","December"]

st.markdown("""
<style>
#MainMenu,footer,header{visibility:hidden;}
[data-testid="stToolbar"],[data-testid="stDecoration"],
[data-testid="stElementToolbar"],
section[data-testid="stSidebar"]{display:none!important;}

.stApp{background:#e8e3d8!important;}
.block-container{
    padding:10px 6px 20px 6px!important;
    max-width:500px!important;margin:0 auto!important;
}
html,body,[class*="css"]{font-family:-apple-system,"PingFang TC","Noto Sans TC",sans-serif;}

.header-row{display:flex;align-items:baseline;gap:10px;margin-bottom:6px;padding-left:4px;}
.header-title{font-size:24px;font-weight:700;color:#333;margin:0;}
.header-date{font-size:16px;font-weight:500;color:#666;}

/* 7-col calendar grid */
div[data-testid="stHorizontalBlock"]:has(>div:nth-child(7)){
    display:grid!important;grid-template-columns:repeat(7,1fr)!important;
    gap:1px!important;width:100%!important;margin-bottom:4px!important;
}
div[data-testid="stHorizontalBlock"]:has(>div:nth-child(7)) button{
    width:100%!important;min-width:0!important;padding:0!important;
    aspect-ratio:1/1!important;height:auto!important;
    display:flex;align-items:center;justify-content:center;
    line-height:1!important;border-radius:4px!important;
    border:1px solid #ccc!important;font-weight:600!important;font-size:14px!important;
}

/* 3-col month nav - 修改箭頭間距與大小 */
div[data-testid="stHorizontalBlock"]:has(>div:nth-child(3):last-child){
    margin-bottom:8px!important;
    gap:0!important;
    align-items:center!important;
}
/* 強制讓中間的文字欄位置中 */
div[data-testid="stHorizontalBlock"]:has(>div:nth-child(3):last-child) div[data-testid="column"]:nth-child(2) {
    display: flex;
    justify-content: center;
    align-items: center;
}
/* 讓左右按鈕容器寬度一致 */
div[data-testid="stHorizontalBlock"]:has(>div:nth-child(3):last-child) button{
    height:36px!important;
    width:100%!important;
    border:none!important;
    background:transparent!important;
    font-size:22px!important; /* 稍微放大 */
    color:#555!important;
    box-shadow:none!important;
    display:flex;
    align-items:center;
    justify-content:center;
    padding:0!important;
}

/* enter button */
.enter-btn button{
    background:white!important;color:#333!important;
    border:1.5px solid #333!important;height:40px!important;
    font-size:15px!important;font-weight:700!important;margin-top:4px!important;
}

/* announcement */
.ann-box{background:white;border:2px solid #333;border-radius:6px;margin-top:6px!important;margin-bottom:8px!important;}
.ann-title{border-bottom:1.5px solid #333;padding:6px;font-weight:700;text-align:center;font-size:15px;}
.ann-body{padding:8px 12px;font-size:13px;line-height:1.5;color:#333;white-space:pre-wrap;}

.admin-tiny button{background:transparent!important;color:#bbb!important;border:none!important;
    font-size:11px!important;padding:0!important;height:auto!important;box-shadow:none!important;}

/* week grid table */
.wk-wrap{overflow-x:auto;margin:0 0 2px 0;}
.wk-tbl{border-collapse:collapse;width:100%;font-size:12px;table-layout:fixed;}
.wk-tbl th{border:1px solid #333;padding:2px;text-align:center;background:#eee;
    font-weight:600;white-space:normal!important;word-wrap:break-word!important;
    vertical-align:middle;height:35px;font-size:11px;}
.wk-tbl td{border:1px solid #333;padding:2px;text-align:center;vertical-align:middle;height:35px;}
.wk-date-cell{background:#f5f5f5;font-weight:700;font-size:11px;width:35px;}
.wk-shift-cell{background:#e8e8e8;font-size:10px;width:20px;font-weight:600;
    writing-mode:vertical-rl;text-orientation:upright;letter-spacing:1px;padding:0 2px;}
.wk-filled-cell{background:#FFD700;}
.wk-empty-cell{background:#FFF;}
.wk-closed-cell{background:#e0e0e0;color:#999;font-size:10px;letter-spacing:1px;
    background-image:repeating-linear-gradient(45deg,transparent,transparent 5px,#ccc 5px,#ccc 6px);}
.wk-outrange-cell{background:#d0d0d0;
    background-image:repeating-linear-gradient(45deg,transparent,transparent 4px,#aaa 4px,#aaa 5px);}
.vol-name{font-size:13px;font-weight:600;color:#000;display:block;
    line-height:1.1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.sel-border{outline:2px solid #cc0000;outline-offset:-2px;}

/* 2-col week nav */
div[data-testid="stHorizontalBlock"]:has(>div:nth-child(2):last-child){
    gap:4px!important;margin-top:2px!important;margin-bottom:2px!important;
}
div[data-testid="stHorizontalBlock"]:has(>div:nth-child(2):last-child) button{
    background:white!important;color:#333!important;
    border:1.5px solid #bbb!important;border-radius:8px!important;
    height:38px!important;font-size:11px!important;font-weight:600!important;width:100%!important;
}
div[data-testid="stHorizontalBlock"]:has(>div:nth-child(2):last-child) button:disabled{
    background:#eee!important;color:#bbb!important;border-color:#ddd!important;
}

/* compress inputs */
div[data-testid="stSelectbox"] label,
div[data-testid="stTextInput"] label{
    font-size:13px!important;margin-bottom:0!important;
    padding-bottom:0!important;line-height:1.3!important;min-height:0!important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"],
div[data-testid="stTextInput"] div[data-baseweb="input"]{
    min-height:32px!important;height:32px!important;font-size:14px!important;
}
div[data-testid="stSelectbox"],div[data-testid="stTextInput"]{
    margin-bottom:3px!important;margin-top:0!important;
}

button[kind="primary"]{background:#ef4444!important;color:white!important;border:none!important;}
button:disabled{background:#e5e5e5!important;color:#bbb!important;opacity:0.6!important;}
.day-header{text-align:center;font-size:12px;font-weight:700;color:#666;margin-bottom:2px;}
.day-header.sun{color:#cc0000;}

.admin-card{background:white;border-radius:14px;padding:28px 20px 20px;
    box-shadow:0 2px 14px rgba(0,0,0,.10);}
.admin-title{color:#e53e3e;text-align:center;font-size:26px;font-weight:700;margin-bottom:24px;}
.admin-big-btn button{background:#4ECDC4!important;color:#111!important;border:none!important;
    border-radius:10px!important;height:64px!important;font-size:18px!important;font-weight:600!important;}
.admin-back-btn button{background:#c8c8c8!important;color:#444!important;border:none!important;
    border-radius:10px!important;height:48px!important;font-size:15px!important;}

.mini-cal-wrap{background:white;border-radius:10px;padding:10px 8px 8px;
    border:1px solid #ddd;margin-bottom:10px;}
.mini-cal-month{text-align:center;font-weight:700;font-size:14px;
    margin-bottom:6px;color:#333;}
.mini-cal-tbl{width:100%;border-collapse:collapse;table-layout:fixed;}
.mini-cal-tbl th{font-size:10px;font-weight:600;color:#888;
    text-align:center;padding:2px 0 4px;}
.mini-cal-tbl th.mc-sun{color:#cc0000;}
.mini-cal-tbl td{text-align:center;padding:2px 0;}
.mc-day{width:30px;height:30px;border-radius:50%;display:inline-flex;
    align-items:center;justify-content:center;font-size:12px;font-weight:500;margin:auto;}
.mc-normal{color:#222;background:transparent;}
.mc-closed-def{background:#e0e0e0;color:#888;}
.mc-closed-sp{background:#ef4444;color:white;}
.mc-open-sp{background:#4ECDC4;color:white;}
.mc-pad{color:#ddd;font-size:12px;}

.cal-legend{display:flex;flex-wrap:wrap;gap:8px;
    font-size:11px;margin-bottom:8px;align-items:center;}
.leg-dot{width:12px;height:12px;border-radius:50%;
    display:inline-block;margin-right:3px;vertical-align:middle;}
</style>
""", unsafe_allow_html=True)

# ── Google Sheets ──────────────────────────────────────────
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

# ── State ──────────────────────────────────────────────────
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
    try: st.session_state.zone_names = json.loads(raw.get("SYS_ZONE_NAMES",json.dumps(DEFAULT_ZONE_NAMES)))
    except: st.session_state.zone_names = DEFAULT_ZONE_NAMES
    st.session_state.announcement   = raw.get("SYS_ANNOUNCEMENT","歡迎！點選週次進行排班。")
    st.session_state.page           = "calendar"
    st.session_state.month_idx      = 0
    st.session_state.sel_week_start = None
    st.session_state.sel_cell       = None
    st.session_state.app_ready      = True

init_state()

# ── Helpers ────────────────────────────────────────────────
def is_open(d: date) -> bool:
    if d in st.session_state.closed_days: return False
    if d in st.session_state.open_days:   return True
    if d.weekday() == 0: return False
    return True

def nav(page):
    st.session_state.page = page
    st.rerun()

def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())

def get_weeks(year, month):
    first = date(year, month, 1)
    last  = date(year, month, calendar.monthrange(year, month)[1])
    ws = week_start(first)
    weeks = []
    while ws <= last:
        weeks.append((ws, [ws+timedelta(days=i) for i in range(7)]))
        ws += timedelta(weeks=1)
    return weeks

def open_bounds():
    months = sorted(st.session_state.open_months_list)
    if not months:
        t = date.today(); return t, t
    y0,m0 = months[0];  y1,m1 = months[-1]
    return date(y0,m0,1), date(y1,m1,calendar.monthrange(y1,m1)[1])

def clipped_week_label(ws: date) -> str:
    min_d, max_d = open_bounds()
    we      = ws + timedelta(days=6)
    eff_s   = max(ws, min_d)
    eff_e   = min(we, max_d)
    if eff_s == eff_e:
        return f"{eff_s.month}/{eff_s.day}({WD[eff_s.weekday()]})"
    return (f"{eff_s.month}/{eff_s.day}({WD[eff_s.weekday()]})"
            f"～{eff_e.month}/{eff_e.day}({WD[eff_e.weekday()]})")

def full_week_label(ws: date) -> str:
    we = ws + timedelta(days=6)
    return f"{ws.month}/{ws.day}({WD[ws.weekday()]})～{we.month}/{we.day}({WD[we.weekday()]})"

def day_status(d: date, min_d: date, max_d: date) -> str:
    if d < min_d or d > max_d:
        return "outrange"
    if not is_open(d):
        return "closed"
    return "open"

# ── Page: Calendar ─────────────────────────────────────────
def page_calendar():
    months = sorted(st.session_state.open_months_list)
    if months:
        idx = min(st.session_state.month_idx, len(months)-1)
        year, month = months[idx]
        date_text = f"{MON_EN[month]} {year}"
    else:
        idx, year, month, date_text = 0, date.today().year, date.today().month, ""

    st.markdown(f'<div class="header-row">'
                f'<span class="header-title">志工排班表</span>'
                f'<span class="header-date">{date_text}</span></div>', unsafe_allow_html=True)

    if not months:
        st.warning("⚠️ 暫無開放月份"); _admin_btn(); return

    weeks     = get_weeks(year, month)
    sel_start = st.session_state.sel_week_start
    min_d, max_d = open_bounds()

    # Month nav - 調整欄位比例為 [1, 3, 1] 讓箭頭間距更緊湊對齊
    c1,c2,c3 = st.columns([1,3,1])
    with c1:
        if st.button("◀", key="prev_m", disabled=(idx==0), use_container_width=True):
            st.session_state.month_idx = idx-1
            st.session_state.sel_week_start = None
            st.rerun()
    with c2:
        st.markdown(f"<div style='text-align:center;font-weight:700;font-size:16px;line-height:36px;'>"
                    f"{MON_EN[month]} {year}</div>", unsafe_allow_html=True)
    with c3:
        if st.button("▶", key="next_m", disabled=(idx>=len(months)-1), use_container_width=True):
            st.session_state.month_idx = idx+1
            st.session_state.sel_week_start = None
            st.rerun()

    # Weekday header
    hdr = st.columns(7)
    for i,lbl in enumerate(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]):
        cls = "day-header sun" if i==6 else "day-header"
        hdr[i].markdown(f'<div class="{cls}">{lbl}</div>', unsafe_allow_html=True)

    # Calendar grid
    for ws, days in weeks:
        is_sel   = (sel_start == ws)
        btn_type = "primary" if is_sel else "secondary"
        dcols    = st.columns(7)
        for i,d in enumerate(days):
            with dcols[i]:
                if d.month != month:
                    st.empty()
                else:
                    status = day_status(d, min_d, max_d)
                    disabled = (status != "open")
                    if st.button(str(d.day), key=f"btn_{d}", type=btn_type,
                                 disabled=disabled, use_container_width=True):
                        st.session_state.sel_week_start = ws
                        st.rerun()

    if sel_start:
        lbl = f"進入排班　{clipped_week_label(sel_start)}"
        st.markdown('<div class="enter-btn">', unsafe_allow_html=True)
        if st.button(lbl, key="enter_grid", use_container_width=True):
            st.session_state.page     = "week_grid"
            st.session_state.sel_cell = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    ann = st.session_state.announcement.replace("<","&lt;").replace(">","&gt;")
    st.markdown(f'<div class="ann-box"><div class="ann-title">公告</div>'
                f'<div class="ann-body">{ann}</div></div>', unsafe_allow_html=True)
    _admin_btn()

def _admin_btn():
    st.markdown('<div class="admin-tiny">', unsafe_allow_html=True)
    if st.button("管理員登入", key="admin_access"):
        nav("admin_login")
    st.markdown('</div>', unsafe_allow_html=True)

# ── Page: Week Grid ────────────────────────────────────────
def page_week_grid():
    ws = st.session_state.sel_week_start
    if ws is None: nav("calendar"); return

    week_days  = [ws+timedelta(days=i) for i in range(7)]
    months     = sorted(st.session_state.open_months_list)
    cy,cm      = months[min(st.session_state.month_idx,len(months)-1)]
    zone_names = st.session_state.zone_names
    sel_cell   = st.session_state.get("sel_cell")
    min_d, max_d = open_bounds()

    st.markdown(f'<div class="header-row">'
                f'<span class="header-title">志工排班表</span>'
                f'<span class="header-date">{MON_EN[cm]} {cy}</span></div>', unsafe_allow_html=True)

    html = '<div class="wk-wrap"><table class="wk-tbl"><tr>'
    html += '<th class="wk-date-cell">日期</th><th class="wk-shift-cell"></th>'
    for z in zone_names: html += f'<th>{z}</th>'
    html += '</tr>'

    for day in week_days:
        d_str  = day.strftime('%Y-%m-%d')
        status = day_status(day, min_d, max_d)
        lbl    = f"{day.month}/{day.day}<br>({WD[day.weekday()]})"

        if status == "outrange":
            html += (f'<tr>'
                     f'<td class="wk-date-cell" rowspan="2" style="color:#bbb;">{lbl}</td>'
                     f'<td class="wk-shift-cell" style="color:#bbb;">上午</td>'
                     f'<td colspan="{len(INTERNAL_ZONES)}" class="wk-outrange-cell" rowspan="2"></td>'
                     f'</tr>'
                     f'<tr><td class="wk-shift-cell" style="color:#bbb;">下午</td></tr>')
        elif status == "closed":
            html += (f'<tr>'
                     f'<td class="wk-date-cell" style="height:26px;">{lbl}</td>'
                     f'<td class="wk-shift-cell"></td>'
                     f'<td colspan="{len(INTERNAL_ZONES)}" class="wk-closed-cell" style="height:26px;">休館</td>'
                     f'</tr>')
        else:
            html += f'<tr><td class="wk-date-cell" rowspan="2">{lbl}</td><td class="wk-shift-cell">上午</td>'
            for z_id in INTERNAL_ZONES:
                k  = f"{d_str}_上午_{z_id}_1"
                v  = st.session_state.bookings.get(k,"").strip()
                cls = "wk-filled-cell" if v else "wk-empty-cell"
                sc  = " sel-border" if k==sel_cell else ""
                html += f'<td class="{cls}{sc}">{"<span class=vol-name>"+v+"</span>" if v else ""}</td>'
            html += '</tr><tr><td class="wk-shift-cell">下午</td>'
            for z_id in INTERNAL_ZONES:
                k  = f"{d_str}_下午_{z_id}_1"
                v  = st.session_state.bookings.get(k,"").strip()
                cls = "wk-filled-cell" if v else "wk-empty-cell"
                sc  = " sel-border" if k==sel_cell else ""
                html += f'<td class="{cls}{sc}">{"<span class=vol-name>"+v+"</span>" if v else ""}</td>'
            html += '</tr>'

    html += '</table></div>'
    st.markdown(html, unsafe_allow_html=True)

    prev_ws  = ws - timedelta(weeks=1)
    next_ws  = ws + timedelta(weeks=1)
    prev_ok  = (prev_ws + timedelta(days=6)) >= min_d
    next_ok  = next_ws <= max_d

    nv1, nv2 = st.columns(2)
    with nv1:
        lbl = f"◀ {clipped_week_label(prev_ws)}" if prev_ok else "◀ （已是最早）"
        if st.button(lbl, key="prev_w", disabled=not prev_ok, use_container_width=True):
            st.session_state.sel_week_start = prev_ws
            st.session_state.sel_cell = None
            st.rerun()
    with nv2:
        lbl = f"{clipped_week_label(next_ws)} ▶" if next_ok else "（已是最後） ▶"
        if st.button(lbl, key="next_w", disabled=not next_ok, use_container_width=True):
            st.session_state.sel_week_start = next_ws
            st.session_state.sel_cell = None
            st.rerun()

    open_days = [d for d in week_days if day_status(d, min_d, max_d) == "open"]

    if open_days:
        st.markdown("**📝 登記排班**")
        d_opts   = [f"{d.month}/{d.day}({WD[d.weekday()]})" for d in open_days]
        d_idx    = st.selectbox("日期", range(len(open_days)),
                               format_func=lambda i: d_opts[i], key="pk_d")
        sel_date = open_days[d_idx]
        shifts = ["上午","下午"]
        s_idx  = st.selectbox("時段", range(2), format_func=lambda i: shifts[i], key="pk_s")
        sel_sf = shifts[s_idx]
        z_idx  = st.selectbox("區域", range(len(zone_names)),
                             format_func=lambda i: zone_names[i], key="pk_z")
        sel_zid = INTERNAL_ZONES[z_idx]
        key = f"{sel_date.strftime('%Y-%m-%d')}_{sel_sf}_{sel_zid}_1"
        val = st.session_state.bookings.get(key, "")
        new_n = st.text_input("輸入或刪除名字", val, key="in_n", placeholder="輸入名字（清空=取消排班）")
        save_clicked = st.button("儲存", key="save_entry", use_container_width=True)
        if save_clicked:
            fresh = load_data()
            cloud = fresh.get(key,"")
            old   = st.session_state.bookings.get(key,"")
            if cloud.strip() and cloud != old:
                st.error(f"⚠️ 此格已被「{cloud}」搶先登記！")
                st.session_state.bookings[key] = cloud
            else:
                st.session_state.bookings[key] = new_n.strip()
                save_data(key, new_n.strip())
                st.session_state.sel_cell = key
                st.success("✅ 已儲存！" if new_n.strip() else "✅ 已取消排班。")
            st.rerun()
    else:
        st.info("本週全部休館或不在開放月份範圍內")

    if st.button("返回月曆", key="exit_g", use_container_width=True):
        st.session_state.page     = "calendar"
        st.session_state.sel_cell = None
        st.rerun()

# ── Admin pages ────────────────────────────────────────────
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
    st.markdown('<div class="admin-card"><div class="admin-title">管理員後台</div>', unsafe_allow_html=True)
    for label,dest in [("管理開放月份","admin_months"),("休館設定","admin_holidays"),
                        ("公告修改","admin_ann"),("區域名稱設定","admin_zones"),
                        ("📥 下載值班表 Excel","admin_export")]:
        st.markdown('<div class="admin-big-btn">', unsafe_allow_html=True)
        if st.button(label, key=f"ab_{dest}", use_container_width=True): nav(dest)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.write("")
    st.markdown('<div class="admin-back-btn">', unsafe_allow_html=True)
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

def render_mini_cal(year, month):
    weeks = get_weeks(year, month)
    html  = f'<div class="mini-cal-wrap">'
    html += f'<div class="mini-cal-month">{year}年 {month}月</div>'
    html += '<table class="mini-cal-tbl"><tr>'
    for h in ["一","二","三","四","五","六"]:
        html += f'<th>{h}</th>'
    html += '<th class="mc-sun">日</th></tr>'
    for _, days in weeks:
        html += '<tr>'
        for d in days:
            if d.month != month:
                html += '<td><span class="mc-pad">·</span></td>'
                continue
            if d in st.session_state.closed_days:
                cls = "mc-day mc-closed-sp"
            elif d in st.session_state.open_days:
                cls = "mc-day mc-open-sp"
            elif d.weekday() in (0, 6):
                cls = "mc-day mc-closed-def"
            else:
                cls = "mc-day mc-normal"
            html += f'<td><span class="{cls}">{d.day}</span></td>'
        html += '</tr>'
    html += '</table></div>'
    return html

def page_admin_holidays():
    st.markdown("## 休館設定")
    st.caption("預設週一及週日休館，可額外設定特別休館/開館日。")
    st.markdown(
        '<div class="cal-legend">'
        '<span><span class="leg-dot" style="background:#e0e0e0;"></span>預設休館</span>'
        '<span><span class="leg-dot" style="background:#ef4444;"></span>特別休館</span>'
        '<span><span class="leg-dot" style="background:#4ECDC4;"></span>特別開館</span>'
        '<span><span class="leg-dot" style="background:#fff;border:1px solid #ccc;"></span>正常開館</span>'
        '</div>', unsafe_allow_html=True)
    for y, m in sorted(st.session_state.open_months_list):
        st.markdown(render_mini_cal(y, m), unsafe_allow_html=True)
    st.markdown("---")
    di = st.date_input("選擇日期", min_value=date(2025,1,1), key="hol_d")
    h1, h2 = st.columns(2)
    if h1.button("❌ 設為休館", key="set_cl", type="primary"):
        if di in st.session_state.open_days: st.session_state.open_days.remove(di)
        if di not in st.session_state.closed_days: st.session_state.closed_days.append(di)
        save_data("SYS_CLOSED_DAYS", json.dumps([d.strftime("%Y-%m-%d") for d in st.session_state.closed_days]))
        save_data("SYS_OPEN_DAYS",   json.dumps([d.strftime("%Y-%m-%d") for d in st.session_state.open_days]))
        st.success("✅ 已設為休館"); st.rerun()
    if h2.button("🟢 設為開館", key="set_op"):
        if di in st.session_state.closed_days: st.session_state.closed_days.remove(di)
        if di not in st.session_state.open_days: st.session_state.open_days.append(di)
        save_data("SYS_CLOSED_DAYS", json.dumps([d.strftime("%Y-%m-%d") for d in st.session_state.closed_days]))
        save_data("SYS_OPEN_DAYS",   json.dumps([d.strftime("%Y-%m-%d") for d in st.session_state.open_days]))
        st.success("✅ 已設為開館"); st.rerun()
    if st.session_state.closed_days:
        st.markdown("**特別休館日：** " + "、".join([f"{d}(週{WD[d.weekday()]})" for d in sorted(st.session_state.closed_days)]))
    if st.session_state.open_days:
        st.markdown("**特別開館日：** " + "、".join([f"{d}(週{WD[d.weekday()]})" for d in sorted(st.session_state.open_days)]))
    if st.button("← 返回", key="bk_h"): nav("admin")

def page_admin_export():
    st.markdown("## 📥 下載值班表 Excel")
    st.caption("將開放月份內所有有登記姓名的值班資料匯出為 Excel。")
    zone_names = st.session_state.zone_names
    rows = []
    bookings = st.session_state.bookings
    for key, val in bookings.items():
        if key.startswith("SYS_"): continue
        val = val.strip()
        if not val: continue
        parts = key.split("_")
        if len(parts) != 4: continue
        d_str, shift, z_id, slot = parts
        if z_id not in INTERNAL_ZONES: continue
        try:
            d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
        except: continue
        min_d, max_d = open_bounds()
        if d_obj < min_d or d_obj > max_d: continue
        z_idx    = INTERNAL_ZONES.index(z_id)
        z_name   = zone_names[z_idx] if z_idx < len(zone_names) else z_id
        weekday  = f"週{WD[d_obj.weekday()]}"
        date_lbl = f"{d_obj.month}/{d_obj.day}({weekday})"
        rows.append({"日期": d_obj, "日期顯示": date_lbl, "星期": weekday, "時段": shift, "區域": z_name, "姓名": val, "名額": slot})
    if not rows:
        st.info("目前開放月份內尚無任何值班登記。")
    else:
        df = (pd.DataFrame(rows).sort_values(["日期","時段","區域","名額"]).reset_index(drop=True))
        df_out = df[["日期顯示","星期","時段","區域","姓名"]].copy()
        df_out.columns = ["日期","星期","上下午","區域","姓名"]
        st.dataframe(df_out, use_container_width=True, hide_index=True)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df_out.to_excel(writer, index=False, sheet_name="值班表")
            ws_xl = writer.sheets["值班表"]
            for col in ws_xl.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                ws_xl.column_dimensions[col[0].column_letter].width = max_len + 4
        buf.seek(0)
        st.download_button(label="⬇️ 下載 Excel", data=buf, file_name=f"志工值班表_{date.today()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    if st.button("← 返回", key="bk_ex"): nav("admin")

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
    new_names = []
    for i in range(6):
        new_names.append(st.text_input(f"區域 {i+1}", value=st.session_state.zone_names[i], key=f"zn_{i}"))
    if st.button("✅ 儲存",type="primary"):
        st.session_state.zone_names = new_names
        save_data("SYS_ZONE_NAMES",json.dumps(new_names))
        st.success("已更新！"); st.rerun()
    if st.button("← 返回",key="bk_zn"): nav("admin")

# ── Router ─────────────────────────────────────────────────
{
    "calendar":       page_calendar,
    "week_grid":      page_week_grid,
    "admin_login":    page_admin_login,
    "admin":          page_admin,
    "admin_months":   page_admin_months,
    "admin_holidays": page_admin_holidays,
    "admin_ann":      page_admin_ann,
    "admin_zones":    page_admin_zones,
    "admin_export":   page_admin_export,
}.get(st.session_state.get("page","calendar"), page_calendar)()
