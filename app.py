import streamlit as st
import pandas as pd
from datetime import date, datetime
import calendar
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- 1. 頁面設定 ---
st.set_page_config(page_title="王船文化館排班系統", page_icon="🚢", layout="wide")

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
[data-testid="stElementToolbar"] { display: none; }

/* ==========================================
   🎨 折疊卡片樣式
   ========================================== */

/* 點位卡片標題列：顯示已排人數徽章 */
.zone-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 15px;
    font-weight: bold;
}

/* 已排人數 badge */
.badge-full  { background:#4CAF50; color:white; padding:2px 8px; border-radius:12px; font-size:12px; }
.badge-part  { background:#FF9800; color:white; padding:2px 8px; border-radius:12px; font-size:12px; }
.badge-empty { background:#9E9E9E; color:white; padding:2px 8px; border-radius:12px; font-size:12px; }

/* 讓 expander 內部更緊湊 */
div[data-testid="stExpander"] > details > summary {
    padding: 10px 14px !important;
}
</style>
""", unsafe_allow_html=True)

# --- 2. 連接 Google Sheets ---
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
                for _, row in df.iterrows():
                    booking_dict[str(row["key"])] = str(row["value"])
        return booking_dict
    except:
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

# --- 3. 初始化參數 ---
ZONES = ["1F-沉浸室劇場", "1F-手扶梯驗票", "2F展區、特展", "3F-展區", "4F-展區", "5F-閱讀區"]
ADMIN_PASSWORD = "1234"
MAX_SLOTS = 2
TIME_MAPPING = {"上午": "上午 09:00–12:00", "下午": "下午 14:00–17:00"}
WEEKDAY_MAP = {0: "一", 1: "二", 2: "三", 3: "四", 4: "五", 5: "六", 6: "日"}

if 'bookings' not in st.session_state:
    raw_data = load_data()
    st.session_state.bookings = raw_data

    if "SYS_OPEN_MONTHS" in raw_data:
        try:
            loaded_m = json.loads(raw_data["SYS_OPEN_MONTHS"])
            st.session_state.open_months_list = [(m[0], m[1]) for m in loaded_m]
        except:
            st.session_state.open_months_list = [(2026, 3)]
    else:
        st.session_state.open_months_list = [(2026, 3)]

    if "SYS_CLOSED_DAYS" in raw_data:
        try:
            st.session_state.closed_days = [datetime.strptime(d, "%Y-%m-%d").date() for d in json.loads(raw_data["SYS_CLOSED_DAYS"])]
        except:
            st.session_state.closed_days = []
    else:
        st.session_state.closed_days = []

    if "SYS_OPEN_DAYS" in raw_data:
        try:
            st.session_state.open_days = [datetime.strptime(d, "%Y-%m-%d").date() for d in json.loads(raw_data["SYS_OPEN_DAYS"])]
        except:
            st.session_state.open_days = []
    else:
        st.session_state.open_days = []

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
            try:
                st.session_state.open_months_list = [(m[0], m[1]) for m in json.loads(new_data["SYS_OPEN_MONTHS"])]
            except:
                pass
        if "SYS_CLOSED_DAYS" in new_data:
            try:
                st.session_state.closed_days = [datetime.strptime(d, "%Y-%m-%d").date() for d in json.loads(new_data["SYS_CLOSED_DAYS"])]
            except:
                pass
        if "SYS_OPEN_DAYS" in new_data:
            try:
                st.session_state.open_days = [datetime.strptime(d, "%Y-%m-%d").date() for d in json.loads(new_data["SYS_OPEN_DAYS"])]
            except:
                pass
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
            if not current_list:
                st.warning("未開放月份")
            else:
                st.write("、".join([f"{y}年{m}月" for y, m in current_list]))
            c1, c2, c3 = st.columns([2, 2, 2])
            add_y = c1.number_input("年", 2025, 2030, 2026)
            add_m = c2.selectbox("月", range(1, 13), 2)
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
                    y, m = s.replace("月", "").split("年")
                    target = (int(y), int(m))
                    if target in st.session_state.open_months_list:
                        st.session_state.open_months_list.remove(target)
                save_data("SYS_OPEN_MONTHS", json.dumps(st.session_state.open_months_list))
                st.rerun()

        with st.expander("⛔ 休館設定"):
            d_input = st.date_input("日期", min_value=date(2025, 1, 1))
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
            with st.expander("📊 點此展開本月總覽表 / 下載 Excel", expanded=False):
                st.caption("💡 空白的格子代表還有缺額，可直接點擊下方日期搶班。")
                overview_data = []
                download_data = []
                num_days = calendar.monthrange(year, month)[1]
                for day in range(1, num_days + 1):
                    d_obj = date(year, month, day)
                    status = "open"
                    if d_obj in st.session_state.closed_days:
                        status = "closed"
                    elif d_obj in st.session_state.open_days:
                        status = "open"
                    elif d_obj.weekday() == 0:
                        status = "closed"
                    if status == "open":
                        d_str = d_obj.strftime('%Y-%m-%d')
                        d_display = f"{d_str} ({WEEKDAY_MAP[d_obj.weekday()]})"
                        for shift in ["上午", "下午"]:
                            row_for_web = {"日期": f"{d_display} ({shift})"}
                            for z in ZONES:
                                names = []
                                for k in range(MAX_SLOTS):
                                    key = f"{d_str}_{shift}_{z}_{k+1}"
                                    val = st.session_state.bookings.get(key, "").strip()
                                    if val:
                                        names.append(val)
                                display_status = "、".join(names) if names else ""
                                row_for_web[z] = display_status
                                if names:
                                    download_data.append({"日期": d_display, "時段": shift, "排班點位": z, "志工姓名": display_status})
                            overview_data.append(row_for_web)

                if overview_data:
                    df_web = pd.DataFrame(overview_data)
                    cols_order = ["日期"] + ZONES
                    df_web = df_web[cols_order]
                    st.dataframe(df_web, use_container_width=True, hide_index=True, height=400)
                    if download_data:
                        df_download = pd.DataFrame(download_data)
                        csv_bytes = df_download.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(
                            label=f"📥 下載 {year}年{month}月 排班表 (已過濾空班)",
                            data=csv_bytes,
                            file_name=f"王船文化館排班表_{year}_{month:02d}.csv",
                            mime="text/csv",
                            type="primary"
                        )
                    else:
                        st.caption("ℹ️ 目前本月份尚未有志工登記排班，暫無資料可下載。")
                else:
                    st.info("本月份目前沒有開放日或排班資料。")

            with st.expander("🔍 點此查詢本月個人班表", expanded=False):
                sc1, sc2 = st.columns([3, 1])
                with sc1:
                    search_name = st.text_input("輸入姓名", key=f"search_{year}_{month}", placeholder="輸入姓名查詢 (例如：陳大明)", label_visibility="collapsed")
                with sc2:
                    do_search = st.button("🔍 查詢", key=f"btn_search_{year}_{month}", use_container_width=True)
                if do_search:
                    if search_name.strip():
                        target_prefix = f"{year}-{month:02d}"
                        found_shifts = []
                        for k, v in st.session_state.bookings.items():
                            if v.strip() and (search_name in v) and k.startswith(target_prefix) and not str(k).startswith("SYS_"):
                                parts = k.split("_")
                                if len(parts) >= 4:
                                    found_shifts.append({"日期": parts[0], "時段": parts[1], "區域": parts[2]})
                        if found_shifts:
                            st.success(f"🎉 找到 **{search_name}** 在本月的排班共 **{len(found_shifts)}** 筆：")
                            df_search = pd.DataFrame(found_shifts).sort_values(by=["日期", "時段", "區域"])
                            for _, row in df_search.iterrows():
                                d_obj_search = datetime.strptime(row['日期'], '%Y-%m-%d').date()
                                d_display_search = f"{row['日期']} ({WEEKDAY_MAP[d_obj_search.weekday()]})"
                                display_time = TIME_MAPPING.get(row['時段'], row['時段'])
                                st.markdown(f"- 📅 **{d_display_search}** ({display_time}) 📍 {row['區域']}")
                        else:
                            st.warning(f"本月沒有找到「{search_name}」的排班記錄喔！")
                    else:
                        st.info("⚠️ 請先輸入姓名，再點擊查詢按鈕喔！")

            st.write("---")

            cols = st.columns(7)
            for i, n in enumerate(["週一", "週二", "週三", "週四", "週五", "週六", "週日"]):
                cols[i].markdown(f"<div style='text-align:center;color:#666;font-size:12px;font-weight:bold;'>{n}</div>", unsafe_allow_html=True)
            st.write("---")
            for week in calendar.monthcalendar(year, month):
                cols = st.columns(7)
                for i, d in enumerate(week):
                    with cols[i]:
                        if d != 0:
                            curr = date(year, month, d)
                            status = "open"
                            if curr in st.session_state.closed_days:
                                status = "closed"
                            elif curr in st.session_state.open_days:
                                status = "open"
                            elif i == 0:
                                status = "closed"
                            if status == "closed":
                                st.markdown(f"<div style='background:#f0f0f0;color:#aaa;text-align:center;padding:5px 0px;border-radius:4px;'><strong>{d}</strong><br><small>休</small></div>", unsafe_allow_html=True)
                            else:
                                is_sel = (st.session_state.selected_date == curr)
                                if st.button(f"{d}", key=f"b_{year}_{month}_{d}", type="primary" if is_sel else "secondary", use_container_width=True):
                                    st.session_state.selected_date = curr
                                    st.rerun()

    for i, (yy, mm) in enumerate(sorted_months):
        render_cal(yy, mm, tabs[i])

    # ==========================================
    # ✍️ 選擇日期後：折疊式點位排班卡片
    # ==========================================
    if st.session_state.selected_date and (st.session_state.selected_date.year, st.session_state.selected_date.month) in sorted_months:
        d = st.session_state.selected_date
        d_str = d.strftime('%Y-%m-%d')

        st.divider()
        st.subheader(f"✍️ {d_str}（週{WEEKDAY_MAP[d.weekday()]}）排班登記")
        st.caption("展開點位卡片，填入姓名後按「💾 儲存」即可。")

        # --- 儲存按鈕（統一儲存） ---
        if st.button("💾 儲存本日所有排班", type="primary", use_container_width=True):
            fresh_db = load_data()
            changes_count = 0
            conflicts = []

            for shift in ["上午", "下午"]:
                for z in ZONES:
                    for k in range(MAX_SLOTS):
                        key = f"{d_str}_{shift}_{z}_{k+1}"
                        widget_key = f"in_{key}"
                        new_val = st.session_state.get(widget_key, st.session_state.bookings.get(key, ""))
                        old_val = st.session_state.bookings.get(key, "")
                        if new_val != old_val:
                            current_cloud_val = fresh_db.get(key, "")
                            if current_cloud_val != old_val:
                                display_name = current_cloud_val if current_cloud_val.strip() else "被清空"
                                conflicts.append(f"{shift} {z} (志工{k+1}) 已變成「{display_name}」")
                                st.session_state.bookings[key] = current_cloud_val
                                if widget_key in st.session_state:
                                    del st.session_state[widget_key]
                            else:
                                st.session_state.bookings[key] = new_val
                                save_data(key, new_val)
                                fresh_db[key] = new_val
                                changes_count += 1

            if conflicts:
                st.error("⚠️ **部分時段已被他人排走：**\n\n" + "\n".join([f"- {msg}" for msg in conflicts]))
                st.info("🔄 畫面已自動更新。如需蓋過，請重新輸入後再次儲存。")
                if changes_count > 0:
                    st.success(f"✅ 其餘 {changes_count} 筆未衝突，已成功儲存！")
            elif changes_count > 0:
                st.success(f"✅ 成功儲存 {changes_count} 筆排班！")
                st.rerun()
            else:
                st.info("ℹ️ 沒有偵測到任何修改。")

        st.write("")

        # ==========================================
        # 🃏 折疊式點位卡片（每個 ZONE × 上下午）
        # ==========================================
        for z in ZONES:
            # 計算各時段目前已排人數，用來顯示 badge
            filled_am = sum(
                1 for k in range(MAX_SLOTS)
                if st.session_state.bookings.get(f"{d_str}_上午_{z}_{k+1}", "").strip()
            )
            filled_pm = sum(
                1 for k in range(MAX_SLOTS)
                if st.session_state.bookings.get(f"{d_str}_下午_{z}_{k+1}", "").strip()
            )
            total_filled = filled_am + filled_pm
            total_slots = MAX_SLOTS * 2  # 上午+下午各MAX_SLOTS個

            # badge 文字
            if total_filled == 0:
                badge = "🔘 尚無排班"
            elif total_filled == total_slots:
                badge = "✅ 已額滿"
            else:
                badge = f"🟡 {total_filled}/{total_slots} 人"

            # expander 標題加上 badge
            expander_label = f"📍 {z}　　{badge}"

            with st.expander(expander_label, expanded=False):

                # --- 上午 ---
                st.markdown(f"**🌞 {TIME_MAPPING['上午']}**")
                am_cols = st.columns(MAX_SLOTS)
                for k in range(MAX_SLOTS):
                    key = f"{d_str}_上午_{z}_{k+1}"
                    val = st.session_state.bookings.get(key, "")
                    with am_cols[k]:
                        st.text_input(
                            f"志工 {k+1}",
                            value=val,
                            key=f"in_{key}",
                            placeholder=f"志工 {k+1} 姓名"
                        )

                st.write("")

                # --- 下午 ---
                st.markdown(f"**🌤️ {TIME_MAPPING['下午']}**")
                pm_cols = st.columns(MAX_SLOTS)
                for k in range(MAX_SLOTS):
                    key = f"{d_str}_下午_{z}_{k+1}"
                    val = st.session_state.bookings.get(key, "")
                    with pm_cols[k]:
                        st.text_input(
                            f"志工 {k+1}",
                            value=val,
                            key=f"in_{key}",
                            placeholder=f"志工 {k+1} 姓名"
                        )
