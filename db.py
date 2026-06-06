"""
db.py  ―  Supabase(PostgreSQL) 연동 레이어
10분 초과 예약은 자동 만료 처리 포함
"""

import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
LIMIT_MINUTES = 10   # 예약 유지 제한 시간

# ── Supabase 클라이언트 (연결 1회만) ──────────────────────────
@st.cache_resource
def _get_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def init_db():
    """
    Supabase 대시보드 SQL Editor에서 아래 SQL을 한 번만 실행하세요.

    CREATE TABLE IF NOT EXISTS reservations (
        table_id    TEXT PRIMARY KEY,
        user_id     TEXT NOT NULL,
        reserved_at TIMESTAMPTZ DEFAULT now()
    );
    """
    pass


def _expire_old_reservations(client):
    """
    reserved_at 이 LIMIT_MINUTES 분을 초과한 예약을 자동 삭제.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=LIMIT_MINUTES)).isoformat()
    try:
        client.table("reservations").delete().lt("reserved_at", cutoff).execute()
    except Exception:
        pass


def get_all_reservations() -> dict:
    """
    만료 예약 정리 후 현재 예약 현황 반환.
    반환: {
      "A1": "user_abc",
      "A1__time": "12:34:56",
      "A1__remaining": 427,   # 남은 초
    }
    """
    client = _get_client()
    _expire_old_reservations(client)

    resp = client.table("reservations").select("table_id, user_id, reserved_at").execute()
    now_utc = datetime.now(timezone.utc)
    result  = {}

    for row in resp.data:
        tid = row["table_id"]
        result[tid] = row["user_id"]

        ts = row.get("reserved_at", "")
        if ts:
            try:
                dt_utc = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                dt_kst = dt_utc.astimezone(KST)
                result[f"{tid}__time"] = dt_kst.strftime("%H:%M:%S")

                # 남은 시간 (초)
                elapsed = (now_utc - dt_utc).total_seconds()
                remaining = max(0, LIMIT_MINUTES * 60 - elapsed)
                result[f"{tid}__remaining"] = int(remaining)
            except Exception:
                result[f"{tid}__time"] = ts[:19]
                result[f"{tid}__remaining"] = 0

    return result


def reserve_seat(table_id: str, user_id: str) -> bool:
    client = _get_client()
    try:
        client.table("reservations").insert({
            "table_id":    table_id,
            "user_id":     user_id,
            "reserved_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        return True
    except Exception as e:
        return False


def cancel_seat(table_id: str, user_id: str) -> bool:
    """본인 예약만 취소."""
    client = _get_client()
    try:
        client.table("reservations") \
            .delete() \
            .eq("table_id", table_id) \
            .eq("user_id",  user_id) \
            .execute()
        return True
    except Exception:
        return False
