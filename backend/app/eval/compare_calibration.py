"""
拿人工打的分和裁判模型的分做对比，判断这个裁判能不能作为回归信号来用。

配套的人工打分 CSV 格式(表头必须是这几个字段):
    external_id,human_faithfulness,human_relevancy,human_notes
human_faithfulness: 1.0 表示"每条声明都有依据"，否则填你觉得支持的比例(比如 2/3 填 0.67)
human_relevancy: 1-5，和裁判用的是同一个量表

用法:
    uv run python -m app.eval.compare_calibration --run-id 4 --human-csv eval_calibration/human_scores.csv
"""
import argparse
import csv
from pathlib import Path

from app.core.database import SessionLocal
from app.models.eval_question import EvalQuestion
from app.models.eval_result import EvalResult

# 判定"完全忠实"的口径：faithfulness 是不是 >= 这个值，人工和裁判都用同一条线比
FULLY_FAITHFUL_THRESHOLD = 1.0


def compare_calibration(run_id: int, human_csv_path: str):
    human_scores = {}
    with open(human_csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            human_scores[row["external_id"]] = {
                "faithfulness": float(row["human_faithfulness"]),
                "relevancy": float(row["human_relevancy"]),
                "notes": row.get("human_notes", ""),
            }

    db = SessionLocal()
    try:
        results = db.query(EvalResult).filter(EvalResult.eval_run_id == run_id).all()

        faithfulness_agree, faithfulness_disagree = 0, []
        relevancy_agree, relevancy_disagree = 0, []
        dangerous_misses = []  # 裁判说 fully faithful，人工标了明显编造的地方
        n_compared = 0

        for r in results:
            q = db.query(EvalQuestion).filter(EvalQuestion.id == r.eval_question_id).first()
            key = q.external_id or str(q.id)
            if key not in human_scores or r.faithfulness_score is None:
                continue
            n_compared += 1
            human = human_scores[key]

            judge_fully_faithful = r.faithfulness_score >= FULLY_FAITHFUL_THRESHOLD
            human_fully_faithful = human["faithfulness"] >= FULLY_FAITHFUL_THRESHOLD
            if judge_fully_faithful == human_fully_faithful:
                faithfulness_agree += 1
            else:
                faithfulness_disagree.append(
                    f"[{key}] judge={r.faithfulness_score:.2f} human={human['faithfulness']:.2f} "
                    f"({human['notes']})"
                )
                if judge_fully_faithful and not human_fully_faithful:
                    dangerous_misses.append(
                        f"[{key}] judge said FULLY FAITHFUL, human disagreed: {human['notes']}"
                    )

            if r.answer_relevancy_score is not None:
                if abs(r.answer_relevancy_score - human["relevancy"]) <= 1.0:
                    relevancy_agree += 1
                else:
                    relevancy_disagree.append(
                        f"[{key}] judge={r.answer_relevancy_score:.0f} human={human['relevancy']:.0f}"
                    )

        if n_compared == 0:
            print("No overlapping questions between the CSV and this run's results — check external_ids match.")
            return

        faithfulness_pct = faithfulness_agree / n_compared * 100
        relevancy_pct = relevancy_agree / n_compared * 100

        print(f"=== Calibration comparison (run #{run_id}, n={n_compared}) ===")
        print(
            f"Faithfulness (binary 'fully faithful?' agreement): "
            f"{faithfulness_agree}/{n_compared} = {faithfulness_pct:.0f}%"
        )
        print(f"Relevancy (within +/-1 on 1-5 scale): {relevancy_agree}/{n_compared} = {relevancy_pct:.0f}%")

        print(f"\nPass bar: faithfulness>=80% AND relevancy>=80% AND zero dangerous misses.")
        passed = faithfulness_pct >= 80 and relevancy_pct >= 80 and not dangerous_misses
        print(f"Result: {'PASS — judge is calibrated enough to trust as a regression signal' if passed else 'FAIL — revise the judge prompt and recalibrate'}")

        if dangerous_misses:
            print(f"\n*** DANGEROUS: judge said 'fully faithful' but human disagreed ({len(dangerous_misses)}) ***")
            for m in dangerous_misses:
                print(f"  {m}")

        if faithfulness_disagree:
            print(f"\nAll faithfulness disagreements ({len(faithfulness_disagree)}):")
            for d in faithfulness_disagree:
                print(f"  {d}")

        if relevancy_disagree:
            print(f"\nAll relevancy disagreements ({len(relevancy_disagree)}):")
            for d in relevancy_disagree:
                print(f"  {d}")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--human-csv", type=str, required=True)
    args = parser.parse_args()
    compare_calibration(args.run_id, args.human_csv)
