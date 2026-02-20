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
#  GLOBAL CSS (核心修改：強制手機版維持網格佈局)
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
    padding: 20px 10px 60px 10px !important;
    max-width: 600px !important; /* 稍微放寬以容納電腦版樣式 */
    margin: 0 auto !important;
}

/* ── Font ─── */
html, body, [class*="css"] {
    font-family: -apple-system, "PingFang TC", "Noto Sans TC", "Helvetica Neue", sans-serif;
}

/* ⭐⭐⭐ 核心修改：強制手機版 Columns 不換行 ⭐⭐⭐ 
   Streamlit 預設手機會把 columns 變成直排，這裡強制改回橫排 
*/
div[data-testid="column"] {
    min-width: 0px !important; /* 允許縮到非常小 */
    flex: 1 1 0px !important;  /* 平均分配寬度 */
    padding: 0 1px !important; /* 減少欄位間距 */
}

div[data-testid="stHorizontalBlock"] {
    gap: 2px !important; /* 減少元件間距 */
}

/* 針對按鈕的優化 */
div[data-testid="stButton"] button {
    padding: 0px !important;
    width: 100% !important;
    min-height: 45px !important; /* 電腦版高度 */
    height: 45px !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
    box-shadow: none !important;
    border: 1px solid #e0e0e0;
}

/* 手機版特定調整 (螢幕小於 640px) */
@media (max-width: 640px) {
    div[data-testid="stHorizontalBlock"] {
        flex-direction: row !important; /* 強制橫向 */
        flex-wrap: nowrap !important;
    }
    div[data-testid="stButton"] button {
        min-height: 40px !important; /* 手機版按鈕稍微矮一點 */
        height: 40px !important;
        font-size: 14px !important;  /* 字體縮小以免被切掉 */
    }
    /* 導航列字體縮小 */
    .nav-label { font-size: 18px !important; min-width: 120px !important; }
}

/* ── Calendar Styles ─── */
.day-header {
    text-align: center;
    font-size: 13px;
    font-weight: 700;
    color: #666;
    margin-bottom: 2px;
}
.day-header.sunday { color: #cc0000; }

/* Month Navigation styling */
.nav-row {
    display: flex;
    justify-content: center;
    align-items: center;
    margin-bottom: 15px;
}
.nav-label {
    font-size: 22px;
    font-weight: 700;
    text-align: center;
    color: #333;
    padding: 0 10px;
    white-space: nowrap;
}

/* Disabled button styling (休館日) */
button:disabled {
    background-color: #e8e8e8 !important;
    color: #bbb !important;
    border: none !important;
    cursor: not-allowed !important;
    opacity: 0.6 !important;
}

/* Selected button styling (Primary) */
button[kind="primary"] {
    background-color: #ef4444 !important; /* 紅色 */
    color: white !important;
    border: none !important;
}

/* ── Enter Button ─── */
.enter-btn-wrap button {
    background-color: #fff !important;
    color: #333 !important;
    border: 1px solid #ccc !important;
    font-size: 16px !important;
    font-weight: 500 !important;
    height: 48px !important;
    border-radius: 8px !important;
    margin-top: 20px !important;
}

/* ── Admin & Other UI ─── */
.ann-box {
    background: white; border: 2px solid #333; border-radius: 6px;
    margin-top: 16px; margin-bottom: 14px;
}
.ann-title { border-bottom: 1.5px solid #333; padding: 9px 16px; font-weight: 700; text-align: center; }
.ann-body { padding: 14px 16px; min-height: 60px; font-size: 14px; white-space: pre-wrap; line-height: 1.7; color: #333; }

/* Grid table styles */
.wk-wrap { overflow-x: auto; margin: 8px 0; }
.wk-tbl { border-collapse: collapse; font-size: 10px; width: 100%; }
.wk-tbl th, .wk-tbl td { border: 1.5px solid #333; padding: 2px 1px; text-align: center; vertical-align: middle; }
.wk-date-cell { background: #f5f5f5; font-size: 10px; line-height: 1.3; }
.wk-filled-cell { background: #FFD700; font-size: 9px; }
.wk-empty-cell { background: #FFE033; height: 16px; }
.edit-bar { background: #f0f0f0; border-radius: 8px; padding: 10px 12px; margin: 6px 0; }
.bot-join { background: #4ECDC4; border-radius: 10px; padding: 14px 10px; text-align: center; font-weight: 600; color: #111; }
.admin-access-wrap button { background: transparent !important; color: #999 !important; border: none !important; font-size: 12px !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────
ZONES   = ["1F-沉浸室劇場","1F-手扶梯驗票","2F展區、特展","3F-展區","4F-展區","5F-閱讀區"]
ZONES_S = ["1F沉浸","1F驗票","2F特展","3F展","4F展","5F閱"]
ADMIN_PW = "1234"
# WD: 0=Mon, 6=Sun
WD = {0:"一",1:"二",2:"三",3:"四",4:"五",5:"六",6:"日"}
MON_EN = ["","January","February","March","April","May","June",
           "July","August","September","October","November","December"]

# ─────────────────────────────────────────
#  GOOGLE SHEETS & DATA
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
    st.session_state.page           = "calendar"
    st.session_state.month_idx      = 0
    st.session_state.sel_week_start = None
    st.session_state.sel_cell       = None
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
    return d - timedelta(days=d.weekday()) # Monday

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
    today  = date.today()

    st.markdown("## 志工排班表")

    if not months:
        st.warning("⚠️ 暫無開放月份，請管理員設定。")
        _admin_btn(); return

    idx = min(st.session_state.month_idx, len(months)-1)
    year, month = months[idx]
    weeks = get_weeks(year, month)
    
    sel_start = st.session_state.sel_week_start

    # ── Month Navigation (Aligned Row) ──
    # 使用 columns 排列：[<] [Month Year] [>]
    c_nav = st.container()
    col_l, col_m, col_r = c_nav.columns([1.5, 5, 1.5])
    
    with col_l:
        if st.button("◀", key="prev_m", disabled=(idx==0), use_container_width=True):
            st.session_state.month_idx = idx-1
            st.session_state.sel_week_start = None
            st.rerun()
        
    with col_m:
        st.markdown(f'<div class="nav-label">{MON_EN[month]} {year}</div>', unsafe_allow_html=True)
        
    with col_r:
        if st.button("▶", key="next_m", disabled=(idx>=len(months)-1), use_container_width=True):
            st.session_state.month_idx = idx+1
            st.session_state.sel_week_start = None
            st.rerun()

    st.write("") # Spacer

    # ── Calendar Header (Mon-Sun) ──
    hcols = st.columns(7)
    days_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for i, label in enumerate(days_labels):
        cls = "day-header sunday" if i == 6 else "day-header"
        hcols[i].markdown(f'<div class="{cls}">{label}</div>', unsafe_allow_html=True)

    # ── Calendar Days Grid ──
    for ws, days in weeks:
        is_selected = (sel_start == ws)
        # 如果是選取狀態，所有按鈕變成 Primary (紅色)，否則 Secondary (白色/灰色)
        btn_type = "primary" if is_selected else "secondary"
        
        dcols = st.columns(7)
        for i, d in enumerate(days):
            with dcols[i]:
                # 1. 檢查是否為當月
                if d.month != month:
                    # 如果不是當月，顯示空白，保持版面整齊但不顯示按鈕
                    st.empty()
                else:
                    # 2. 檢查是否休館
                    is_closed = not is_open(d)
                    label = str(d.day)
                    
                    # 點擊按鈕：選擇該週 (ws)
                    # disabled=is_closed (如果是休館日，按鈕失效)
                    if st.button(label, key=f"btn_{d}", type=btn_type, disabled=is_closed, use_container_width=True):
                        st.session_state.sel_week_start = ws
                        st.rerun()

    # ── Enter Scheduling Button ──
    # 只有當選擇了某一週時才出現
    if sel_start:
        w_end = sel_start + timedelta(days=6)
        lbl = f"進入排班 ({sel_start.month}/{sel_start.day} ～ {w_end.month}/{w_end.day})"
        
        st.markdown('<div class="enter-btn-wrap">', unsafe_allow_html=True)
        if st.button(lbl, key="enter_grid", use_container_width=True):
            st.session_state.sel_week_sun = sel_start 
            st.session_state.page = "week_grid"
            st.session_state.sel_cell = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Announcement ──
    ann = st.session_state.announcement.replace("<","&lt;").replace(">","&gt;")
    st.markdown(f'<div class="ann-box"><div class="ann-title">公告</div><div class="ann-body">{ann}</div></div>', unsafe_allow_html=True)

    _admin_btn()


def _admin_btn():
    st.markdown('<div class="admin-access-wrap" style="text-align:center;">', unsafe_allow_html=True)
    if st.button("管理員登入", key="admin_access"):
        nav("admin_login")
    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────
#  PAGE: WEEK GRID (排班表)
# ─────────────────────────────────────────
def page_week_grid():
    ws = st.session_state.get("sel_week_start") 
    if not ws: ws = st.session_state.get("sel_week_sun")
    if ws is None: nav("calendar"); return

    week_days = [ws + timedelta(days=i) for i in range(7)]
    months = sorted(st.session_state.open_months_list)
    cy, cm = months[min(st.session_state.month_idx, len(months)-1)]
    shift    = st.session_state.grid_shift
    sel_cell = st.session_state.sel_cell

    st.markdown(f"<div class='wk-title'>志工排班表</div>", unsafe_allow_html=True)
    st.caption(f"{MON_EN[cm]} {cy}　可切換上下午查看排班狀況 ↓")

    # Shift toggle
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
    for zs in ZONES_S: html += f'<th class="wk-hdr-zone">{zs}</th>'
    html += '</tr>'

    for day in week_days:  
        d_str  = day.strftime('%Y-%m-%d')
        closed = not is_open(day)
        lbl    = f"{day.month}/{day.day}<br>({WD[day.weekday()]})"
        if closed: lbl += '<br><span style="color:#c00;font-size:8px;">休</span>'

        html += f'<tr><td class="wk-date-cell" rowspan="2">{lbl}</td>'
        for slot in ["1", "2"]:
            if slot == "2": html += '<tr>' 
            for z in ZONES:
                k = f"{d_str}_{shift}_{z}_{slot}"
                v = st.session_state.bookings.get(k,"").strip()
                if closed:
                    html += '<td class="wk-closed-cell"></td>'
                else:
                    sc  = " wk-sel-cell" if k==sel_cell else ""
                    cls = "wk-filled-cell" if v else "wk-empty-cell"
                    ct  = f"<small>{slot}.{v}</small>" if v else ""
                    html += f'<td class="{cls}{sc}">{ct}</td>'
            html += '</tr>'
    
    html += '</table></div>'
    st.markdown(html, unsafe_allow_html=True)

    # Edit bar
    if sel_cell:
        parts = sel_cell.split("_")
        cur_val = st.session_state.bookings.get(sel_cell,"")
        try:
            d_obj = datetime.strptime(parts[0],"%Y-%m-%d").date()
            lbl = f"{parts[0]}({WD[d_obj.weekday()]}) {parts[1]} {'_'.join(parts[2:-1])} 志工{parts[-1]}"
        except: lbl = sel_cell

        st.markdown('<div class="edit-bar">', unsafe_allow_html=True)
        st.markdown(f"<b>📍 {lbl}</b><br><small style='color:#666'>↓ 也可以刪除已輸入的名字後儲存取消排班</small>", unsafe_allow_html=True)
        ei1, ei2, ei3 = st.columns([2,4,1])
        ei1.markdown("<div style='padding-top:8px;font-weight:700;font-size:13px;'>輸入姓名</div>", unsafe_allow_html=True)
        new_nm = ei2.text_input("姓名", cur_val, key=f"nm_{sel_cell}", label_visibility="collapsed", placeholder="輸入姓名")
        with ei3:
            if st.button("儲存", key="save_c", type="primary"):
                fresh = load_data()
                cloud = fresh.get(sel_cell,"")
                old   = st.session_state.bookings.get(sel_cell,"")
                if cloud.strip() and cloud != old:
                    st.error(f"⚠️ 此格已被「{cloud}」先排班！")
                    st.session_state.bookings[sel_cell] = cloud; st.rerun()
                else:
                    st.session_state.bookings[sel_cell] = new_nm
                    save_data(sel_cell, new_nm)
                    st.session_state.sel_cell = None; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Cell picker
    open_days = [d for d in week_days if is_open(d)]
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
                st.session_state.sel_cell = k; st.session_state.grid_shift = sf; st.rerun()

    # Bottom bar
    bc1, bc2 = st.columns([3,2])
    bc1.markdown('<div class="bot-join">加入或取消值班<br><small>（點選想要的格子）</small></div>', unsafe_allow_html=True)
    with bc2:
        if st.button("退出畫面", key="exit_g", use_container_width=True):
            st.session_state.page = "calendar"; st.session_state.sel_cell = None; st.rerun()

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
    for label, dest in [("管理開放月份","admin_months"),("休館設定","admin_holidays"),("公告修改","admin_ann")]:
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
