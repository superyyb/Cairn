"""
线上用户反馈(👍/👎)聚合报表 —— 让 Phase 1 攒的 chat_feedback 数据变成能讲的数字。

reason 按类别分桶统计时故意把 reason IS NULL 单独列一桶：Phase 1 的 UX 是点 👎 立刻提交，
reason 是事后可选补充的，NULL 占比高说明用户懒得选 chip，是 UX 健康信号，不是噪声。

样本量小的时候不装：低于 MIN_SAMPLE_SIZE 只报原始计数，不报百分比，跟 eval 那边
"true_negative n=8 的 100% 是精心挑出来的 100%，不是统计学意义的 100%" 是同一条纪律。

用法:
    uv run python -m app.eval.feedback_report
    uv run python -m app.eval.feedback_report --days 7 --recent 20
"""
import argparse
from datetime import timedelta

from app.core.database import SessionLocal
from app.core.utils import utc_now
from app.models.chat_feedback import ChatFeedback
from app.models.chat_session import ChatSession

MIN_SAMPLE_SIZE = 30


def feedback_report(days: int, recent: int):
    db = SessionLocal()
    try:
        since = utc_now() - timedelta(days=days)
        rows = db.query(ChatFeedback).filter(ChatFeedback.created_at >= since).all()

        total = len(rows)
        print(f"=== Feedback report (last {days}d, n={total}) ===")
        if total == 0:
            print("No feedback in this window.")
            return

        up = sum(1 for r in rows if r.rating)
        down = [r for r in rows if not r.rating]
        print(f"\U0001f44d {up}/{total} ({up / total * 100:.0f}%)   \U0001f44e {len(down)}/{total} ({len(down) / total * 100:.0f}%)")

        if not down:
            print("\nNo negative feedback in this window.")
            return

        print(f"\n--- \U0001f44e breakdown by reason (n={len(down)}) ---")
        small_sample = len(down) < MIN_SAMPLE_SIZE
        if small_sample:
            print(f"sample size too small for reliable distribution (n={len(down)} < {MIN_SAMPLE_SIZE}) "
                  f"— showing raw counts only, not percentages")

        reason_counts: dict[str | None, int] = {}
        for r in down:
            reason_counts[r.reason] = reason_counts.get(r.reason, 0) + 1
        for reason, count in sorted(reason_counts.items(), key=lambda kv: -kv[1]):
            label = reason if reason else "(no reason given)"
            if small_sample:
                print(f"  {label:<18}{count}")
            else:
                print(f"  {label:<18}{count:<6}{count / len(down) * 100:.0f}%")

        no_reason_pct = reason_counts.get(None, 0) / len(down) * 100
        print(f"\n  ({no_reason_pct:.0f}% of \U0001f44e have no reason attached — if this climbs over time, "
              f"users are clicking \U0001f44e and skipping the reason chips, worth simplifying the UX)")

        n_recent = min(recent, len(down))
        print(f"\n--- Most recent {n_recent} \U0001f44e (for triage / Phase 3 replay input) ---")
        recent_down = sorted(down, key=lambda r: r.created_at, reverse=True)[:recent]
        session_by_id = {
            s.id: s for s in db.query(ChatSession).filter(
                ChatSession.id.in_([r.chat_session_id for r in recent_down])
            )
        }
        for r in recent_down:
            session = session_by_id.get(r.chat_session_id)
            question = session.question if session else "(session not found)"
            reason = r.reason or "(no reason)"
            comment = f" — {r.comment}" if r.comment else ""
            print(f"  [{r.created_at:%Y-%m-%d %H:%M}] ({reason}) {question}{comment}")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--recent", type=int, default=10, help="How many most-recent \U0001f44e to list for triage")
    args = parser.parse_args()
    feedback_report(days=args.days, recent=args.recent)
