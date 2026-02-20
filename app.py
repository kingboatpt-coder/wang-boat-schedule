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
#  GLOBAL CSS (針對手機直立模式的極限修正)
# ─────────────────────────────────────────
st.markdown("""
<style>
/* 1. 隱藏不必要的元件，爭取空間 */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"], [data-testid="stDecoration"], section[data-testid="stSidebar"] { display: none !important; }

/* 2. 主容器設定：確保在手機上貼邊顯示 */
.stApp { background-color: #e8e3d8 !important; }
.block-container {
    padding-top: 10px !important;
    padding-bottom: 20px !important;
    padding-left: 2px !important;  /* 極限貼邊 */
    padding-right: 2px !important; /* 極限貼邊 */
    max-width: 100% !important;
}

/* ⭐⭐⭐ 核心：解決手機直立超出螢幕的問題 ⭐⭐⭐ */

/* 讓存放7個格子的容器強制橫排，且不允許溢出 */
div[data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-wrap: nowrap !important; /* 絕對禁止換行 */
    width: 100% !important;
    gap: 1px !important;          /* 格子間僅留 1px 縫隙 */
    justify-content: space-between !important;
}

/* 強制每個格子 (Column) 寬度鎖死為 1/7 */
div[data-testid="column"] {
    flex: 1 1 0px !important;     /* 讓所有格子平分空間 */
    width: 14.2% !important;      /* 鎖定寬度百分比 */
    min-width: 0px !important;    /* 允許縮到無限小，這點最重要 */
    max-width: 14.2% !important;  /* 不准變大 */
    padding: 0 !important;
    margin: 0 !important;
    overflow: hidden !important;  /* 內容太大就切掉，不要撐開 */
}

/* 按鈕本體設定 */
div[data-testid="stButton"] {
    width: 100% !important;
}

div[data-testid="stButton"] button {
    width: 100% !important;
    min-width: 0px !important;
    padding: 0px !important;      /* 移除內距 */
    margin: 0px !important;
    border-radius: 4px !important;
    border: 1px solid #ccc !important;
    display: flex;
    align-items: center;
    justify-content: center;
    line-height: 1 !important;
    box-shadow: none !important;
}

/* 內層文字設定：這也是撐開的主因之一 */
div[data-testid="stButton"] button p {
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1 !important;
}

/* 📱 手機版特定調整 (螢幕寬度 < 500px，即直立模式) */
@media (max-width: 500px) {
    /* 按鈕高度與字體縮小 */
    div[data-testid="stButton"] button {
        height: 38px !important;      /* 固定高度 */
        font-size: 13px !important;   /* 字體縮小 */
    }
    
    /* 強制 Streamlit 內部文字也縮小 */
    div[data-testid="stButton"] button p {
        font-size: 13px !important;
    }

    /* 星期標題縮小 */
    .day-header {
        font-size: 11px !important;
        margin-bottom: 2px !important;
    }
    
    /* 導航列 (月份) 縮小 */
    .nav-label {
        font-size: 18px !important;
    }
}

/* 💻 電腦版調整 (螢幕寬度 > 500px) */
@media (min-width: 501px) {
    .block-container { max-width: 500px !important; padding: 20px !important; }
    div[data-testid="stButton"] button { height: 48px !important; font-size: 16px !important; }
    div[data-testid="stHorizontalBlock"] { gap: 4px !important; }
}

/* ── 其他 UI 美化 ── */
.day-header { text-align: center; font-weight: 700; color: #666; margin-bottom: 4px; }
.day-header.sunday { color: #cc0000; }
.nav-label { font-weight: 700; text-align: center; color: #333; white-space: nowrap; }

button:disabled {
    background-color: #e5e5e5 !important; color: #bbb !important;
    border: 1px solid #ddd !important; cursor: not-allowed !important; opacity: 0.8 !important;
}
button[kind="primary"] {
    background-color: #ef4444 !important; color: white !important; border: none !important;
}

/* 進入排班按鈕 */
.enter-btn-wrap button {
    background-color: white !important; color: #333 !important;
    border: 1.5px solid #333 !important; margin-top: 20px !important;
    height: 48px !important; width: 100% !important; font-size: 16px !important;
}

/* 公告與表格 */
.ann-box { background: white; border: 2px solid #333; border-radius: 6px; margin: 15px 0; }
.ann-title { border-bottom: 1.5px solid #333; padding: 8px; font-weight: 700; text-align: center; }
.ann-body { padding: 12px; font-size: 14px; line-height: 1.6; color: #333; }

.wk-title { font-size: 20px; font-weight: 700; margin: 10px 5px; }
.wk-wrap { overflow-x: auto; margin: 5px 0; }
.wk-tbl { border-collapse: collapse; width: 100%; font-size: 11px; }
.wk-tbl th, .wk-tbl td { border: 1px solid #333; padding: 4px 2px; text-align: center; }
.wk-filled-cell { background: #FFD700; }
.wk-empty-cell { background: #FFE033; height: 20px; }
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
# WD: 0=Mon, 6=Sun
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

    # ── Month Navigation (使用 columns 來排列) ──
    c_nav = st.container()
    c1, c2, c3 = c_nav.columns([1, 4, 1])
    
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

    # ── Days Header (7列) ──
    # 使用 container 包裹，確保 CSS 選擇器生效
    with st.container():
        header_cols = st.columns(7)
        days_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, label in enumerate(days_labels):
            cls = "day-header sunday" if i == 6 else "day-header"
            header_cols[i].markdown(f'<div class="{cls}">{label}</div>', unsafe_allow_html=True)

        # ── Calendar Grid ──
        for ws, days in weeks:
            is_selected = (sel_start == ws)
            btn_type = "primary" if is_selected else "secondary"

            dcols = st.columns(7)
            
            for i, d in enumerate(days):
                with dcols[i]:
                    # 1. 隱藏非本月
                    if d.month != month:
                        st.empty() 
                    else:
                        # 2. 判斷休館
                        is_closed = not is_open(d)
                        label = str(d.day)
                        
                        # 3. 按鈕
                        if st.button(label, key=f"btn_{d}", type=btn_type, disabled=is_closed, use_container_width=True):
                            st.session_state.sel_week_start = ws
                            st.rerun()

    # ── Enter Scheduling Button ──
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
#  PAGE: WEEK GRID
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
    html += f'<tr><th colspan="7" style="background:#ddd;font-size:12px;padding:4px;">{shift}（{time_lbl}）</th></tr>'
    html += '<tr><th class="wk-hdr-zone">日期</th>'
    for zs in ZONES_S: html += f'<th class="wk-hdr-zone">{zs}</th>'
    html += '</tr>'

    for day in week_days:  
        d_str  = day.strftime('%Y-%m-%d')
        closed = not is_open(day)
        lbl    = f"{day.month}/{day.day}<br>({WD[day.weekday()]})"
        if closed: lbl += '<br><span style="color:#c00;font-size:8px;">休</span>'

        html += f'<tr><td rowspan="2" style="background:#f9f9f9;">{lbl}</td>'
        for slot in ["1", "2"]:
            if slot == "2": html += '<tr>' 
            for z in ZONES:
                k = f"{d_str}_{shift}_{z}_{slot}"
                v = st.session_state.bookings.get(k,"").strip()
                if closed:
                    html += '<td style="background:#ddd;"></td>'
                else:
                    sc  = " border:2px solid #c00 !important;" if k==sel_cell else ""
                    cls = "wk-filled-cell" if v else "wk-empty-cell"
                    ct  = f"<small>{slot}.{v}</small>" if v else ""
                    html += f'<td class="{cls}" style="{sc}">{ct}</td>'
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
