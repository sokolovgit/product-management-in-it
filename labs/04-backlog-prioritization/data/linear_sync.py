"""Перенесення беклогу в Linear: Epic -> Project, Feature -> батьківська issue, Story -> sub-issue."""

import json
import urllib.request
from pathlib import Path

from backlog import DOD, EPICS, FEATURES, RELEASES, RICE, STORIES, TITLES

HERE = Path(__file__).parent
STATE = HERE / "linear_map.json"
API = "https://api.linear.app/graphql"
KEY = (Path.home() / ".config/linear/api_key").read_text().strip()
TEAM_KEY = "CLA"

PRIORITY = {"Must": 1, "Should": 2, "Could": 3, "Won't": 4}
RELEASE_COLORS = {
    "MVP": "#2a78d6",
    "Release 2": "#eb6834",
    "Backlog": "#9a9893",
    "Не зараз": "#52514e",
}


def gql(query, variables=None):
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Content-Type": "application/json", "Authorization": KEY},
    )
    with urllib.request.urlopen(req) as resp:
        body = json.load(resp)
    if body.get("errors"):
        raise RuntimeError(json.dumps(body["errors"], ensure_ascii=False))
    return body["data"]


def load_state():
    return (
        json.loads(STATE.read_text())
        if STATE.exists()
        else {"projects": {}, "issues": {}, "labels": {}}
    )


def save_state(state):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def team():
    data = gql(
        """query($key: String!) { teams(filter: {key: {eq: $key}}) { nodes {
            id issueEstimationType
            states { nodes { id name } }
            labels { nodes { id name } }
        } } }""",
        {"key": TEAM_KEY},
    )
    return data["teams"]["nodes"][0]


def ensure_labels(t, state):
    existing = {l["name"]: l["id"] for l in t["labels"]["nodes"]}
    if "Реліз" not in existing:
        existing["Реліз"] = gql(
            "mutation($i: IssueLabelCreateInput!) { issueLabelCreate(input: $i) { issueLabel { id } } }",
            {
                "i": {
                    "teamId": t["id"],
                    "name": "Реліз",
                    "color": "#2a78d6",
                    "isGroup": True,
                }
            },
        )["issueLabelCreate"]["issueLabel"]["id"]
    for name, color in RELEASE_COLORS.items():
        if name not in existing:
            existing[name] = gql(
                "mutation($i: IssueLabelCreateInput!) { issueLabelCreate(input: $i) { issueLabel { id } } }",
                {
                    "i": {
                        "teamId": t["id"],
                        "name": name,
                        "color": color,
                        "parentId": existing["Реліз"],
                    }
                },
            )["issueLabelCreate"]["issueLabel"]["id"]
    state["labels"] = existing


def story_description(s):
    release = next(r for r, ids in RELEASES.items() if s["id"] in ids)
    lines = [
        f"**User Story.** {s['story']}",
        "",
        f"**Тип:** {s['type']}  ",
        f"**JTBD / Pain:** {s['jtbd']}  ",
        f"**MoSCoW:** {s['moscow']} Have – {s['moscow_reason']}  ",
        f"**Реліз:** {release}",
    ]
    if s["id"] in RICE:
        reach, impact, conf = RICE[s["id"]]
        effort = s["sp"] / 20
        lines.append(
            f"**RICE:** Reach {reach} × Impact {impact:g} × Confidence {conf}% / Effort {effort:g} = {round(reach * impact * conf / 100 / effort)}"
        )
    lines += ["", "## Acceptance Criteria", ""]
    for i, (given, when, then) in enumerate(s["ac"], 1):
        lines.append(f"{i}. **Given** {given}, **When** {when}, **Then** {then}")
    if s["notes"]:
        lines += ["", "## Нотатки / залежності", "", s["notes"]]
    lines += ["", "Definition of Done – у описі проєкту."]
    return "\n".join(lines)


def project_content(epic):
    feats = [f for f in FEATURES if f["epic"] == epic["id"]]
    lines = [
        f"**JTBD:** {epic['jtbd']}",
        "",
        f"**Business Value:** {epic['value']}",
        "",
        "**Features:** " + ", ".join(f"{f['id']} {f['name']}" for f in feats),
        "",
        "## Definition of Done",
        "",
    ]
    lines += [f"{i}. {item}" for i, item in enumerate(DOD, 1)]
    return "\n".join(lines)


def create_issue(t, state, key, payload):
    if key in state["issues"]:
        return state["issues"][key]["id"]
    payload = {"teamId": t["id"], **payload}
    issue = gql(
        "mutation($i: IssueCreateInput!) { issueCreate(input: $i) { issue { id identifier url } } }",
        {"i": payload},
    )["issueCreate"]["issue"]
    state["issues"][key] = issue
    save_state(state)
    print(issue["identifier"], key)
    return issue["id"]


def main():
    state = load_state()
    t = team()
    if t["issueEstimationType"] != "fibonacci":
        gql(
            'mutation($id: String!) { teamUpdate(id: $id, input: {issueEstimationType: "fibonacci", issueEstimationExtended: true}) { success } }',
            {"id": t["id"]},
        )
    ensure_labels(t, state)
    save_state(state)
    states = {s["name"]: s["id"] for s in t["states"]["nodes"]}
    labels = state["labels"]
    release_of = {sid: r for r, ids in RELEASES.items() for sid in ids}

    for epic in EPICS:
        if epic["id"] in state["projects"]:
            continue
        project = gql(
            "mutation($i: ProjectCreateInput!) { projectCreate(input: $i) { project { id url } } }",
            {
                "i": {
                    "name": f"{epic['id']} {epic['name']}",
                    "teamIds": [t["id"]],
                    "description": epic["value"][:255],
                    "content": project_content(epic),
                    "priority": {"High": 2, "Med": 3, "Low": 4}[epic["priority"]],
                }
            },
        )["projectCreate"]["project"]
        state["projects"][epic["id"]] = project
        save_state(state)
        print("project", epic["id"])

    for f in FEATURES:
        stories = [s for s in STORIES if s["feature"] == f["id"]]
        in_mvp = any(release_of[s["id"]] == "MVP" for s in stories)
        parent = create_issue(
            t,
            state,
            f["id"],
            {
                "title": f"{f['id']} · {f['name']}",
                "description": f"**User Value:** {f['value']}\n\n**Stories:** {', '.join(s['id'] for s in stories)}",
                "projectId": state["projects"][f["epic"]]["id"],
                "labelIds": [labels["Feature"]],
                "stateId": states["Todo" if in_mvp else "Backlog"],
            },
        )
        for s in stories:
            release = release_of[s["id"]]
            label_ids = [labels[release]]
            if s["type"] == "Покращення":
                label_ids.append(labels["Improvement"])
            payload = {
                "title": f"{s['id']} · {TITLES[s['id']]}",
                "description": story_description(s),
                "projectId": state["projects"][f["epic"]]["id"],
                "parentId": parent,
                "priority": PRIORITY[s["moscow"]],
                "labelIds": label_ids,
                "stateId": states["Todo" if release == "MVP" else "Backlog"],
            }
            if isinstance(s["sp"], int):
                payload["estimate"] = s["sp"]
            create_issue(t, state, s["id"], payload)


if __name__ == "__main__":
    main()
