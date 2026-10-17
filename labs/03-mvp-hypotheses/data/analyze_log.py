"""Метрики Concierge MVP з журналу concierge_log.csv: щоденник тестування і результати гіпотез."""

import csv
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
LOG = HERE / "concierge_log.csv"
OUT = HERE / "metrics.json"

DAYS = 14
WINDOW = 3
CHECKPOINTS = [1, 3, 5, 7, 10, 12, 14]
TUTORS = ["Аліна", "Ірина", "Олена", "Софія", "Андрій"]


def load():
    with LOG.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["day"] = int(r["day"])
        r["amount"] = int(r["amount"]) if r["amount"] else 0
    return rows


def episodes(rows):
    by_student = defaultdict(list)
    for r in rows:
        if r["student"]:
            by_student[(r["tutor"], r["student"])].append(r)
    result = []
    for (tutor, student), events in by_student.items():
        start = None
        for r in events:
            if r["event"] == "reminder_first":
                start, channel, amount = r["day"], r["channel"], r["amount"]
            elif (
                r["event"] == "payment"
                and r["detail"] == "після нагадування"
                and start is not None
            ):
                result.append(
                    {
                        "tutor": tutor,
                        "start": start,
                        "paid": r["day"],
                        "channel": channel,
                        "amount": amount,
                    }
                )
                start = None
        if start is not None:
            result.append(
                {
                    "tutor": tutor,
                    "start": start,
                    "paid": None,
                    "channel": channel,
                    "amount": amount,
                }
            )
    return result


def within(e, day=DAYS):
    return (
        e["paid"] is not None and e["paid"] - e["start"] <= WINDOW and e["paid"] <= day
    )


def share(part, whole):
    return round(100 * part / whole, 1) if whole else None


def main():
    rows = load()
    eps = episodes(rows)
    eligible = [e for e in eps if e["start"] <= DAYS - WINDOW]
    delays = [e["paid"] - e["start"] for e in eps if e["paid"] is not None]

    reminders = [r for r in rows if r["event"].startswith("reminder")]
    recipients = {(r["tutor"], r["student"]) for r in reminders}
    negative = [r for r in rows if r["event"] == "reply_negative"]
    false_rem = [r for r in rows if r["event"] == "reminder_false"]
    false_keys = {(r["day"], r["tutor"], r["student"]) for r in false_rem}
    negative_after_false = sum((r["day"], r["tutor"], r["student"]) in false_keys for r in negative)

    reports = {t: [0, 0] for t in TUTORS}
    for r in rows:
        if r["event"] == "tutor_report":
            reports[r["tutor"]][0 if r["day"] <= 7 else 1] += 1

    diary = []
    for d in CHECKPOINTS:
        closed = [e for e in eps if e["start"] <= d - WINDOW]
        sent = [r for r in reminders if r["day"] <= d]
        diary.append(
            {
                "day": d,
                "reminders": len(sent),
                "episodes": len(closed),
                "paid3": sum(within(e, d) for e in closed),
                "share3": share(sum(within(e, d) for e in closed), len(closed)),
                "negative": sum(r["day"] <= d for r in negative),
                "false": sum(r["day"] <= d for r in false_rem),
                "report_days": sum(
                    1 for r in rows if r["event"] == "tutor_report" and r["day"] <= d
                ),
            }
        )

    by_channel = {}
    for ch in ("Telegram", "Viber"):
        sub = [e for e in eligible if e["channel"] == ch]
        by_channel[ch] = {
            "episodes": len(sub),
            "paid3": sum(map(within, sub)),
            "share3": share(sum(map(within, sub)), len(sub)),
        }

    by_tutor = {}
    for t in TUTORS:
        sub = [e for e in eligible if e["tutor"] == t]
        by_tutor[t] = {
            "lessons": sum(
                1 for r in rows if r["tutor"] == t and r["event"] == "lesson"
            ),
            "students": len(
                {r["student"] for r in rows if r["tutor"] == t and r["student"]}
            ),
            "reminders": sum(1 for r in reminders if r["tutor"] == t),
            "episodes": len(sub),
            "paid3": sum(map(within, sub)),
            "report_w1": reports[t][0],
            "report_w2": reports[t][1],
            "negative": sum(1 for r in negative if r["tutor"] == t),
            "false": sum(1 for r in false_rem if r["tutor"] == t),
        }

    metrics = {
        "lessons": sum(1 for r in rows if r["event"] == "lesson"),
        "revenue": sum(r["amount"] for r in rows if r["event"] == "lesson"),
        "reminders_total": len(reminders),
        "reminders_first": sum(1 for r in reminders if r["event"] == "reminder_first"),
        "reminders_repeat": sum(
            1 for r in reminders if r["event"] == "reminder_repeat"
        ),
        "reminders_false": len(false_rem),
        "recipients": len(recipients),
        "negative": len(negative),
        "negative_share": share(len(negative), len(reminders)),
        "negative_after_false": negative_after_false,
        "negative_share_true": share(len(negative) - negative_after_false, len(reminders) - len(false_rem)),
        "false_share": share(len(false_rem), len(reminders)),
        "false_w1": sum(r["day"] <= 7 for r in false_rem),
        "false_w2": sum(r["day"] > 7 for r in false_rem),
        "episodes_all": len(eps),
        "episodes_eligible": len(eligible),
        "paid3": sum(map(within, eligible)),
        "share3": share(sum(map(within, eligible)), len(eligible)),
        "unpaid_at_end": sum(1 for e in eps if e["paid"] is None),
        "avg_delay": round(sum(delays) / len(delays), 1),
        "collected_after_reminder": sum(
            e["amount"] for e in eps if e["paid"] is not None
        ),
        "report_avg_w1": round(sum(v[0] for v in reports.values()) / len(TUTORS), 1),
        "report_avg_w2": round(sum(v[1] for v in reports.values()) / len(TUTORS), 1),
        "tutors_5of7_w2": sum(1 for v in reports.values() if v[1] >= 5),
        "diary": diary,
        "by_channel": by_channel,
        "by_tutor": by_tutor,
    }
    OUT.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {k: v for k, v in metrics.items() if k not in ("diary", "by_tutor")},
            ensure_ascii=False,
            indent=1,
        )
    )
    for row in diary:
        print(row)
    for t, v in by_tutor.items():
        print(t, v)


if __name__ == "__main__":
    main()
