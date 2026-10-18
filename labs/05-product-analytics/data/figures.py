"""Рисунки звіту: воронка AARRR, схематичні криві утримання і прогноз MRR на 12 місяців."""

import json
from pathlib import Path

import matplotlib.pyplot as plt

HERE = Path(__file__).parent
ASSETS = HERE.parent / "docs/report/assets"
plt.rcParams.update({"font.family": "Arial", "font.size": 10})

BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#9a9893"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e5e0"

# Схематичні цілі утримання (% від когорти) на день N після реєстрації.
DAYS = [0, 1, 3, 7, 14, 21, 30, 45, 60, 75, 90]
ALL_USERS = [100, 55, 44, 35, 26, 21, 18, 16, 15, 14.5, 14]
ACTIVATED = [100, 88, 84, 78, 70, 65, 60, 57, 55, 54, 53]


def style(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRAY)
    ax.tick_params(colors=MUTED)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def funnel_figure(results):
    steps = [("Відвідувачі", 6000)] + [
        (r["step"].split(" (")[0].split(" –")[0], r["value"]) for r in results["funnel"]
    ]
    labels = ["Відвідувачі", "Реєстрації", "Activation", "D30 Retained", "Платять"]
    values = [v for _, v in steps]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    y = range(len(values))[::-1]
    colors = [GRAY, BLUE, ORANGE, BLUE, BLUE]
    ax.barh(list(y), values, color=colors, height=0.6)
    for yi, v, lab, i in zip(y, values, labels, range(len(values))):
        conv = (
            "" if i == 0 else f"  {100 * v / values[i - 1]:.0f}% від попереднього етапу"
        )
        ax.text(
            v + 60,
            yi,
            f"{v:,}".replace(",", " ") + conv,
            va="center",
            color=INK,
            fontsize=9,
        )
    ax.set_yticks(list(y), labels)
    ax.set_xlim(0, 9000)
    ax.set_xlabel(
        "Користувачів на місяць (ціль на третій місяць після запуску)", color=MUTED
    )
    style(ax)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(ASSETS / "funnel.png", dpi=200)
    plt.close(fig)


def retention_figure():
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.plot(
        DAYS,
        ACTIVATED,
        color=BLUE,
        linewidth=2,
        marker="o",
        markersize=4,
        label="Виконали Aha Moment за 7 днів",
    )
    ax.plot(
        DAYS,
        ALL_USERS,
        color=ORANGE,
        linewidth=2,
        marker="o",
        markersize=4,
        label="Усі зареєстровані",
    )
    ax.axvspan(45, 90, color=GRID, alpha=0.6, zorder=0)
    ax.text(67, 92, "плато", ha="center", color=MUTED, fontsize=9)
    for d, v in ((30, 60), (30, 18), (7, 35)):
        ax.annotate(
            f"D{d}: {v}%",
            (d, v),
            xytext=(6, 6),
            textcoords="offset points",
            color=INK,
            fontsize=8.5,
        )
    ax.set_xlim(0, 90)
    ax.set_ylim(0, 105)
    ax.set_xticks([0, 7, 14, 30, 45, 60, 90])
    ax.set_xlabel("День після реєстрації", color=MUTED)
    ax.set_ylabel("Активні, % когорти", color=MUTED)
    ax.legend(
        frameon=False, loc="center right", labelcolor=MUTED, bbox_to_anchor=(1, 0.5)
    )
    style(ax)
    fig.tight_layout()
    fig.savefig(ASSETS / "retention_curve.png", dpi=200)
    plt.close(fig)


def mrr_figure(results):
    proj = results["projection"]
    months = [f"{r['n']}\n{r['month']}" for r in proj]
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(8, 5.4), sharex=True, gridspec_kw={"height_ratios": [3, 2]}
    )
    top.plot(
        months,
        [r["mrr"] for r in proj],
        color=BLUE,
        linewidth=2,
        marker="o",
        markersize=4,
    )
    top.axvspan(5.5, 7.5, color=GRID, alpha=0.6, zorder=0)
    top.text(
        6.5, 2150, "літо:\nchurn 12%", ha="center", va="top", color=MUTED, fontsize=8.5
    )
    last = proj[-1]
    top.annotate(
        f"${last['mrr']:,.0f}".replace(",", " "),
        (11, last["mrr"]),
        xytext=(-6, 8),
        textcoords="offset points",
        ha="right",
        color=INK,
        fontsize=9,
    )
    top.set_ylabel("MRR, $", color=MUTED)
    style(top)
    bottom.bar(
        months,
        [r["new"] for r in proj],
        color=BLUE,
        width=0.38,
        align="edge",
        label="нові клієнти",
    )
    bottom.bar(
        months,
        [r["churned"] for r in proj],
        color=ORANGE,
        width=-0.38,
        align="edge",
        label="churned",
    )
    bottom.set_ylabel("Клієнтів за місяць", color=MUTED)
    bottom.legend(frameon=False, loc="upper left", labelcolor=MUTED, ncol=2)
    style(bottom)
    fig.tight_layout()
    fig.savefig(ASSETS / "mrr_projection.png", dpi=200)
    plt.close(fig)


def main():
    results = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
    funnel_figure(results)
    retention_figure()
    mrr_figure(results)


if __name__ == "__main__":
    main()
