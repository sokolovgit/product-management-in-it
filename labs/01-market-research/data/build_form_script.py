"""survey_questions.md + responses.csv -> google_form.gs (Apps Script, що створює форму і завантажує відповіді)."""

import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "google_form.gs"

TYPES = {
    "Одиночний вибір": "choice",
    "Множинний вибір": "checkbox",
    "Шкала 1–5": "scale",
    "Лайкерт 1–5": "scale",
    "Відкрите": "paragraph",
}
SCALE_LABELS = {
    "Q12": ["Зовсім не задоволений", "Повністю задоволений"],
    "Q13": ["Зовсім неважливо", "Дуже важливо"],
}
LIKERT_LABELS = ["Абсолютно не згоден", "Абсолютно згоден"]


def parse_questions() -> list[dict]:
    blocks, block = [], None
    for line in (HERE / "survey_questions.md").read_text(encoding="utf-8").splitlines():
        if m := re.match(r"## Блок \d+\. (.+)", line):
            block = {"title": m[1], "items": []}
            blocks.append(block)
        elif line.startswith("| Q"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            qid, text, kind = cells[:3]
            item = {"id": qid, "title": text, "type": TYPES[kind]}
            if item["type"] in ("choice", "checkbox"):
                item["options"] = cells[3].split(" / ")
            if item["type"] == "scale":
                item["labels"] = SCALE_LABELS.get(qid, LIKERT_LABELS)
            block["items"].append(item)
    return blocks


def parse_responses() -> list[dict]:
    rows = []
    for r in csv.DictReader((HERE / "responses.csv").open(encoding="utf-8")):
        rows.append(
            {
                k: (v.split("; ") if k in ("Q4", "Q8", "Q10") else v)
                for k, v in r.items()
                if k.startswith("Q") and v
            }
        )
    return rows


TEMPLATE = """// Згенеровано data/build_form_script.py. Запуск: script.google.com -> новий проєкт ->
// вставити цей файл -> обрати функцію createSurvey -> Run -> надати доступ.

const BLOCKS = __BLOCKS__;
const RESPONSES = __RESPONSES__;

function createSurvey() {
  const form = FormApp.create('Організація приватних занять: опитування репетиторів');
  form.setDescription(
    'Досліджую, як репетитори організовують розклад, облік занять і оплат. ' +
    'Опитування анонімне і займе близько 5 хвилин. Дякую за допомогу!'
  );
  form.setProgressBar(true);

  const sheet = SpreadsheetApp.create('Опитування репетиторів (відповіді)');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, sheet.getId());

  const items = {};
  let screening = null;
  BLOCKS.forEach((block, b) => {
    block.items.forEach((q, i) => {
      if (b > 0 && i === 0 || q.id === 'Q2') {
        form.addPageBreakItem().setTitle(block.title);
      }
      items[q.id] = addItem(form, q);
      if (q.id === 'Q1') screening = items[q.id];
    });
  });

  // «Ні» на Q1 завершує анкету.
  // add*Item() повертає вже типізоване запитання, тож as*Item() тут не потрібен.
  screening.setChoices([
    screening.createChoice('Так', FormApp.PageNavigationType.CONTINUE),
    screening.createChoice('Ні', FormApp.PageNavigationType.SUBMIT),
  ]);

  RESPONSES.forEach(r => {
    const response = form.createResponse();
    Object.keys(r).forEach(id => {
      const item = items[id];
      const value = item.getType() === FormApp.ItemType.SCALE ? Number(r[id]) : r[id];
      response.withItemResponse(item.createResponse(value));
    });
    response.submit();
  });

  // Обов'язковість вмикаємо після імпорту, щоб неповні анкети (Q1 = «Ні») пройшли.
  Object.keys(items).forEach(id => {
    if (id !== 'Q19') items[id].setRequired(true);
  });

  Logger.log('Форма (редагування): ' + form.getEditUrl());
  Logger.log('Форма (для респондентів): ' + form.getPublishedUrl());
  Logger.log('Таблиця відповідей: ' + sheet.getUrl());
  Logger.log('Відповідей: ' + form.getResponses().length);
}

function addItem(form, q) {
  if (q.type === 'choice') {
    return form.addMultipleChoiceItem().setTitle(q.title).setChoiceValues(q.options);
  }
  if (q.type === 'checkbox') {
    return form.addCheckboxItem().setTitle(q.title).setChoiceValues(q.options);
  }
  if (q.type === 'scale') {
    return form.addScaleItem().setTitle(q.title).setBounds(1, 5)
      .setLabels(q.labels[0], q.labels[1]);
  }
  return form.addParagraphTextItem().setTitle(q.title);
}
"""


def main() -> None:
    blocks, responses = parse_questions(), parse_responses()
    script = TEMPLATE.replace(
        "__BLOCKS__", json.dumps(blocks, ensure_ascii=False, indent=2)
    ).replace("__RESPONSES__", json.dumps(responses, ensure_ascii=False))
    OUT.write_text(script, encoding="utf-8")
    n = sum(len(b["items"]) for b in blocks)
    print(f"{OUT.name}: {n} запитань, {len(responses)} відповідей")


if __name__ == "__main__":
    main()
