import streamlit as st
from datetime import datetime
from db import get_all_reservations, reserve_seat, cancel_seat, init_db, LIMIT_MINUTES

st.set_page_config(page_title="학생 식당 자리 예약", page_icon="🍽", layout="wide")

st.markdown("""
<style>
  .stApp { background: #F7F7F5; }
  .block-container { padding-top: 1.5rem !important; }
  hr { border-color: #E0DED8; }
  div[data-testid="metric-container"] {
    background:#fff; border:1px solid #E0DED8;
    border-radius:10px; padding:14px 20px;
  }
  .timer-wrap {
    background:#fff; border:1px solid #E0DED8;
    border-radius:12px; padding:16px 20px; margin-bottom:8px;
  }
  .timer-bar-bg {
    background:#E0DED8; border-radius:99px; height:10px; width:100%; margin-top:8px;
  }
  .timer-bar-fill { height:10px; border-radius:99px; }
  .detail-box {
    background:#fff; border:1.5px solid #1D9E75;
    border-radius:12px; padding:20px 24px; margin-bottom:16px;
  }
  .login-box {
    background:#fff; border:1px solid #E0DED8;
    border-radius:16px; padding:40px;
    max-width:400px; margin:80px auto;
    text-align:center;
  }
</style>
""", unsafe_allow_html=True)

ZONES = {
    "A": {"label":"🪟 A구역 (창가)","cols":3,"tables":[
        {"id":"A1","seats":2},{"id":"A2","seats":2},{"id":"A3","seats":4},
        {"id":"A4","seats":4},{"id":"A5","seats":2},{"id":"A6","seats":4}]},
    "B": {"label":"👥 B구역 (중앙)","cols":4,"tables":[
        {"id":"B1","seats":4},{"id":"B2","seats":6},{"id":"B3","seats":4},{"id":"B4","seats":6},
        {"id":"B5","seats":4},{"id":"B6","seats":6},{"id":"B7","seats":4},{"id":"B8","seats":4}]},
    "C": {"label":"🚪 C구역 (입구)","cols":4,"tables":[
        {"id":"C1","seats":2},{"id":"C2","seats":4},{"id":"C3","seats":4},{"id":"C4","seats":2},
        {"id":"C5","seats":4},{"id":"C6","seats":4},{"id":"C7","seats":2},{"id":"C8","seats":4}]},
}
TOTAL_SEC = LIMIT_MINUTES * 60

# ── 세션 초기화 ────────────────────────────────────────────────
if "student_id"   not in st.session_state: st.session_state.student_id   = None
if "my_table"     not in st.session_state: st.session_state.my_table     = None
if "selected_tbl" not in st.session_state: st.session_state.selected_tbl = None

# ── 로그인 화면 ───────────────────────────────────────────────
if not st.session_state.student_id:
    st.markdown("""
    <div class="login-box">
      <div style="font-size:48px;margin-bottom:8px;">🍽</div>
      <div style="font-size:22px;font-weight:700;color:#2C2C2A;margin-bottom:6px;">학생 식당 자리 예약</div>
      <div style="font-size:14px;color:#888;margin-bottom:28px;">학번을 입력하면 새로고침해도<br>내 자리가 유지됩니다</div>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        student_input = st.text_input(
            "학번 입력",
            placeholder="예: 20241234",
            max_chars=20,
            label_visibility="collapsed"
        )
        if st.button("입장하기 →", type="primary", use_container_width=True):
            if student_input.strip():
                st.session_state.student_id = student_input.strip()
                st.rerun()
            else:
                st.warning("학번을 입력해주세요!")
    st.stop()

# ── 여기서부터 로그인된 사용자만 ──────────────────────────────
user_id = st.session_state.student_id

init_db()
reservations = get_all_reservations()

# 내 예약 DB 동기화
if st.session_state.my_table and st.session_state.my_table not in reservations:
    st.session_state.my_table = None
if st.session_state.my_table is None:
    for tid, val in reservations.items():
        if "__" not in tid and val == user_id:
            st.session_state.my_table = tid
            break

now = datetime.now()

# ── 헤더 ──────────────────────────────────────────────────────
c1, c2 = st.columns([3, 1])
with c1:
    st.markdown("## 🍽 학생 식당 자리 예약")
    st.caption(f"{now.year}년 {now.month}월 {now.day}일  ·  예약 후 {LIMIT_MINUTES}분 초과 시 자동 해제  ·  학번: {user_id}")
with c2:
    st.markdown(
        f"<div style='text-align:right;padding-top:8px;'>"
        f"<span style='font-size:22px;font-weight:700;color:#1D9E75;'>🕐 {now.strftime('%H:%M:%S')}</span><br>"
        f"<span style='font-size:12px;color:#888;'>자동 갱신: 3초마다</span></div>",
        unsafe_allow_html=True)

# 로그아웃 버튼
with st.sidebar:
    st.markdown(f"**👤 학번:** {user_id}")
    if st.button("🚪 로그아웃", use_container_width=True):
        st.session_state.student_id   = None
        st.session_state.my_table     = None
        st.session_state.selected_tbl = None
        st.rerun()

st.divider()

# ── 통계 ──────────────────────────────────────────────────────
total = sum(len(z["tables"]) for z in ZONES.values())
taken = sum(1 for k in reservations if "__" not in k)
avail = total - taken
m1, m2, m3, m4 = st.columns(4)
m1.metric("🟢 예약 가능",   avail)
m2.metric("🔴 사용 중",     taken)
m3.metric("📋 전체 테이블", total)
m4.metric("✅ 내 자리",     1 if st.session_state.my_table else 0)

st.divider()

# ── 내 예약 타이머 배너 ───────────────────────────────────────
if st.session_state.my_table:
    tid       = st.session_state.my_table
    zk        = tid[0]
    tbl_info  = next(t for t in ZONES[zk]["tables"] if t["id"] == tid)
    t_time    = reservations.get(f"{tid}__time", "—")
    remaining = reservations.get(f"{tid}__remaining", TOTAL_SEC)
    mins, secs = divmod(remaining, 60)
    pct        = remaining / TOTAL_SEC * 100
    bar_color  = "#E24B4A" if remaining < 180 else "#E8952A" if remaining < 300 else "#1D9E75"
    urgency    = ("⚠️ 곧 자동 해제됩니다!" if remaining < 180
                  else "⏳ 시간이 얼마 남지 않았습니다" if remaining < 300 else "")

    zone_label = ZONES[zk]['label'].split()[1]
    zone_label = ZONES[zk]['label'].split()[1]
    with st.container(border=True):
        col_l, col_r = st.columns([3, 1])
        with col_l:
            st.markdown(f"**✅ {tid}번 테이블 · {zone_label} · {tbl_info['seats']}인석**")
            st.caption(f"예약 시각: {t_time}")
            if remaining < 180:
                st.error("⚠️ 곧 자동 해제됩니다!")
            elif remaining < 300:
                st.warning("⏳ 시간이 얼마 남지 않았습니다")
        with col_r:
            timer_color = "red" if remaining < 180 else "orange" if remaining < 300 else "green"
            st.markdown(f"### :{timer_color}[{mins:02d}:{secs:02d}]")
            st.caption("남은 시간")
        st.progress(int(pct))

    if st.button("🗑 예약 취소", key="cancel_top"):
        cancel_seat(tid, user_id)
        st.session_state.my_table     = None
        st.session_state.selected_tbl = None
        st.rerun()
    st.divider()

# ── 선택한 자리 상세 패널 ─────────────────────────────────────
sel = st.session_state.selected_tbl
if sel and sel != st.session_state.my_table:
    zk       = sel[0]
    tbl_info = next(t for t in ZONES[zk]["tables"] if t["id"] == sel)
    st.markdown(f"""
    <div class="detail-box">
      <div style="font-size:16px;font-weight:700;color:#0F6E56;margin-bottom:12px;">🪑 선택한 자리 정보</div>
      <table style="width:100%;font-size:14px;border-collapse:collapse;">
        <tr><td style="color:#888;padding:4px 0;width:90px;">테이블</td>
            <td style="font-weight:600;color:#2C2C2A;">{sel}번 테이블</td></tr>
        <tr><td style="color:#888;padding:4px 0;">구역</td>
            <td style="font-weight:600;color:#2C2C2A;">{ZONES[zk]['label']}</td></tr>
        <tr><td style="color:#888;padding:4px 0;">좌석 수</td>
            <td style="font-weight:600;color:#2C2C2A;">{tbl_info['seats']}인석</td></tr>
        <tr><td style="color:#888;padding:4px 0;">예약 학번</td>
            <td style="font-weight:600;color:#2C2C2A;">{user_id}</td></tr>
        <tr><td style="color:#888;padding:4px 0;">예약 시각</td>
            <td style="font-weight:600;color:#2C2C2A;">{now.strftime('%H:%M:%S')}</td></tr>
      </table>
    </div>""", unsafe_allow_html=True)

    bc1, bc2 = st.columns([1, 3])
    with bc1:
        if st.button("✅ 예약 확정", key="confirm_btn", type="primary"):
            if st.session_state.my_table:
                cancel_seat(st.session_state.my_table, user_id)
            ok = reserve_seat(sel, user_id)
            if ok:
                st.session_state.my_table     = sel
                st.session_state.selected_tbl = None
            else:
                st.warning("방금 다른 사람이 예약했습니다.")
                st.session_state.selected_tbl = None
            st.rerun()
    with bc2:
        if st.button("✖ 취소", key="cancel_sel"):
            st.session_state.selected_tbl = None
            st.rerun()
    st.divider()

# ── 좌석 배치도 ───────────────────────────────────────────────
st.markdown("### 좌석 배치도")
st.caption("자리를 클릭하면 상세 정보가 표시됩니다")

for zone_key, zone_info in ZONES.items():
    st.markdown(f"**{zone_info['label']}**")
    tables = zone_info["tables"]
    cols_n = zone_info["cols"]

    for row_start in range(0, len(tables), cols_n):
        row_tbls = tables[row_start: row_start + cols_n]
        while len(row_tbls) < cols_n:
            row_tbls.append(None)

        cols = st.columns(cols_n)
        for col, tbl in zip(cols, row_tbls):
            if tbl is None:
                col.empty()
                continue

            tid = tbl["id"]

            if reservations.get(tid) == user_id:
                status = "mine"
            elif tid in [k for k in reservations if "__" not in k]:
                status = "taken"
            else:
                status = "avail"

            rem = reservations.get(f"{tid}__remaining", 0)
            m, s = divmod(rem, 60)

            if status == "mine":
                bg, fg, bc = "#1D9E75", "#ffffff", "#0F6E56"
                icon  = "✅"
                timer = f"⏱ {m:02d}:{s:02d}"
            elif status == "taken":
                bg, fg, bc = "#EBEBEB", "#AAAAAA", "#CCCCCC"
                icon  = "⬛"
                timer = f"⏱ {m:02d}:{s:02d}"
            else:
                bg, fg, bc = "#E1F5EE", "#0F6E56", "#1D9E75"
                icon  = "🟢"
                timer = "예약하기"

            with col:
                st.markdown(f"""
                <div style="
                  background:{bg}; color:{fg}; border:2px solid {bc};
                  border-radius:10px; padding:10px 6px; text-align:center;
                  font-size:13px; font-weight:600; line-height:1.7;
                  margin-bottom:2px;
                ">
                  {icon} {tid}<br>
                  {tbl['seats']}인석<br>
                  <span style="font-size:11px;opacity:0.85;">{timer}</span>
                </div>
                """, unsafe_allow_html=True)

                if status != "taken":
                    clicked = st.button(
                        "선택" if status == "avail" else "내 자리 ✅",
                        key=f"tbl_{tid}",
                        use_container_width=True
                    )
                    if clicked:
                        st.session_state.selected_tbl = None if status == "mine" else tid
                        st.rerun()
                else:
                    st.markdown("<div style='height:36px;'></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

# ── 범례 ──────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;gap:20px;font-size:13px;color:#888;margin-top:8px;">
  <span><span style="display:inline-block;width:14px;height:14px;background:#E1F5EE;border:2px solid #1D9E75;border-radius:3px;vertical-align:middle;"></span> 예약 가능</span>
  <span><span style="display:inline-block;width:14px;height:14px;background:#1D9E75;border:2px solid #0F6E56;border-radius:3px;vertical-align:middle;"></span> 내 자리</span>
  <span><span style="display:inline-block;width:14px;height:14px;background:#EBEBEB;border:2px solid #CCC;border-radius:3px;vertical-align:middle;"></span> 사용 중</span>
</div>
""", unsafe_allow_html=True)

# ── 자동 새로고침 (3초, 타이머는 JS가 독립적으로 카운트다운) ──
st.markdown("<script>setTimeout(()=>window.location.reload(),3000);</script>",
            unsafe_allow_html=True)
st.caption(f"👤 {user_id}  |  갱신: {now.strftime('%H:%M:%S')}")
