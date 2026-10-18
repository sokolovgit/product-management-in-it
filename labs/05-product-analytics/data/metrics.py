"""Unit economics, CAC за каналами, прогноз MRR на 12 місяців, воронка AARRR і вибірка A/B-тесту; таблиці підставляються у звіт."""

import json
import math
import re
from pathlib import Path
from statistics import NormalDist

HERE = Path(__file__).parent
REPORT = HERE.parent / "docs/report/report.md"

UAH_PER_USD = 42
PRO_UAH, STUDIO_UAH = 149, 499
PRO = PRO_UAH / UAH_PER_USD
STUDIO = STUDIO_UAH / UAH_PER_USD

# COGS на одного платного клієнта на місяць, $.
COGS = {
    "Хостинг, база даних, Telegram-бот": 0.15,
    "Платіжний провайдер (2.75% від платежу)": round(PRO * 0.0275, 2),
    "Підтримка (частка ставки на одного клієнта)": 0.25,
}
CHURN = 0.06

# Канали на третій місяць після запуску: витрати за місяць ($) і нові платні клієнти.
CHANNELS = [
    (
        "Telegram-спільноти репетиторів",
        "Organic",
        300,
        18,
        "Комʼюніті-менеджер на пів ставки, пости й відповіді в чатах НМТ і репетиторів",
    ),
    (
        "Реферали й підпис у нагадуваннях",
        "Product-Led",
        None,
        14,
        "Місяць Pro безкоштовно і тому, хто запросив, і новому клієнту",
    ),
    (
        "Таргетована реклама Facebook / Instagram",
        "Paid",
        300,
        12,
        "Аудиторія вчителів і студентів-репетиторів, CPC ≈ $0.25",
    ),
    (
        "Facebook-групи вчителів",
        "Organic",
        100,
        6,
        "Частина часу того ж комʼюніті-менеджера",
    ),
    (
        "Контент і SEO",
        "Organic",
        150,
        3,
        "Статті «як вести облік учнів і оплат», окупаються через 4–6 місяців",
    ),
]

# План на шостий місяць: частка рефералів росте, реклама скорочується, контент окупається.
CHANNELS_M6 = {
    "Telegram-спільноти репетиторів": (300, 25),
    "Реферали й підпис у нагадуваннях": (None, 30),
    "Таргетована реклама Facebook / Instagram": (150, 6),
    "Facebook-групи вчителів": (100, 8),
    "Контент і SEO": (150, 12),
}

# Прогноз з першого місяця після публічного запуску (січень 2027).
MONTHS = [
    "Січ",
    "Лют",
    "Бер",
    "Кві",
    "Тра",
    "Чер",
    "Лип",
    "Сер",
    "Вер",
    "Жов",
    "Лис",
    "Гру",
]
NEW_PAYING = [20, 35, 53, 65, 75, 70, 40, 45, 120, 110, 95, 85]
MONTH_CHURN = [CHURN] * 6 + [0.12, 0.12] + [CHURN] * 4
UPGRADES = [0, 1, 1, 2, 2, 1, 0, 1, 3, 3, 2, 2]

FUNNEL = [
    ("Відвідувачі сайту й лендінгу", 6000),
    ("Реєстрації (Acquisition)", 840),
    ("Activation – Aha Moment за 7 днів", 252),
    ("D30 Retained", 151),
    ("Платять (Revenue)", 53),
]

AB = {
    "baseline": 0.40,
    "mde_rel": 0.20,
    "alpha": 0.05,
    "power": 0.80,
    "daily_new": 28,
    "eligible": 0.85,
    "window": 14,
    "n_calculator": 592,
}


def unit_economics():
    cogs = sum(COGS.values())
    gm = (PRO - cogs) / PRO
    ltv = PRO / CHURN * gm
    rows = []
    referral_cost = None
    for name, kind, spend, new, note in CHANNELS:
        if spend is None:
            spend = round(new * 2 * PRO)
            referral_cost = spend
        rows.append(
            {
                "name": name,
                "kind": kind,
                "spend": spend,
                "new": new,
                "cac": spend / new,
                "note": note,
            }
        )
    total_spend = sum(r["spend"] for r in rows)
    total_new = sum(r["new"] for r in rows)
    cac = total_spend / total_new
    m6 = {name: (spend if spend is not None else round(new * 2 * PRO), new) for name, (spend, new) in CHANNELS_M6.items()}
    cac_m6 = sum(v[0] for v in m6.values()) / sum(v[1] for v in m6.values())
    return {
        "cac_m6": cac_m6,
        "ltv_cac_m6": ltv / cac_m6,
        "m6": m6,
        "pro": PRO,
        "studio": STUDIO,
        "cogs": cogs,
        "gm": gm,
        "churn": CHURN,
        "ltv": ltv,
        "channels": rows,
        "referral_cost": referral_cost,
        "cac": cac,
        "ltv_cac": ltv / cac,
        "payback": cac / (PRO * gm),
        "churn_for_3x": PRO * gm / (3 * cac),
        "ltv_cac_paid": ltv / next(r["cac"] for r in rows if r["kind"] == "Paid"),
    }


def projection():
    pro, studio, cumulative = 0.0, 0, 0.0
    rows = []
    for i, month in enumerate(MONTHS):
        churned = round((pro + studio) * MONTH_CHURN[i])
        churned_studio = round(studio * MONTH_CHURN[i])
        pro = pro + NEW_PAYING[i] - (churned - churned_studio) - UPGRADES[i]
        studio = studio - churned_studio + UPGRADES[i]
        mrr = pro * PRO + studio * STUDIO
        cumulative += mrr
        rows.append(
            {
                "n": i + 1,
                "month": month,
                "new": NEW_PAYING[i],
                "churned": churned,
                "upgrades": UPGRADES[i],
                "clients": int(pro + studio),
                "studio": studio,
                "mrr": mrr,
                "cumulative": cumulative,
            }
        )
    return rows


def funnel():
    rows = []
    for (name, value), (_, prev) in zip(FUNNEL[1:], FUNNEL[:-1]):
        rows.append(
            {
                "step": name,
                "value": value,
                "share": value / prev,
                "drop": 1 - value / prev,
                "from": prev,
            }
        )
    return rows


def sample_size(p1, mde_rel, alpha, power):
    p2 = p1 * (1 + mde_rel)
    z_a = NormalDist().inv_cdf(1 - alpha / 2)
    z_b = NormalDist().inv_cdf(power)
    p_bar = (p1 + p2) / 2
    n = (
        z_a * math.sqrt(2 * p_bar * (1 - p_bar))
        + z_b * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    ) ** 2 / (p2 - p1) ** 2
    simple = 2 * (z_a + z_b) ** 2 * p1 * (1 - p1) / (mde_rel * p1) ** 2
    return {
        "p2": p2,
        "z_a": z_a,
        "z_b": z_b,
        "n": math.ceil(n),
        "n_simple": math.ceil(simple),
    }


def ab_test():
    s = sample_size(AB["baseline"], AB["mde_rel"], AB["alpha"], AB["power"])
    per_day = AB["daily_new"] * AB["eligible"]
    per_group = per_day / 2
    enroll_days = math.ceil(AB["n_calculator"] / per_group)
    enroll_weeks = math.ceil(enroll_days / 7)
    return {
        **AB,
        **s,
        "per_day": per_day,
        "per_group": per_group,
        "enroll_days": enroll_days,
        "enroll_weeks": enroll_weeks,
        "total_days": enroll_weeks * 7 + AB["window"],
    }


def money(x, digits=0):
    s = f"{x:,.{digits}f}".replace(",", " ")
    return f"\\${s}"


def pct(x, digits=1):
    s = f"{100 * x:.{digits}f}"
    return (s.rstrip("0").rstrip(".") if "." in s else s) + "%"


def table(header, rows, widths):
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("-" * w for w in widths) + " |",
    ]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def render(ue, proj, fun, ab):
    blocks = {}
    blocks["cac"] = table(
        [
            "Канал",
            "Тип",
            "Витрати",
            "Клієнтів",
            "CAC",
            "Що входить у витрати",
        ],
        [
            [
                c["name"],
                c["kind"],
                money(c["spend"]),
                c["new"],
                money(c["cac"], 2),
                c["note"],
            ]
            for c in ue["channels"]
        ]
        + [
            [
                "Разом / середній",
                "–",
                money(sum(c["spend"] for c in ue["channels"])),
                sum(c["new"] for c in ue["channels"]),
                money(ue["cac"], 2),
                "Зважений за кількістю клієнтів",
            ]
        ],
        [22, 13, 13, 12, 11, 29],
    )
    blocks["cogs"] = table(
        ["Стаття COGS", "На клієнта / міс"],
        [[k, money(v, 2)] for k, v in COGS.items()] + [["Разом", money(ue["cogs"], 2)]],
        [70, 30],
    )
    blocks["unit"] = table(
        ["Показник", "Формула", "Значення", "Джерело / обґрунтування"],
        [
            [
                "Модель монетизації",
                "–",
                "Freemium + підписка",
                "Безкоштовно до 5 учнів, Pro без обмежень, Studio для міні-шкіл (ПР01)",
            ],
            [
                "Ціна підписки (ARPPU Pro)",
                f"{PRO_UAH} грн / {UAH_PER_USD}",
                money(ue["pro"], 2),
                "У діапазоні WTP 100–200 грн, який назвали 25% респондентів ПР01; Studio – "
                + money(ue["studio"], 2),
            ],
            [
                "Gross Margin",
                "(ARPU − COGS) / ARPU",
                pct(ue["gm"], 0),
                f"COGS {money(ue['cogs'], 2)} на клієнта: таблиця нижче",
            ],
            [
                "Monthly Churn Rate",
                "–",
                pct(ue["churn"], 0),
                "Бенчмарк SaaS 2–5% на місяць [2]; для самозайнятих репетиторів закладено 6%, влітку 12%",
            ],
            [
                "LTV",
                "ARPU × (1 / Churn) × GM",
                money(ue["ltv"], 2),
                f"{money(ue['pro'], 2)} × {1 / ue['churn']:.1f} × {ue['gm']:.2f}",
            ],
            [
                "CAC (середній)",
                "Витрати / нових клієнтів",
                money(ue["cac"], 2),
                "Зважений по п'яти каналах, таблиця CAC",
            ],
            [
                "LTV / CAC",
                "LTV / CAC",
                f"{ue['ltv_cac']:.2f} : 1",
                "Нижче цілі 3 : 1 – план нижче",
            ],
            [
                "CAC Payback Period",
                "CAC / (ARPU × GM)",
                f"{ue['payback']:.1f} міс",
                "Ціль < 12 місяців виконана",
            ],
            [
                "MRR (ціль Q4)",
                "Σ клієнтів × ціна",
                money(proj[-1]["mrr"]),
                "Грудень у прогнозі нижче",
            ],
            [
                "ARR (ціль)",
                "MRR × 12",
                money(proj[-1]["mrr"] * 12),
                "Run-rate на кінець першого року",
            ],
        ],
        [18, 22, 15, 45],
    )
    blocks["projection"] = table(
        [
            "Місяць",
            "Нових клієнтів",
            "Churned",
            "Expansion (переходи на Studio)",
            "Всього клієнтів",
            "MRR",
            "Cumul. Revenue",
        ],
        [
            [
                f"{r['n']} ({r['month']})",
                r["new"],
                r["churned"],
                r["upgrades"],
                r["clients"],
                money(r["mrr"]),
                money(r["cumulative"]),
            ]
            for r in proj
        ],
        [13, 13, 12, 14, 14, 15, 19],
    )
    blocks["funnel"] = table(
        ["Етап воронки", "Числа (ціль, 3-й місяць)", "Конверсія", "Відтік"],
        [
            [
                f"{r['from']:,}".replace(",", " ") + " → " + r["step"],
                f"{r['value']:,}".replace(",", " "),
                pct(r["share"]),
                pct(r["drop"]),
            ]
            for r in fun
        ],
        [44, 20, 16, 20],
    )
    blocks["ab_calc"] = table(
        ["Параметр", "Значення"],
        [
            ["Baseline CR (p)", pct(ab["baseline"], 0)],
            ["MDE (відносний)", pct(ab["mde_rel"], 0)],
            [
                "Absolute MDE",
                f"{pct(ab['baseline'], 0)} × {pct(ab['mde_rel'], 0)} = {pct(ab['p2'] - ab['baseline'], 0)} (8 п.п.)",
            ],
            ["Очікуване значення B", pct(ab["p2"], 0)],
            ["α", ab["alpha"]],
            ["Power", pct(ab["power"], 0)],
            ["N у кожній групі (калькулятор)", ab["n_calculator"]],
            [
                "Нових репетиторів на день, з них з першим заняттям",
                f"{ab['daily_new']}, {ab['per_day']:.0f}",
            ],
            [
                "Трафік на групу (50/50)",
                f"{ab['per_day']:.0f} / 2 ≈ {ab['per_group']:.1f} на день",
            ],
            [
                "Набір вибірки",
                f"{ab['n_calculator']} / {ab['per_group']:.1f} ≈ {ab['enroll_days']} днів → {ab['enroll_weeks']} тижнів",
            ],
            ["Спостереження за останньою когортою", f"{ab['window']} днів"],
            [
                "Тривалість тесту",
                f"{ab['enroll_weeks']} × 7 + {ab['window']} = {ab['total_days']} днів",
            ],
        ],
        [55, 45],
    )
    return blocks


def inject(blocks):
    text = REPORT.read_text(encoding="utf-8")
    text = re.sub(
        r"<!-- gen:(\w+) -->.*?<!-- /gen:\1 -->",
        lambda m: (
            f"<!-- gen:{m.group(1)} -->\n{blocks[m.group(1)]}\n<!-- /gen:{m.group(1)} -->"
        ),
        text,
        flags=re.S,
    )
    counter = iter(range(1, 1000))
    text = re.sub(
        r"Таблиця (?:\{t\}|\d+) – ", lambda m: f"Таблиця {next(counter)} – ", text
    )
    REPORT.write_text(text, encoding="utf-8")


def main():
    ue = unit_economics()
    proj = projection()
    fun = funnel()
    ab = ab_test()
    (HERE / "results.json").write_text(
        json.dumps(
            {"unit": ue, "projection": proj, "funnel": fun, "ab": ab},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    if REPORT.exists():
        inject(render(ue, proj, fun, ab))
    print(
        json.dumps(
            {k: v for k, v in ue.items() if k != "channels"},
            ensure_ascii=False,
            indent=1,
        )
    )
    for c in ue["channels"]:
        print(c["name"], round(c["cac"], 2))
    for r in proj:
        print(r)
    for r in fun:
        print(r)
    print(ab)


if __name__ == "__main__":
    main()
