"""Моделювання відповідей 12 репетиторів на Kano-опитування та Opportunity Scoring -> kano.csv, opportunity.csv."""

import csv
import random
from pathlib import Path

from backlog import KANO_FEATURES, OUTCOMES

SEED = 4
HERE = Path(__file__).parent

RESPONDENTS = [
    ("Р1", "Аліна", "студенти"),
    ("Р2", "Софія", "студенти"),
    ("Р3", "Респондент опитування", "студенти"),
    ("Р4", "Респондент опитування", "студенти"),
    ("Р5", "Андрій", "студенти"),
    ("Р6", "Ірина", "вчителі"),
    ("Р7", "Олена", "вчителі"),
    ("Р8", "Респондент опитування", "вчителі"),
    ("Р9", "Респондент опитування", "вчителі"),
    ("Р10", "Респондент опитування", "вчителі"),
    ("Р11", "Респондент опитування", "інші"),
    ("Р12", "Респондент опитування", "інші"),
]

# Категорія Kano, яку модель закладає кожному респонденту Р1–Р12 для функцій K1–K10.
KANO_PROFILE = {
    "K1": "MMOMMMMMOMMI",
    "K2": "OOMOAOMOOIOA",
    "K3": "OAOAOOAROOAO",
    "K4": "AAIAOAIARAAI",
    "K5": "IOIAOOOMOAIO",
    "K6": "IMIOIMMMOMIM",
    "K7": "AAIRAIRIAIAI",
    "K8": "IIIIOMMOMMII",
    "K9": "IIIQIAIAOIII",
    "K10": "IIAIMMMMOMIM",
}

# Відповіді: 1 – дуже задоволений, 2 – так і має бути, 3 – байдуже, 4 – можу прийняти, 5 – дуже незадоволений.
MIDDLE = [2, 3, 4]
PAIRS = {
    "M": [(f, 5) for f in MIDDLE],
    "O": [(1, 5)],
    "A": [(1, d) for d in MIDDLE],
    "I": [(f, d) for f in MIDDLE for d in MIDDLE],
    "R": [(f, 1) for f in MIDDLE + [5]] + [(5, d) for d in MIDDLE],
    "Q": [(1, 1), (5, 5)],
}

# Середні Importance і Satisfaction, на які налаштована модель, та зсув для вчителів.
OUTCOME_TARGETS = {
    "O1": (9.0, 3.3, 0.0),
    "O2": (8.5, 2.5, -0.6),
    "O3": (7.7, 3.6, 1.2),
    "O4": (7.8, 9.0, 0.0),
    "O5": (7.0, 3.9, 1.4),
    "O6": (5.8, 3.2, -1.2),
    "O7": (7.3, 4.1, 1.6),
    "O8": (5.2, 4.4, 1.4),
    "O9": (6.9, 5.6, 0.8),
    "O10": (6.4, 7.0, 0.0),
}


def clamp(x):
    return max(1, min(10, round(x)))


def main():
    rng = random.Random(SEED)

    with (HERE / "kano.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["respondent", "name", "segment", "feature", "functional", "dysfunctional"]
        )
        for key, _, _ in KANO_FEATURES:
            for (rid, name, segment), category in zip(RESPONDENTS, KANO_PROFILE[key]):
                functional, dysfunctional = rng.choice(PAIRS[category])
                writer.writerow([rid, name, segment, key, functional, dysfunctional])

    with (HERE / "opportunity.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["respondent", "name", "segment", "outcome", "importance", "satisfaction"]
        )
        teachers = sum(seg == "вчителі" for *_, seg in RESPONDENTS) / len(RESPONDENTS)
        for key, _ in OUTCOMES:
            imp, sat, shift = OUTCOME_TARGETS[key]
            for rid, name, segment in RESPONDENTS:
                delta = shift * ((1 - teachers) if segment == "вчителі" else -teachers)
                importance = clamp(rng.gauss(imp + delta, 1.0))
                satisfaction = clamp(rng.gauss(sat, 1.1))
                writer.writerow([rid, name, segment, key, importance, satisfaction])

    print("-> kano.csv, opportunity.csv")


if __name__ == "__main__":
    main()
