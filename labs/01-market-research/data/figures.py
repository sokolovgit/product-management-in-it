"""Рисунки звіту: affinity map за інтерв'ю та емоційна крива CJM."""

import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ASSETS = Path(__file__).parents[1] / "docs/report/assets"
plt.rcParams.update({"font.family": "Arial"})

# Кластер: (кількість стікерів, колір, приклади стікерів з нотаток інтерв'ю)
CLUSTERS = {
    "Незручно нагадувати про гроші": (
        12,
        "#FFE08A",
        [
            "Соромно писати мамі, що винна за 3 заняття (1)",
            "Не пам'ятаю, хто скинув за тиждень (1)",
            "Помилявся в пакетах на свою користь (3)",
            "Гроші в конверті через дитину (4)",
        ],
    ),
    "Облік розкиданий по інструментах": (
        11,
        "#A7D8F0",
        [
            "Calendar + нотатки + Telegram (1)",
            "Журнал + Excel + Viber (2)",
            "Calendly не знає про пакет (3)",
            "Таблицю ламають троє людей (5)",
        ],
    ),
    "Перенесення ламають розклад": (
        9,
        "#F7B6B6",
        [
            "Перенос за годину – дірка в розкладі (1)",
            "Блекаут – переписую розклад (2)",
            "Діти приходять не в той день (4)",
        ],
    ),
    "Вечори йдуть на рутину": (
        8,
        "#C9E4B4",
        [
            "Неділя з журналом і калькулятором (2)",
            "5–6 нагадувань щовечора (4)",
            "День на зарплати викладачам (5)",
        ],
    ),
    "Батьки хочуть бачити прогрес": (
        7,
        "#D9C3F0",
        [
            "22 учні – кожному не напишу (2)",
            "Звіт у один клік (2)",
            "Батьки самі бачать оплати (4)",
        ],
    ),
    "Наявні програми складні або дорогі": (
        6,
        "#FFD1A6",
        [
            "Англійською і багато кнопок (2)",
            "$15 за 5 учнів – смішно (3)",
            "Бот ніхто не підтримує (5)",
        ],
    ),
    "Прозорість знімає конфлікти": (
        5,
        "#B8E0D2",
        [
            "Спільна історія оплат (4)",
            "Нагадування «не від мене» (1)",
        ],
    ),
}

STAGES = ["Awareness", "Consideration", "Decision", "Onboarding", "Retention"]
EMOTIONS = [2, 3, 4, 3, 5]
MOMENTS = [
    "Втратила оплату\nза 3 заняття",
    "Західні CRM дорогі\nй англомовні",
    "Безкоштовно до 5 учнів,\nукраїнською",
    "Вручну вносить\n8 учнів",
    "Aha: борг оплачено\nпісля автонагадування",
]


def affinity_map() -> None:
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 2)
    ax.axis("off")
    for i, (title, (count, color, notes)) in enumerate(CLUSTERS.items()):
        col, row = i % 4, 1 - i // 4
        x0, y0 = col + 0.05, row + 0.05
        ax.add_patch(
            FancyBboxPatch(
                (x0, y0),
                0.9,
                0.9,
                boxstyle="round,pad=0.01",
                fc="#F4F4F4",
                ec="#BBBBBB",
            )
        )
        ax.text(
            x0 + 0.45,
            y0 + 0.85,
            f"{title}\n({count} стікерів)",
            ha="center",
            va="top",
            fontsize=11,
            fontweight="bold",
        )
        for j, note in enumerate(notes):
            nx, ny = x0 + 0.04 + (j % 2) * 0.43, y0 + 0.43 - (j // 2) * 0.36
            ax.add_patch(
                FancyBboxPatch(
                    (nx, ny),
                    0.39,
                    0.3,
                    boxstyle="square,pad=0",
                    fc=color,
                    ec="#999999",
                    lw=0.5,
                )
            )
            ax.text(
                nx + 0.195,
                ny + 0.15,
                textwrap.fill(note, 20),
                ha="center",
                va="center",
                fontsize=9,
            )
    ax.text(
        3.5,
        0.5,
        "У дужках – номер\nучасника інтерв'ю",
        ha="center",
        va="center",
        fontsize=11,
        color="#555555",
    )
    fig.tight_layout()
    fig.savefig(ASSETS / "affinity_map.png", dpi=200)
    plt.close(fig)


def emotion_curve() -> None:
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.plot(STAGES, EMOTIONS, marker="o", markersize=9, color="#4472C4", lw=2.5)
    for x, (y, label) in enumerate(zip(EMOTIONS, MOMENTS)):
        ax.annotate(
            label,
            (x, y),
            textcoords="offset points",
            xytext=(0, 14),
            ha="center",
            fontsize=9,
        )
    ax.set_ylim(0.5, 6)
    ax.set_xlim(-0.4, len(STAGES) - 0.6)
    ax.set_yticks(range(1, 6))
    ax.set_ylabel("Емоція (1 – негативна, 5 – позитивна)")
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(ASSETS / "cjm_emotions.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    ASSETS.mkdir(parents=True, exist_ok=True)
    affinity_map()
    emotion_curve()
