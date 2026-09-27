"""Аналіз responses.csv: зведені показники для звіту і графіки в docs/report/assets."""

import csv
import statistics
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt

DATA = Path(__file__).with_name("responses.csv")
ASSETS = Path(__file__).parents[1] / "docs/report/assets"

WTP_ORDER = [
    "Лише безкоштовно",
    "До 100 грн",
    "100–200 грн",
    "200–500 грн",
    "Понад 500 грн",
]
FREQ_ORDER = ["Щодня", "Кілька разів на тиждень", "Рідко"]
ADMIN_ORDER = ["Менше 1 год", "1–2 год", "3–5 год", "Понад 5 год"]
LIKERT = {
    "Q12": "Задоволеність поточним способом",
    "Q13": "Важливість вирішення проблеми",
    "Q14": "Важко відстежувати оплати",
    "Q15": "Перенесення забирають час",
    "Q16": "Хочу звіти, але немає часу",
}

plt.rcParams.update(
    {
        "font.family": "Arial",
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)
BLUE = "#4472C4"


def pct(n: int, total: int) -> str:
    return f"{n / total * 100:.0f}%"


def counts(rows: list[dict], q: str, multi: bool = False) -> Counter:
    c = Counter()
    for r in rows:
        values = r[q].split("; ") if multi else [r[q]]
        c.update(v for v in values if v)
    return c


def barh(ax, labels: list[str], values: list[int], total: int) -> None:
    bars = ax.barh(labels[::-1], values[::-1], color=BLUE)
    for bar, v in zip(bars, values[::-1]):
        ax.text(
            bar.get_width() + 0.2,
            bar.get_y() + bar.get_height() / 2,
            f"{v} ({pct(v, total)})",
            va="center",
        )
    ax.set_xlim(0, max(values) * 1.3)
    ax.xaxis.set_visible(False)
    ax.spines["bottom"].set_visible(False)


def chart(
    name: str, title: str, labels: list[str], values: list[int], total: int
) -> None:
    fig, ax = plt.subplots(figsize=(8, 0.5 * len(labels) + 1))
    barh(ax, labels, values, total)
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(ASSETS / name, dpi=200)
    plt.close(fig)


def likert_chart(rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(8, 3.6))
    colors = ["#C00000", "#F4B183", "#D9D9D9", "#9DC3E6", "#2E75B6"]
    labels = list(LIKERT.values())[::-1]
    for i, q in enumerate(list(LIKERT)[::-1]):
        c = Counter(int(r[q]) for r in rows)
        left = 0
        for score in range(1, 6):
            share = c[score] / len(rows) * 100
            ax.barh(
                i,
                share,
                left=left,
                color=colors[score - 1],
                label=str(score) if i == 0 else None,
            )
            if share >= 7:
                ax.text(
                    left + share / 2,
                    i,
                    f"{share:.0f}%",
                    ha="center",
                    va="center",
                    fontsize=9,
                )
            left += share
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlim(0, 100)
    ax.set_xlabel("% респондентів")
    ax.legend(
        title="Оцінка",
        ncol=5,
        loc="upper center",
        bbox_to_anchor=(0.4, -0.25),
        frameon=False,
    )
    fig.tight_layout()
    fig.savefig(ASSETS / "survey_likert.png", dpi=200)
    plt.close(fig)


def main() -> None:
    rows = list(csv.DictReader(DATA.open(encoding="utf-8")))
    target = [r for r in rows if r["Q1"] == "Так"]
    n = len(target)

    freq = counts(target, "Q7")
    tools = counts(target, "Q8", multi=True).most_common()
    wtp = counts(target, "Q17")
    feature = counts(target, "Q18").most_common()
    themes = counts(target, "theme").most_common()
    answered_open = sum(1 for r in target if r["Q19"])

    print(f"Відповідей усього: {len(rows)}")
    print(f"Пройшли скринінг: {n} ({pct(n, len(rows))})")
    print(f"Q2 труднощі: {dict(counts(target, 'Q2'))}")
    often = freq["Щодня"] + freq["Кілька разів на тиждень"]
    print(
        f"Щодня: {freq['Щодня']} ({pct(freq['Щодня'], n)}), щодня або часто: {often} ({pct(often, n)})"
    )
    print("Поточні рішення:", [(k, v, pct(v, n)) for k, v in tools])
    for q, name in LIKERT.items():
        v = [int(r[q]) for r in target]
        print(
            f"{q} {name}: середнє {statistics.mean(v):.2f}, медіана {statistics.median(v):g}"
        )
    print("WTP:", [(k, wtp[k], pct(wtp[k], n)) for k in WTP_ORDER])
    print("Функція:", [(k, v, pct(v, n)) for k, v in feature])
    print(
        f"Відкриті відповіді: {answered_open}; теми:", [(k, v) for k, v in themes if k]
    )
    for q in ("Q3", "Q5", "Q6", "Q9", "Q11"):
        print(q, counts(target, q).most_common())
    print("Q4", counts(target, "Q4", multi=True).most_common())
    print("Q10", counts(target, "Q10", multi=True).most_common())

    ASSETS.mkdir(parents=True, exist_ok=True)
    chart(
        "survey_frequency.png",
        "Як часто ви стикаєтесь з організаційними проблемами?",
        FREQ_ORDER,
        [freq[k] for k in FREQ_ORDER],
        n,
    )
    chart(
        "survey_tools.png",
        "Яким чином ви зараз ведете облік занять і оплат?",
        [k for k, _ in tools],
        [v for _, v in tools],
        n,
    )
    admin = counts(target, "Q9")
    chart(
        "survey_admin.png",
        "Скільки часу на тиждень іде на адміністрування?",
        ADMIN_ORDER,
        [admin[k] for k in ADMIN_ORDER],
        n,
    )
    chart(
        "survey_wtp.png",
        "Скільки ви готові платити щомісяця?",
        WTP_ORDER,
        [wtp[k] for k in WTP_ORDER],
        n,
    )
    chart(
        "survey_feature.png",
        "Яка функція для вас найважливіша?",
        [k for k, _ in feature],
        [v for _, v in feature],
        n,
    )
    likert_chart(target)


if __name__ == "__main__":
    main()
