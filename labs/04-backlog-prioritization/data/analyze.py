"""RICE, класифікація Kano, Opportunity Score і фінальний беклог; таблиці підставляються у звіт між мітками gen."""

import csv
import json
import re
from collections import Counter
from pathlib import Path

from backlog import (
    DECISIONS,
    DOD,
    EPICS,
    FEATURES,
    KANO_FEATURES,
    OUTCOMES,
    RICE,
    STORIES,
    STORY_KANO,
    STORY_OUTCOME,
    TITLES,
)

HERE = Path(__file__).parent
REPORT = HERE.parent / "docs/report/report.md"

DAYS_PER_SP = 1
DAYS_PER_MONTH = 20

KANO_TABLE = {
    1: "QAAAO",
    2: "RIIIM",
    3: "RIIIM",
    4: "RIIIM",
    5: "RRRRQ",
}
KANO_ORDER = "MOAI"
KANO_NAMES = {
    "M": "Must-be",
    "O": "Performance",
    "A": "Delighter",
    "I": "Indifferent",
    "R": "Reverse",
    "Q": "Questionable",
}
DECISION_LABEL = {
    "MVP": "MVP",
    "R2": "Release 2",
    "Backlog": "Backlog",
    "Відкласти": "❌ Відкласти",
}


def fmt(x, digits=1):
    s = f"{x:,.{digits}f}".replace(",", " ")
    return s.rstrip("0").rstrip(".") if "." in s else s


def rice():
    by_id = {s["id"]: s for s in STORIES}
    rows = []
    for sid, (reach, impact, conf) in RICE.items():
        effort = by_id[sid]["sp"] * DAYS_PER_SP / DAYS_PER_MONTH
        score = reach * impact * conf / 100 / effort
        rows.append(
            {
                "id": sid,
                "reach": reach,
                "impact": impact,
                "conf": conf,
                "sp": by_id[sid]["sp"],
                "effort": effort,
                "score": round(score),
            }
        )
    rows.sort(key=lambda r: -r["score"])
    for rank, r in enumerate(rows, 1):
        r["rank"] = rank
    return rows


def kano():
    with (HERE / "kano.csv").open(encoding="utf-8") as f:
        answers = list(csv.DictReader(f))
    result = {}
    for key, name, story in KANO_FEATURES:
        counts = Counter(
            KANO_TABLE[int(a["functional"])][int(a["dysfunctional"]) - 1]
            for a in answers
            if a["feature"] == key
        )
        valid = {c: n for c, n in counts.items() if c != "Q"}
        top = max(valid.values())
        final = next(c for c in KANO_ORDER + "R" if valid.get(c) == top)
        segments = {}
        for seg in ("студенти", "вчителі"):
            seg_counts = Counter(
                KANO_TABLE[int(a["functional"])][int(a["dysfunctional"]) - 1]
                for a in answers
                if a["feature"] == key and a["segment"] == seg
            )
            seg_counts.pop("Q", None)
            seg_top = max(seg_counts.values())
            segments[seg] = next(
                c for c in KANO_ORDER + "R" if seg_counts.get(c) == seg_top
            )
        result[key] = {
            "name": name,
            "story": story,
            "counts": {c: counts.get(c, 0) for c in "MOAIRQ"},
            "valid": sum(valid.values()),
            "final": final,
            "tie": sum(1 for n in valid.values() if n == top) > 1,
            "segments": segments,
        }
    return result, answers


def opportunity():
    with (HERE / "opportunity.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    result = {}
    for key, text in OUTCOMES:
        sub = [r for r in rows if r["outcome"] == key]
        imp = round(sum(int(r["importance"]) for r in sub) / len(sub), 1)
        sat = round(sum(int(r["satisfaction"]) for r in sub) / len(sub), 1)
        opp = round(imp + max(imp - sat, 0), 1)
        if imp < 6:
            zone = "Low Importance"
        elif opp > 12:
            zone = "Underserved"
        elif sat >= imp:
            zone = "Overserved"
        else:
            zone = "Contested"
        teachers = [r for r in sub if r["segment"] == "вчителі"]
        result[key] = {
            "text": text,
            "importance": imp,
            "satisfaction": sat,
            "opp": opp,
            "zone": zone,
            "importance_teachers": round(
                sum(int(r["importance"]) for r in teachers) / len(teachers), 1
            ),
            "n": len(sub),
        }
    return result


def table(header, rows, widths):
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("-" * w for w in widths) + " |",
    ]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def render(rice_rows, kano_res, kano_answers, opp_res):
    by_id = {s["id"]: s for s in STORIES}
    feat = {f["id"]: f for f in FEATURES}
    blocks = {}

    blocks["epics"] = table(
        ["Epic ID", "Назва Epic", "Пов'язаний JTBD", "Business Value", "Пріоритет"],
        [[e["id"], e["name"], e["jtbd"], e["value"], e["priority"]] for e in EPICS],
        [8, 17, 32, 27, 16],
    )

    frows = []
    for f in FEATURES:
        stories = [s for s in STORIES if s["feature"] == f["id"]]
        sp = sum(s["sp"] for s in stories if isinstance(s["sp"], int))
        unknown = " + ?" if any(not isinstance(s["sp"], int) for s in stories) else ""
        frows.append(
            [f["id"], f["name"], f["epic"], f["value"], len(stories), f"{sp}{unknown}"]
        )
    blocks["features"] = table(
        ["Feature ID", "Назва Feature", "Epic", "User Value", "Stories", "SP"],
        frows,
        [11, 20, 7, 40, 10, 8],
    )

    blocks["dod"] = "\n".join(f"{i}. {item}." for i, item in enumerate(DOD, 1))

    story_blocks = []
    for n, s in enumerate(STORIES):
        f = feat[s["feature"]]
        rows = [
            ["ID", s["id"]],
            ["Feature", f"{f['id']} «{f['name']}»"],
            ["User Story", s["story"]],
            ["Тип", s["type"]],
            ["Пов'язаний JTBD або Pain", s["jtbd"]],
            ["Story Points", s["sp"]],
            ["Пріоритет (MoSCoW)", f"{s['moscow']} Have. {s['moscow_reason']}"],
        ]
        for i, (given, when, then) in enumerate(s["ac"], 1):
            rows.append(
                [
                    f"Acceptance Criteria #{i}",
                    f"Given {given}, When {when}, Then {then}",
                ]
            )
        rows.append(["Definition of Done", "Загальний DoD команди (підрозділ 1.3)"])
        rows.append(["Нотатки / Обмеження / Залежності", s["notes"] or "–"])
        caption = f"Таблиця {{t}} – {s['id']} «{TITLES[s['id']]}»"
        story_blocks.append((caption, table(["Поле", "Зміст"], rows, [26, 74])))
    blocks["stories"] = story_blocks

    blocks["moscow"] = table(
        ["Категорія", "Stories", "Кількість", "SP", "Частка SP"],
        [
            [
                f"{m} Have",
                ", ".join(s["id"] for s in STORIES if s["moscow"] == m),
                sum(1 for s in STORIES if s["moscow"] == m),
                sum(
                    s["sp"]
                    for s in STORIES
                    if s["moscow"] == m and isinstance(s["sp"], int)
                )
                or "?",
                f"{100 * sum(s['sp'] for s in STORIES if s['moscow'] == m and isinstance(s['sp'], int)) / sum(s['sp'] for s in STORIES if isinstance(s['sp'], int)):.0f}%",
            ]
            for m in ("Must", "Should", "Could", "Won't")
        ],
        [14, 42, 15, 9, 14],
    )

    blocks["rice"] = table(
        [
            "Ранг",
            "ID",
            "Назва User Story",
            "Reach",
            "Impact",
            "Conf.",
            "Effort",
            "RICE",
        ],
        [
            [
                r["rank"],
                r["id"],
                short(by_id[r["id"]]),
                fmt(r["reach"], 0),
                fmt(r["impact"], 2),
                f"{r['conf']}%",
                fmt(r["effort"], 2),
                fmt(r["score"], 0),
            ]
            for r in rice_rows
        ],
        [7, 11, 29, 10, 9, 8, 9, 10],
    )

    blocks["kano_questions"] = table(
        ["#", "Функція", "Functional запитання", "Dysfunctional запитання"],
        [
            [
                key[1:],
                name,
                f"Як ви почуватиметесь, якщо в Classno буде: {name[0].lower() + name[1:]}?",
                f"Як ви почуватиметесь, якщо в Classno не буде: {name[0].lower() + name[1:]}?",
            ]
            for key, name, _ in KANO_FEATURES
        ],
        [5, 25, 35, 35],
    )

    kano_rows = []
    for key, k in kano_res.items():
        c = k["counts"]
        final = KANO_NAMES[k["final"]] + (" *" if k["tie"] else "")
        kano_rows.append(
            [key, k["name"], c["M"], c["O"], c["A"], c["I"], c["R"], c["Q"], final]
        )
    blocks["kano"] = table(
        ["#", "Функція", "M", "O", "A", "I", "R", "Q", "Категорія"],
        kano_rows,
        [6, 33, 6, 6, 6, 6, 6, 6, 17],
    )

    seg_rows = [
        [
            key,
            k["name"],
            KANO_NAMES[k["segments"]["студенти"]],
            KANO_NAMES[k["segments"]["вчителі"]],
        ]
        for key, k in kano_res.items()
    ]
    blocks["kano_segments"] = table(
        ["#", "Функція", "Студенти", "Вчителі"], seg_rows, [6, 44, 22, 22]
    )

    resp = sorted(
        {(a["respondent"], a["segment"]) for a in kano_answers},
        key=lambda x: int(x[0][1:]),
    )
    raw_rows = []
    for rid, seg in resp:
        row = [rid, seg]
        for key, _, _ in KANO_FEATURES:
            a = next(
                a
                for a in kano_answers
                if a["respondent"] == rid and a["feature"] == key
            )
            row.append(f"{a['functional']}/{a['dysfunctional']}")
        raw_rows.append(row)
    blocks["kano_raw"] = table(
        ["Р", "Сегмент"] + [k for k, _, _ in KANO_FEATURES],
        raw_rows,
        [6, 13] + [8] * 10,
    )

    zone_ua = {
        "Underserved": "Underserved",
        "Contested": "Contested",
        "Overserved": "Overserved",
        "Low Importance": "Low Importance",
    }
    prio = {
        "Underserved": "High",
        "Contested": "Med",
        "Overserved": "Low",
        "Low Importance": "Low",
    }
    blocks["opportunity"] = table(
        [
            "#",
            "Outcome (бажаний результат)",
            "Import.",
            "Satisf.",
            "Opp.",
            "Зона",
            "Пріоритет",
        ],
        [
            [
                key[1:],
                o["text"],
                fmt(o["importance"]),
                fmt(o["satisfaction"]),
                fmt(o["opp"]),
                zone_ua[o["zone"]],
                prio[o["zone"]],
            ]
            for key, o in opp_res.items()
        ],
        [5, 33, 11, 10, 8, 17, 16],
    )

    rice_by = {r["id"]: r for r in rice_rows}
    final_rows = []
    for r in rice_rows:
        sid = r["id"]
        decision, why = DECISIONS[sid]
        kkey = STORY_KANO.get(sid)
        okey = STORY_OUTCOME[sid]
        final_rows.append(
            [
                sid,
                short(by_id[sid]),
                fmt(rice_by[sid]["score"], 0),
                kano_res[kkey]["final"] if kkey else "–",
                f"{fmt(opp_res[okey]['opp'])} ({okey})",
                DECISION_LABEL[decision],
                why,
            ]
        )
    order = {"MVP": 0, "R2": 1, "Backlog": 2, "Відкласти": 3}
    final_rows.sort(
        key=lambda row: (order[DECISIONS[row[0]][0]], -rice_by[row[0]]["score"])
    )
    final_rows = [[i] + row for i, row in enumerate(final_rows, 1)]
    blocks["final"] = table(
        [
            "Ранг",
            "ID",
            "Назва Story",
            "RICE",
            "Kano",
            "Opp.",
            "Рішення",
            "Обґрунтування",
        ],
        final_rows,
        [8, 11, 18, 10, 9, 10, 12, 22],
    )
    return blocks


def short(story):
    return TITLES[story["id"]]


def inject(blocks):
    text = REPORT.read_text(encoding="utf-8")

    def repl(m):
        name = m.group(1)
        block = blocks[name]
        if name == "stories":
            block = "\n\n".join(f"{cap}\n\n{tbl}" for cap, tbl in block)
        return f"<!-- gen:{name} -->\n{block}\n<!-- /gen:{name} -->"

    text = re.sub(r"<!-- gen:(\w+) -->.*?<!-- /gen:\1 -->", repl, text, flags=re.S)

    counter = iter(range(1, 1000))
    text = re.sub(
        r"Таблиця (?:\{t\}|\d+) – ", lambda m: f"Таблиця {next(counter)} – ", text
    )
    REPORT.write_text(text, encoding="utf-8")


def main():
    rice_rows = rice()
    kano_res, kano_answers = kano()
    opp_res = opportunity()
    (HERE / "results.json").write_text(
        json.dumps(
            {"rice": rice_rows, "kano": kano_res, "opportunity": opp_res},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    if REPORT.exists():
        inject(render(rice_rows, kano_res, kano_answers, opp_res))
    for r in rice_rows:
        print(r["rank"], r["id"], r["score"], r["effort"])
    for key, k in kano_res.items():
        print(key, k["final"], k["counts"], "tie" if k["tie"] else "", k["segments"])
    for key, o in opp_res.items():
        print(
            key,
            o["importance"],
            o["satisfaction"],
            o["opp"],
            o["zone"],
            o["importance_teachers"],
        )


if __name__ == "__main__":
    main()
