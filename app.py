import streamlit as st
from datetime import datetime
from db import get_all_reservations, reserve_seat, cancel_seat, init_db, LIMIT_MINUTES
import uuid

# ── 페이지 설정 ────────────────────────────────────────────────
st.set_page_config(
    page_title="학생 식당 자리 예약",
    page_icon="🍽",
    layout="wide",
)

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
  .stApp { background: #F7F7F5; }
  .block-container { padding-top: 1.5rem !important; }

  div[data-testid="column"] .stButton > button {
    width: 100%; height: 80px;
    border-radius: 10px; font-size: 13px; font-weight: 600;
    border: 2px solid; transition: opacity .15s;
    white-space: pre-line;
  }
  div[data-testid="column"] .stButton > button:hover { opacity: .85; }

  div[data-testid="metric-container"] {
    background: #fff; border: 1px solid #E0DED8;
    border-radius: 10px; padding: 14px 20px;
  }

  hr { border-color: #E0DED8; }

  /* 타이머 바 */
  .timer-wrap {
    background: #fff; border: 1px solid #E0DED8;
    border-radius: 12px; padding: 16px 20px; margin-bottom: 8px;
  }
  .timer-bar-bg {
    background: #E0DED8; border-radius: 99px;
    height: 10px; width: 100%; margin-top: 8px;
  }
  .timer-bar-fill {
    height: 10px; border-radius: 99px;
    transition: width .5s;
  }
</style>
""", unsafe_allow_html=True)

# ── 구역 정의 ─────────────────────────────────────────────────
ZONES = {
    "A": {
        "label": "🪟 A구역 (창가)",
        "tables": [
            {"id": "A1", "seats": 2}, {"id": "A2", "seats": 2},
            {"id": "A3", "seats": 4}, {"id": "A4", "seats": 4},
            {"id": "A5", "seats": 2}, {"id": "A6", "seats": 4},
        ],
        "cols": 3,
    },
    "B": {
        "label": "👥 B구역 (중앙)",
        "tables": [
            {"id": "B1", "seats": 4}, {"id": "B2", "seats": 6},
            {"id": "B3", "seats": 4}, {"id": "B4", "seats": 6},
            {"id": "B5", "seats": 4}, {"id": "B6", "seats": 6},
            {"id": "B7", "seats": 4}, {"id": "B8", "seats": 4},
        ],
        "cols": 4,
    },
    "C": {
        "label": "🚪 C구역 (입구)",
        "tables": [
            {"id": "C1", "seats": 2}, {"id": "C2", "seats": 4},
            {"id": "C3", "seats": 4}, {"id": "C4", "seats": 2},
            {"id": "C5", "seats": 4}, {"id": "C6", "seats": 4},
            {"id": "C7", "seats": 2}, {"id": "C8", "seats": 4},
        ],
        "cols": 4,
    },
}

TOTAL_SEC = LIMIT_MINUTES * 60  # 600초

# ── 세션 초기화 ────────────────────────────────────────────────
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())[:8]
if "my_table" not in st.session_state:
    st.session_state.my_table = None

# ── DB 초기화 / 예약 로드 ──────────────────────────────────────
init_db()
reservations = get_all_reservations()   # {tid: uid, tid__time: ..., tid__remaining: ...}

# 내 예약 DB 동기화
if st.session_state.my_table and st.session_state.my_table not in reservations:
    st.session_state.my_table = None
if st.session_state.my_table is None:
    for tid, val in reservations.items():
        if "__" not in tid and val == st.session_state.user_id:
            st.session_state.my_table = tid
            break

now = datetime.now()

# ── 헤더 ──────────────────────────────────────────────────────
col_title, col_clock = st.columns([3, 1])
with col_title:
    st.markdown("## 🍽 학생 식당 자리 예약")
    st.caption(f"{now.year}년 {now.month}월 {now.day}일  ·  예약 후 {LIMIT_MINUTES}분 초과 시 자동 해제")
with col_clock:
    st.markdown(
        f"<div style='text-align:right;padding-top:8px;'>"
        f"<span style='font-size:22px;font-weight:700;color:#1D9E75;'>🕐 {now.strftime('%H:%M:%S')}</span><br>"
        f"<span style='font-size:12px;color:#888;'>자동 갱신: 3초마다</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

st.divider()

# ── 통계 ──────────────────────────────────────────────────────
all_tables = [t for z in ZONES.values() for t in z["tables"]]
total  = len(all_tables)
taken  = sum(1 for k, v in reservations.items() if "__" not in k)
avail  = total - taken
mine_c = 1 if st.session_state.my_table else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("🟢 예약 가능",    avail)
m2.metric("🔴 사용 중",      taken)
m3.metric("📋 전체 테이블",  total)
m4.metric("✅ 내 자리",      mine_c)

st.divider()

# ── 내 예약 현황 + 타이머 바 ──────────────────────────────────
if st.session_state.my_table:
    tid      = st.session_state.my_table
    zone_key = tid[0]
    tbl      = next(t for t in ZONES[zone_key]["tables"] if t["id"] == tid)
    t_time   = reservations.get(f"{tid}__time", "—")
    remaining = reservations.get(f"{tid}__remaining", TOTAL_SEC)

    # 남은 시간 계산
    mins, secs = divmod(remaining, 60)
    pct        = remaining / TOTAL_SEC * 100

    # 색상: 3분 미만이면 빨간색, 5분 미만이면 주황
    if remaining < 180:
        bar_color = "#E24B4A"
        urgency   = "⚠️ 곧 자동 해제됩니다!"
    elif remaining < 300:
        bar_color = "#E8952A"
        urgency   = "⏳ 시간이 얼마 남지 않았습니다"
    else:
        bar_color = "#1D9E75"
        urgency   = ""

    st.markdown(
        f"""
        <div class="timer-wrap">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <span style="font-size:15px;font-weight:700;color:#2C2C2A;">
                ✅ {tid}번 테이블 · {ZONES[zone_key]['label'].split()[1]} · {tbl['seats']}인석
              </span><br>
              <span style="font-size:12px;color:#888;">예약 시각: {t_time}</span>
              {"&nbsp;&nbsp;<span style='font-size:12px;color:" + bar_color + ";font-weight:600;'>" + urgency + "</span>" if urgency else ""}
            </div>
            <div style="text-align:right;">
              <span style="font-size:28px;font-weight:800;color:{bar_color};">
                {mins:02d}:{secs:02d}
              </span><br>
              <span style="font-size:11px;color:#888;">남은 시간</span>
            </div>
          </div>
          <div class="timer-bar-bg">
            <div class="timer-bar-fill" style="width:{pct:.1f}%;background:{bar_color};"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🗑 예약 취소", type="secondary", key="cancel_top"):
        cancel_seat(tid, st.session_state.user_id)
        st.session_state.my_table = None
        st.rerun()

    st.divider()

# ── 좌석 배치도 ───────────────────────────────────────────────
st.markdown("### 좌석 배치도")
st.caption("🟢 초록 = 예약 가능  |  🔴 회색 = 사용 중  |  ✅ 진한 초록 = 내 자리")

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

            tid    = tbl["id"]
            status = (
                "mine"  if tid == st.session_state.my_table else
                "taken" if tid in reservations and "__" not in tid and reservations[tid] != "" else
                "avail"
            )
            # 정확한 상태 재계산
            if tid in [k for k in reservations if "__" not in k]:
                status = "mine" if reservations[tid] == st.session_state.user_id else "taken"
            else:
                status = "avail"

            rem = reservations.get(f"{tid}__remaining", None)

            if status == "mine":
                mins_r, secs_r = divmod(rem or 0, 60)
                btn_label = f"✅ {tid}\n{tbl['seats']}인석\n⏱ {mins_r:02d}:{secs_r:02d}"
                style     = "background:#1D9E75;color:#fff;border-color:#0F6E56;"
            elif status == "taken":
                mins_r, secs_r = divmod(rem or 0, 60)
                btn_label = f"🔴 {tid}\n{tbl['seats']}인석\n⏱ {mins_r:02d}:{secs_r:02d}"
                style     = "background:#F1EFE8;color:#B4B2A9;border-color:#D3D1C7;"
            else:
                btn_label = f"🟢 {tid}\n{tbl['seats']}인석"
                style     = "background:#E1F5EE;color:#0F6E56;border-color:#1D9E75;"

            with col:
                st.markdown(f"<style>#btn_{tid} button{{{style}}}</style>", unsafe_allow_html=True)
                st.markdown(f"<span id='btn_{tid}'></span>", unsafe_allow_html=True)
                clicked = st.button(btn_label, key=f"tbl_{tid}", disabled=(status == "taken"))

            if clicked:
                if status == "mine":
                    cancel_seat(tid, st.session_state.user_id)
                    st.session_state.my_table = None
                    st.rerun()
                elif status == "avail":
                    if st.session_state.my_table:
                        cancel_seat(st.session_state.my_table, st.session_state.user_id)
                    ok = reserve_seat(tid, st.session_state.user_id)
                    if ok:
                        st.session_state.my_table = tid
                        st.rerun()
                    else:
                        st.warning("방금 다른 사람이 예약했습니다. 다른 자리를 선택해주세요.")
                        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

# ── 자동 새로고침 (3초) ────────────────────────────────────────
st.markdown("<script>setTimeout(()=>window.location.reload(),3000);</script>",
            unsafe_allow_html=True)

st.caption(f"🆔 세션: `{st.session_state.user_id}`  |  갱신: {now.strftime('%H:%M:%S')}")
