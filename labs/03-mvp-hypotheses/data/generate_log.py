"""Моделювання 14 днів Concierge MVP Classno з п'ятьма репетиторами -> concierge_log.csv."""

import csv
import random
from pathlib import Path

SEED = 15
DAYS = 14
OUT = Path(__file__).with_name("concierge_log.csv")

# Частка днів, коли репетитор надсилає команді звіт про оплати: тиждень 1, тиждень 2.
TUTORS = {
    "Аліна": {"students": 8, "price": 350, "viber": 0, "cash": 0.0, "report": (0.86, 0.5)},
    "Ірина": {"students": 22, "price": 350, "viber": 16, "cash": 0.5, "report": (0.86, 0.6)},
    "Олена": {"students": 14, "price": 400, "viber": 14, "cash": 0.4, "report": (0.71, 0.5)},
    "Софія": {"students": 7, "price": 400, "viber": 0, "cash": 0.0, "report": (1.0, 0.65)},
    "Андрій": {"students": 9, "price": 400, "viber": 2, "cash": 0.2, "report": (0.86, 0.55)},
}

FIELDS = ["day", "tutor", "student", "event", "channel", "amount", "detail"]


def make_students(rng):
    students = []
    for tutor, cfg in TUTORS.items():
        for i in range(1, cfg["students"] + 1):
            per_week = rng.choice([1, 2, 2]) if tutor in ("Ірина", "Олена") else rng.choice([1, 2, 2, 2, 3])
            weekdays = sorted(rng.sample(range(6 if tutor in ("Ірина", "Олена") else 5), per_week))
            students.append({
                "tutor": tutor,
                "name": f"{tutor[0]}{i:02d}",
                "price": cfg["price"] + rng.choice([-50, 0, 0, 50]),
                "weekdays": weekdays,
                "channel": "Viber" if i <= cfg["viber"] else "Telegram",
                "cash": rng.random() < cfg["cash"],
                "prompt": rng.uniform(0.3, 0.75),
                "responsive": rng.uniform(0.55, 0.95),
                "unpaid": [],
                "unreported": [],
                "pay_day": None,
                "last_reminder": None,
                "episode_open": False,
            })
    return students


def simulate(rng):
    students = make_students(rng)
    rows = []

    def log(day, s, event, channel="", amount="", detail=""):
        rows.append([day, s["tutor"], s["name"], event, channel, amount, detail])

    for day in range(1, DAYS + 1):
        week = 0 if day <= 7 else 1
        weekday = (day - 1) % 7

        for s in students:
            seen_unpaid = s["unpaid"] + s["unreported"]
            if not seen_unpaid or min(l for l, _ in seen_unpaid) > day - 2:
                continue
            if s["last_reminder"] is not None and day - s["last_reminder"] < 3:
                continue
            amount = sum(p for _, p in seen_unpaid)
            if not s["unpaid"]:
                log(day, s, "reminder_false", s["channel"], amount, "оплату не передано команді")
                reply = "reply_negative" if rng.random() < 0.2 else "reply_paid_already"
                log(day, s, reply, s["channel"])
                s["unreported"] = []
                continue
            log(day, s, "reminder_repeat" if s["episode_open"] else "reminder_first", s["channel"], amount)
            s["episode_open"] = True
            s["last_reminder"] = day
            if rng.random() < 0.02:
                log(day, s, "reply_negative", s["channel"])
            if s["pay_day"] is None:
                if rng.random() < s["responsive"]:
                    delay = rng.choices([0, 1, 2, 3], weights=[45, 30, 15, 10])[0]
                else:
                    delay = rng.randint(4, 9)
                s["pay_day"] = day + delay

        for s in students:
            if weekday in s["weekdays"]:
                log(day, s, "lesson", amount=s["price"])
                if s["cash"]:
                    s["unreported"].append((day, s["price"]))
                    log(day, s, "payment", amount=s["price"], detail="готівка")
                else:
                    s["unpaid"].append((day, s["price"]))
                    if s["pay_day"] is None and rng.random() < s["prompt"]:
                        s["pay_day"] = day + rng.choice([0, 0, 1])

            if s["pay_day"] is not None and s["pay_day"] <= day and s["unpaid"]:
                detail = "після нагадування" if s["episode_open"] else "без нагадування"
                log(day, s, "payment", amount=sum(p for _, p in s["unpaid"]), detail=detail)
                s["unreported"] += s["unpaid"]
                s["unpaid"] = []
                s["pay_day"] = None
                s["episode_open"] = False
                s["last_reminder"] = None

        for tutor, cfg in TUTORS.items():
            if rng.random() < cfg["report"][week]:
                rows.append([day, tutor, "", "tutor_report", "Telegram", "", ""])
                for s in students:
                    if s["tutor"] == tutor:
                        s["unreported"] = []

        if weekday == 6:
            for tutor in TUTORS:
                rows.append([day, tutor, "", "weekly_summary", "Telegram", "", ""])

    return rows


def main():
    rng = random.Random(SEED)
    rows = simulate(rng)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)
        writer.writerows(rows)
    print(f"{len(rows)} подій -> {OUT.name}")


if __name__ == "__main__":
    main()
