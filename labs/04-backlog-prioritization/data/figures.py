"""Рисунки звіту: матриця Opportunity Scoring і User Story Map з реліз-розрізом."""

import json
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import FancyBboxPatch, Patch

from backlog import RELEASES, STORIES, TITLES

HERE = Path(__file__).parent
ASSETS = HERE.parent / "docs/report/assets"
plt.rcParams.update({"font.family": "Arial", "font.size": 10})

INK, MUTED, GRID = "#0b0b0b", "#52514e", "#9a9893"
ZONES = [
    ("Low Importance", "#ecebe6"),
    ("Overserved", "#cfe7d9"),
    ("Contested", "#d6e6f8"),
    ("Underserved", "#fbd9c8"),
]

JOURNEY = [
    ("Почати роботу", ["US-007", "US-001", "US-008", "US-009"]),
    (
        "Вести розклад",
        [
            "US-002",
            "US-003",
            "US-020",
            "US-021",
            "US-022",
            "US-017",
            "US-018",
            "US-019",
        ],
    ),
    ("Відмітити оплату", ["US-004", "US-014", "US-006", "US-016"]),
    ("Бачити борги", ["US-005", "US-015"]),
    (
        "Отримати борг",
        ["US-010", "US-011", "US-012", "US-013", "US-024", "US-025", "US-023"],
    ),
    ("Звітувати батькам", ["US-027", "US-026", "US-028"]),
]



def zone(imp, sat):
    if imp < 6:
        return 0
    if imp + max(imp - sat, 0) > 12:
        return 3
    if sat >= imp:
        return 1
    return 2


def opportunity_matrix(opp):
    fig, ax = plt.subplots(figsize=(8, 6.4))
    xs = np.linspace(1, 10, 400)
    ys = np.linspace(1, 10, 400)
    grid = np.array([[zone(y, x) for x in xs] for y in ys])
    ax.imshow(
        grid,
        origin="lower",
        extent=(1, 10, 1, 10),
        cmap=ListedColormap([c for _, c in ZONES]),
        vmin=0,
        vmax=3,
        aspect="auto",
    )

    offsets = {
        "O1": (8, 6),
        "O2": (8, -12),
        "O3": (8, 4),
        "O4": (-30, 6),
        "O5": (8, 4),
        "O6": (8, 4),
        "O7": (-64, 6),
        "O8": (8, -12),
        "O9": (8, -12),
        "O10": (8, -12),
    }
    for key, o in opp.items():
        ax.scatter(
            o["satisfaction"],
            o["importance"],
            s=60,
            color="#2a78d6",
            edgecolor="white",
            linewidth=1.5,
            zorder=3,
        )
        ax.annotate(
            f"{key} ({o['opp']:g})",
            (o["satisfaction"], o["importance"]),
            xytext=offsets[key],
            textcoords="offset points",
            color=INK,
            fontsize=9.5,
        )

    ax.set_xlim(1, 10)
    ax.set_ylim(1, 10)
    ax.set_xticks(range(1, 11))
    ax.set_yticks(range(1, 11))
    ax.set_xlabel(
        "Satisfaction – наскільки добре задовольняють поточні рішення", color=MUTED
    )
    ax.set_ylabel("Importance – наскільки важливо досягти результату", color=MUTED)
    ax.tick_params(colors=MUTED)
    for side in ax.spines.values():
        side.set_color(GRID)
    ax.legend(
        handles=[Patch(facecolor=c, label=n) for n, c in ZONES][::-1],
        loc="lower right",
        frameon=True,
        facecolor="white",
        edgecolor=GRID,
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(ASSETS / "opportunity_matrix.png", dpi=200)
    plt.close(fig)


def story_map():
    by_id = {s["id"]: s for s in STORIES}
    release_of = {sid: rel for rel, ids in RELEASES.items() for sid in ids}
    rows = list(RELEASES)
    row_colors = {
        "MVP": "#d6e6f8",
        "Release 2": "#fbe3c2",
        "Backlog": "#ecebe6",
        "Не зараз": "#f5f4f0",
    }
    card_w, card_h, gap = 1.3, 0.62, 0.06
    col_w = card_w + 0.12

    stacks = {(c, r): [] for c in range(len(JOURNEY)) for r in rows}
    for c, (_, ids) in enumerate(JOURNEY):
        for sid in ids:
            stacks[(c, release_of[sid])].append(sid)
    heights = {r: max(len(stacks[(c, r)]) for c in range(len(JOURNEY))) for r in rows}

    total_h = sum(max(h, 1) * (card_h + gap) + 0.25 for h in heights.values()) + 0.6
    fig_w = len(JOURNEY) * col_w + 1.1
    fig, ax = plt.subplots(figsize=(fig_w, total_h))
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, total_h)
    ax.axis("off")

    top = total_h - 0.5
    for c, (step, _) in enumerate(JOURNEY):
        x = 1.0 + c * col_w
        ax.add_patch(
            FancyBboxPatch(
                (x, top),
                card_w,
                0.38,
                boxstyle="round,pad=0.01,rounding_size=0.04",
                facecolor="#2a78d6",
                edgecolor="none",
            )
        )
        ax.text(
            x + card_w / 2,
            top + 0.19,
            step,
            ha="center",
            va="center",
            color="white",
            fontsize=7.5,
            fontweight="bold",
        )

    y = top - 0.15
    for r in rows:
        band_h = max(heights[r], 1) * (card_h + gap) + 0.15
        y_band = y - band_h
        ax.add_patch(
            plt.Rectangle(
                (0.05, y_band),
                fig_w - 0.1,
                band_h,
                facecolor=row_colors[r],
                edgecolor="none",
            )
        )
        ax.text(
            0.12,
            y_band + band_h - 0.12,
            r,
            ha="left",
            va="top",
            color=INK,
            fontsize=9,
            fontweight="bold",
        )
        for c in range(len(JOURNEY)):
            x = 1.0 + c * col_w
            for i, sid in enumerate(stacks[(c, r)]):
                cy = y - 0.08 - (i + 1) * (card_h + gap) + gap
                buffer = True if r == "MVP" and by_id[sid]["moscow"] != "Must" else None
                ax.add_patch(
                    FancyBboxPatch(
                        (x, cy),
                        card_w,
                        card_h,
                        boxstyle="round,pad=0.005,rounding_size=0.03",
                        facecolor="white",
                        edgecolor=GRID if buffer is None else "#2a78d6",
                        linewidth=0.6 if buffer is None else 1.0,
                        linestyle="-" if buffer is None else (0, (3, 2)),
                    )
                )
                label = "\n".join(textwrap.wrap(TITLES[sid], 16))
                ax.text(
                    x + 0.05,
                    cy + card_h - 0.06,
                    f"{sid} · {by_id[sid]['sp']} SP",
                    ha="left",
                    va="top",
                    color=MUTED,
                    fontsize=6.3,
                )
                ax.text(
                    x + 0.05,
                    cy + card_h - 0.19,
                    label,
                    ha="left",
                    va="top",
                    color=INK,
                    fontsize=7.4,
                )
        if r == "MVP":
            ax.plot(
                [0.05, fig_w - 0.05],
                [y_band - 0.02, y_band - 0.02],
                color="#d03b3b",
                linewidth=1.6,
                linestyle="--",
            )
            ax.text(
                fig_w - 0.08,
                y_band - 0.06,
                "реліз-розріз MVP",
                ha="right",
                va="top",
                color="#d03b3b",
                fontsize=8,
            )
            ax.text(
                0.12,
                y_band + 0.08,
                "пунктир – буфер\nShould / Could",
                ha="left",
                va="bottom",
                color=MUTED,
                fontsize=7,
            )
        y = y_band - 0.1

    fig.savefig(ASSETS / "story_map.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def main():
    results = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
    opportunity_matrix(results["opportunity"])
    story_map()


if __name__ == "__main__":
    main()
