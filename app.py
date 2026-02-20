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
/* 1. 基礎清理 */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"], [data-testid="stDecoration"], section[data-testid="stSidebar"] { display: none !important; }

/* 2. 背景與主容器設定 */
.stApp { background-color: #e8e3d8 !important; }
.block-container {
    padding-top: 10px !important;
    padding-bottom: 30px !important;
    padding-left: 4px !important;
    padding-right: 4px !important;
    max-width: 500px !important; /* 鎖定最大寬度 */
    margin: 0 auto !important;
}

/* ==============================================
   🎯 日曆頁面樣式 (Calendar)
   ============================================== */

/* 針對日曆網格 (7個欄位) */
div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) {
    display: grid !important;
    grid-template-columns: repeat(7, 1fr) !important;
    gap: 2px !important;
    width: 100% !important;
    margin-bottom: 5px !important;
}

div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) > div[data-testid="column"] {
    min-width: 0px !important;
    width: auto !important;
    padding: 0 !important;
    margin: 0 !important;
    display: flex;
    justify-content: center;
}

/* 日曆按鈕 */
div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) button {
    width: 100% !important;
    min-width: 0px !important;
    padding: 0px !important;
    aspect-ratio: 1 / 1 !important;
    height: auto !important;
    display: flex;
    align-items: center;
    justify-content: center;
    line-height: 1 !important;
    border-radius: 4px !important;
    border: 1px solid #ccc !important;
    font-weight: 600 !important;
}

/* 針對導航列 (3個欄位) */
div[data-testid="stHorizontalBlock"]:has(> div:nth-child(3):last-child) {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
}
div[data-testid="stHorizontalBlock"]:has(> div:nth-child(3):last-child) button {
    border: none !important;
    background: transparent !important;
    font-size: 20px !important;
    color: #555 !important;
    box-shadow: none !important;
}

/* 手機版微調 */
@media (max-width: 450px) {
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) button { font-size: 13px !important; }
    div[data-testid="stHorizontalBlock"]:has(> div:nth-child(7)) button p { font-size: 13px !important; }
    .day-header { font-size: 11px !important; }
    .nav-label { font-size: 18px !important; }
}

/* ==============================================
   🎯 排班表頁面樣式 (Week Grid) - 本次修改重點
   ============================================== */

/* 1. 上下午切換按鈕 (緊貼) */
.shift-toggle-wrap {
    display: flex;
    gap: 0px; /* 移除間距 */
    margin-bottom: 10px;
    background: white;
    border-radius: 8px;
    padding: 2px;
    border: 1px solid #ccc;
}
.shift-btn {
    flex: 1;
    border: none;
    background: transparent;
    padding: 8px 0;
    font-weight: 700;
    font-size: 14px;
    border-radius: 6px;
    color: #555;
    cursor: pointer;
    text-align: center;
}
.shift-btn.active {
    background: #222;
    color: white;
}

/* 2. 表格樣式優化 */
.wk-wrap { overflow-x: auto; margin: 0 0 10px 0; }
.wk-tbl { 
    border-collapse: collapse; 
    width: 100%; 
    font-size: 12px; 
    table-layout: fixed; /* 固定佈局，確保格子大小一致 */
}

/* 表頭：允許換行 */
.wk-tbl th { 
    border: 1px solid #333; 
    padding: 4px 2px; 
    text-align: center; 
    background: #eee; 
    font-weight: 600;
    white-space: normal; /* 允許換行 */
    word-wrap: break-word; /* 強制換行 */
    vertical-align: middle;
    height: 35px;
}

/* 表格內容 */
.wk-tbl td { 
    border: 1px solid #333; 
    padding: 2px; 
    text-align: center; 
    vertical-align: middle;
    height: 45px; /* 固定高度，讓每個格子一樣大 */
}

/* 日期格 */
.wk-date-cell { 
    background: #f5f5f5; 
    font-weight: 700; 
    font-size: 11px;
    width: 35px; /* 固定日期欄寬度 */
}

/* 填寫名字的格子 */
.wk-filled-cell { background: #FFD700; }
.wk-empty-cell { background: #FFF; }

/* 休館日格子 */
.wk-closed-cell { 
    background: #e0e0e0; 
    color: #999;
    font-size: 10px;
    letter-spacing: 1px;
    background-image: repeating-linear-gradient(45deg, transparent, transparent 5px, #ccc 5px, #ccc 6px);
}

/* 人名樣式 (放大、無編號) */
.vol-name {
    font-size: 14px; /* 放大字體 */
    font-weight: 600;
    color: #000;
    display: block;
    line-height: 1.2;
}

/* 選中格子的紅框 */
.sel-border {
    outline: 2px solid #cc0000;
    outline-offset: -2px;
}

/* 其他通用 UI */
.day-header { text-align: center; font-size: 13px; font-weight: 700; color: #666; margin-bottom: 2px; }
.day-header.sunday { color: #cc0000; }
.nav-label { font-size: 20px; font-weight: 700; text-align: center; color: #333; white-space: nowrap; line-height: 40px; }
button:disabled { background-color: #e5e5e5 !important; color: #bbb !important; cursor: not-allowed !important; opacity: 0.6 !important; border: 1px solid #ddd !important; }
button[kind="primary"] { background-color: #ef4444 !important; color: white !important; border: none !important; }
.enter-btn-wrap button { background-color: white !important; color: #333 !important; border: 1.5px solid #333 !important; margin-top: 15px !important; height: 48px !important; width: 100% !important; font-size: 16px !important; }
.ann-box { background: white; border: 2px solid #333; border-radius: 6px; margin: 15px 0; }
.ann-title { border-bottom: 1.5px solid #333; padding: 8px; font-weight: 700; text-align: center; }
.ann-body { padding: 12px; font-size: 14px; color: #333; line-height: 1.6; }
.edit-bar { background: #f0f0f0; border-radius: 8px; padding: 10px; margin: 6px 0; }
.bot-join { background: #4ECDC4; border-radius: 10px; padding: 10px; text-align: center; font-weight: 600; color: #111; }
.admin-access-wrap button { background: transparent !important; color: #aaa !important; border: none !important; font-size: 12px !important; }

</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────
ZONES   = ["1F-沉浸室劇場","1F-手扶梯驗票","2F展區、特展","3F-展區","4F-展區","5F-閱讀區"]
ZONES_S = ["1F沉浸","1F驗票","2F特展","3F展","4F展","5F閱"]
ADMIN_PW = "1234"
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
    sel_cell = st.session_state.sel_cell

    st.markdown(f"<div class='wk-title'>志工排班表</div>", unsafe_allow_html=True)
    st.caption(f"{MON_EN[cm]} {cy}")

    # (1) 上下午按鈕：改用 CSS 製作的緊密切換器
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🌞 上午", key="t_am", use_container_width=True, type="primary" if shift=="上午" else "secondary"):
            st.session_state.grid_shift = "上午"; st.rerun()
    with c2:
        if st.button("🌤️ 下午", key="t_pm", use_container_width=True, type="primary" if shift=="下午" else "secondary"):
            st.session_state.grid_shift = "下午"; st.rerun()

    # Grid HTML table
    time_lbl = "09:00-12:00" if shift=="上午" else "14:00-17:00"
    
    # 建立表格
    html  = '<div class="wk-wrap"><table class="wk-tbl">'
    html += f'<tr><th colspan="7" style="background:#ddd;font-size:12px;padding:4px;">{shift}（{time_lbl}）</th></tr>'
    
    # 表頭：日期 + 區域
    html += '<tr><th class="wk-hdr-zone" style="width:35px;">日期</th>'
    for zs in ZONES_S: 
        html += f'<th class="wk-hdr-zone">{zs}</th>'
    html += '</tr>'

    for day in week_days:  
        d_str  = day.strftime('%Y-%m-%d')
        closed = not is_open(day)
        lbl    = f"{day.month}/{day.day}<br>({WD[day.weekday()]})"
        if closed: lbl += '<br><span style="color:#c00;font-size:8px;">休</span>'

        if closed:
            # (2) 休館日：只生成一列，高度加倍，中間無線，不顯示格子
            # 這裡設定 height: 90px (45px * 2) 讓它看起來跟兩列一樣高
            html += f'<tr><td class="wk-date-cell" style="height:90px;">{lbl}</td>'
            # 橫跨所有區域，顯示休館斜線或灰色
            html += f'<td colspan="{len(ZONES)}" class="wk-closed-cell">休 館</td>'
            html += '</tr>'
        else:
            # 開館日：生成兩列 (Slot 1 & Slot 2)
            # Row 1 (Slot 1)
            html += f'<tr><td class="wk-date-cell" rowspan="2">{lbl}</td>'
            for z in ZONES:
                k = f"{d_str}_{shift}_{z}_1"
                v = st.session_state.bookings.get(k,"").strip()
                
                # 樣式判斷
                sc = " sel-border" if k==sel_cell else ""
                cls = "wk-filled-cell" if v else "wk-empty-cell"
                
                # (4) 人名顯示：拿掉數字，字體放大 (.vol-name)
                ct = f"<span class='vol-name'>{v}</span>" if v else ""
                html += f'<td class="{cls}{sc}">{ct}</td>'
            html += '</tr>'

            # Row 2 (Slot 2)
            html += '<tr>'
            for z in ZONES:
                k = f"{d_str}_{shift}_{z}_2"
                v = st.session_state.bookings.get(k,"").strip()
                
                sc = " sel-border" if k==sel_cell else ""
                cls = "wk-filled-cell" if v else "wk-empty-cell"
                ct = f"<span class='vol-name'>{v}</span>" if v else ""
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
            lbl = f"{parts[0]}({WD[d_obj.weekday()]}) {parts[1]} {'_'.join(parts[2:-1])}"
        except: lbl = sel_cell

        st.markdown('<div class="edit-bar">', unsafe_allow_html=True)
        st.markdown(f"<b>📍 {lbl}</b><br><small style='color:#666'>↓ 輸入名字後儲存</small>", unsafe_allow_html=True)
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
            sl = st.selectbox("名額", ["1","2"], format_func=lambda s: f"名額{s}", key="pk_sl")
            if st.button("📌 選取此格", key="pick", type="primary", use_container_width=True):
                k = f"{open_days[di].strftime('%Y-%m-%d')}_{sf}_{ZONES[zn]}_{sl.replace('名額','')}"
                st.session_state.sel_cell = k; st.session_state.grid_shift = sf; st.rerun()

    # Bottom bar
    bc1, bc2 = st.columns([3,2])
    bc1.markdown('<div class="bot-join">加入或取消值班<br><small>（點選想要的格子）</small></div>', unsafe_allow_html=True)
    with bc2:
        if st.button("退出畫面", key="exit_g", use_container_width=True):
            st.session_state.page = "calendar"; st.session_state.sel_cell = None; st.rerun()

# ─────────────────────────────────────────
#  ADMIN PAGES (略)
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
