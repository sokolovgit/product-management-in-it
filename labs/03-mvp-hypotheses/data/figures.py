"""Рисунки звіту за журналом Concierge MVP: динаміка оплат після нагадувань, звіти репетиторів і канали."""

from pathlib import Path

import matplotlib.pyplot as plt

from analyze_log import DAYS, TUTORS, WINDOW, episodes, load, within

ASSETS = Path(__file__).parents[1] / "docs/report/assets"
plt.rcParams.update({"font.family": "Arial", "font.size": 10})

BLUE, ORANGE, GRAY = "#2a78d6", "#eb6834", "#9a9893"
INK, MUTED = "#0b0b0b", "#52514e"


def style(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color(GRAY)
    ax.spines["bottom"].set_color(GRAY)
    ax.tick_params(colors=MUTED)
    ax.grid(axis="y", color="#e6e5e0", linewidth=0.8)
    ax.set_axisbelow(True)


def payments_figure(rows, eps):
    fig, (left, right) = plt.subplots(1, 2, figsize=(10, 3.8))

    days = list(range(WINDOW + 1, DAYS + 1))
    shares = []
    for d in days:
        closed = [e for e in eps if e["start"] <= d - WINDOW]
        shares.append(
            100 * sum(within(e, d) for e in closed) / len(closed) if closed else None
        )
    pts = [(d, s) for d, s in zip(days, shares) if s is not None]
    left.plot(
        [d for d, _ in pts],
        [s for _, s in pts],
        color=BLUE,
        linewidth=2,
        marker="o",
        markersize=5,
    )
    left.axhline(60, color=ORANGE, linewidth=1.5, linestyle="--")
    left.text(DAYS, 61.5, "поріг 60%", color=MUTED, ha="right", fontsize=9)
    last_d, last_s = pts[-1]
    left.annotate(
        f"{last_s:.1f}%",
        (last_d, last_s),
        xytext=(0, 8),
        textcoords="offset points",
        ha="center",
        color=INK,
    )
    left.set_ylim(0, 100)
    left.set_xlim(0.5, DAYS + 0.5)
    left.set_xticks(range(1, DAYS + 1))
    left.set_xlabel("День тесту", color=MUTED)
    left.set_ylabel("Погашено за ≤ 3 дні, %", color=MUTED)
    left.set_title(
        "Частка боргів, погашених після нагадування", color=INK, fontsize=10.5
    )
    style(left)

    true_rem = [
        sum(
            1
            for r in rows
            if r["day"] == d and r["event"] in ("reminder_first", "reminder_repeat")
        )
        for d in range(1, DAYS + 1)
    ]
    false_rem = [
        sum(1 for r in rows if r["day"] == d and r["event"] == "reminder_false")
        for d in range(1, DAYS + 1)
    ]
    x = list(range(1, DAYS + 1))
    right.bar(
        x,
        true_rem,
        color=BLUE,
        width=0.7,
        label="борг є",
        edgecolor="white",
        linewidth=1,
    )
    right.bar(
        x,
        false_rem,
        bottom=true_rem,
        color=ORANGE,
        width=0.7,
        label="оплату вже внесено",
        edgecolor="white",
        linewidth=1,
    )
    right.set_xticks(x)
    right.yaxis.get_major_locator().set_params(integer=True)
    right.set_xlabel("День тесту", color=MUTED)
    right.set_ylabel("Нагадувань за день", color=MUTED)
    right.set_title("Надіслані нагадування", color=INK, fontsize=10.5)
    right.legend(frameon=False, loc="upper left", labelcolor=MUTED)
    style(right)

    fig.tight_layout()
    fig.savefig(ASSETS / "concierge_payments.png", dpi=200)
    plt.close(fig)


def tutors_figure(rows, eps):
    fig, (left, right) = plt.subplots(
        1, 2, figsize=(10, 3.6), gridspec_kw={"width_ratios": [2, 1]}
    )

    w1 = [
        sum(
            1
            for r in rows
            if r["tutor"] == t and r["event"] == "tutor_report" and r["day"] <= 7
        )
        for t in TUTORS
    ]
    w2 = [
        sum(
            1
            for r in rows
            if r["tutor"] == t and r["event"] == "tutor_report" and r["day"] > 7
        )
        for t in TUTORS
    ]
    x = range(len(TUTORS))
    left.bar([i - 0.19 for i in x], w1, width=0.36, color=BLUE, label="тиждень 1")
    left.bar([i + 0.19 for i in x], w2, width=0.36, color=ORANGE, label="тиждень 2")
    left.axhline(5, color=GRAY, linewidth=1.2, linestyle="--")
    left.text(
        len(TUTORS) - 0.5, 5.15, "поріг 5 з 7", color=MUTED, ha="right", fontsize=9
    )
    left.set_xticks(list(x), TUTORS)
    left.set_ylim(0, 8.6)
    left.set_ylabel("Днів зі звітом про оплати", color=MUTED)
    left.set_title("Регулярність звітів репетиторів", color=INK, fontsize=10.5)
    left.legend(frameon=False, loc="upper center", ncol=2, labelcolor=MUTED)
    style(left)

    eligible = [e for e in eps if e["start"] <= DAYS - WINDOW]
    channels = ["Telegram", "Viber"]
    shares, labels = [], []
    for ch in channels:
        sub = [e for e in eligible if e["channel"] == ch]
        paid = sum(map(within, sub))
        shares.append(100 * paid / len(sub))
        labels.append(f"{paid} з {len(sub)}")
    right.bar(channels, shares, width=0.55, color=BLUE)
    for i, (s, lab) in enumerate(zip(shares, labels)):
        right.text(
            i,
            s + 2,
            f"{s:.0f}%\n{lab}",
            ha="center",
            va="bottom",
            color=INK,
            fontsize=9,
        )
    right.axhline(60, color=ORANGE, linewidth=1.5, linestyle="--")
    right.set_ylim(0, 115)
    right.set_yticks(range(0, 101, 20))
    right.set_ylabel("Погашено за ≤ 3 дні, %", color=MUTED)
    right.set_title("За каналом нагадування", color=INK, fontsize=10.5)
    style(right)

    fig.tight_layout()
    fig.savefig(ASSETS / "concierge_tutors.png", dpi=200)
    plt.close(fig)


def main():
    rows = load()
    eps = episodes(rows)
    payments_figure(rows, eps)
    tutors_figure(rows, eps)


if __name__ == "__main__":
    main()
