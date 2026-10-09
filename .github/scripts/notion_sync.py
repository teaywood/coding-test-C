"""Sync BaekjoonHub Python/C submissions without executing solution code.

Existing pages are identified by their GitHub folder URL. Only the code block
inside the 'GitHub 자동 기록' toggle is updated; user properties and notes remain.
"""
import argparse
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.parse import quote, unquote
from urllib.request import Request, urlopen

DATA_SOURCE = "55795d92-4eca-480e-a9f8-9aa09e8d0ac9"
MANAGED = "GitHub 자동 기록"


def rich(text):
    return [{"type": "text", "text": {"content": text[i:i + 1900]}}
            for i in range(0, len(text), 1900)] or [{"type": "text", "text": {"content": ""}}]


def block(kind, text, **extra):
    return {"object": "block", "type": kind, kind: {"rich_text": rich(text), **extra}}


def parse_problem(repo, root, code_path):
    path = code_path.relative_to(root)
    folder = path.parent
    readme_path = code_path.parent / "README.md"
    if not readme_path.is_file():
        return None
    readme = readme_path.read_text(encoding="utf-8")
    match = re.search(r"^# \[level (\d+)\] (.*?) - (\d+)\s*$", readme, re.M)
    if not match:
        return None
    level, title, problem_id = match.groups()
    date = re.search(r"(\d{4})년\s*(\d{2})월\s*(\d{2})일", readme)
    link = re.search(r"\[문제 링크\]\(([^)]+)\)", readme)
    notes = readme.split("### 성능 요약")[0]
    notes = re.sub(r"^#.*\n+", "", notes, count=1)
    notes = re.sub(r"\[문제 링크\]\([^)]+\)\s*", "", notes, count=1).strip()
    notes = re.sub(r"^---\s*|\s*---$", "", notes).strip()
    explicit = re.search(r"## 핵심 (?:개념|아이디어)\s*\n([\s\S]*?)(?=\n---|\n#{1,3} |$)", notes)
    inline = re.search(r"^- 핵심 아이디어:\s*(.*)$", notes, re.M)
    core = re.sub(r"^- ", "", explicit.group(1).strip(), flags=re.M) if explicit else (inline.group(1) if inline else "")
    return {"title": title.strip(), "id": problem_id, "level": level,
            "language": "Python" if path.suffix == ".py" else "C",
            "code": code_path.read_text(encoding="utf-8"), "path": path.as_posix(),
            "date": "-".join(date.groups()) if date else None,
            "url": f"https://github.com/{repo}/tree/main/{quote(folder.as_posix(), safe='/')}",
            "problem_url": link.group(1) if link else None, "notes": notes, "core": core}


def discover(repo, root):
    problems = []
    for code in sorted(root.rglob("*")):
        if code.suffix not in (".py", ".c") or not code.is_file():
            continue
        # Restrict to the actual BaekjoonHub problem layout, not tooling.
        if "프로그래머스" not in code.relative_to(root).parts:
            continue
        problem = parse_problem(repo, root, code)
        if problem:
            problems.append(problem)
    urls = [p["url"] for p in problems]
    if len(urls) != len(set(urls)):
        raise ValueError("One folder contains multiple solution files; resolve before syncing.")
    return problems


class Notion:
    def __init__(self, token):
        self.token = token

    def call(self, method, path, payload=None):
        request = Request("https://api.notion.com/v1/" + path,
                          data=json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None,
                          method=method,
                          headers={"Authorization": "Bearer " + self.token,
                                   "Content-Type": "application/json",
                                   "Notion-Version": "2025-09-03"})
        for attempt in range(5):
            time.sleep(0.36)
            try:
                with urlopen(request, timeout=45) as response:
                    return json.load(response)
            except HTTPError as error:
                # Retry rejected rate-limited requests, but never blindly retry
                # uncertain page creation responses, which can create duplicates.
                if error.code == 429 and attempt < 4:
                    time.sleep(min(float(error.headers.get("Retry-After", "2")), 60))
                    continue
                raise RuntimeError(f"Notion {method} {path}: HTTP {error.code}. Check permissions and rerun.") from None
        raise RuntimeError("Notion rate limit retries exhausted")

    def pages(self):
        payload = {"page_size": 100}
        result = []
        while True:
            response = self.call("POST", f"data_sources/{DATA_SOURCE}/query", payload)
            result.extend(response["results"])
            if not response.get("has_more"):
                return result
            payload["start_cursor"] = response["next_cursor"]

    def children(self, block_id):
        path = f"blocks/{block_id}/children?page_size=100"
        result = []
        while True:
            response = self.call("GET", path)
            result.extend(response["results"])
            if not response.get("has_more"):
                return result
            path = f"blocks/{block_id}/children?page_size=100&start_cursor={response['next_cursor']}"


def code_block(problem):
    return block("code", problem["code"], language="python" if problem["language"] == "Python" else "c")


def initial_children(problem):
    children = [block("paragraph", f"PROGRAMMERS · Level {problem['level']} · {problem['id']}"),
                block("paragraph", problem["url"])]
    if problem["problem_url"]:
        children.append(block("paragraph", problem["problem_url"]))
    children.append(block("toggle", MANAGED, children=[
        block("paragraph", "GitHub에 저장된 풀이입니다. 자동화는 이 영역의 코드만 갱신합니다."),
        code_block(problem)]))
    if problem["notes"]:
        children.append(block("heading_2", "GitHub에 남긴 공부 메모"))
        # Preserve original notes as plain text without interpreting/rewriting them.
        for paragraph in re.split(r"\n\s*\n", problem["notes"]):
            children.append(block("paragraph", paragraph))
    for heading in ("배운 내용", "막힌 점과 해결", "다음에 할 것"):
        children.append(block("heading_2", heading))
    return children


def create_page(api, problem):
    properties = {"제목": {"title": rich(problem["title"])},
                  "언어": {"select": {"name": problem["language"]}},
                  "분야": {"select": {"name": "알고리즘"}},
                  "GitHub 풀이": {"url": problem["url"]}}
    if problem["date"]:
        properties["공부 날짜"] = {"date": {"start": problem["date"]}}
    if problem["core"]:
        properties["핵심 개념"] = {"rich_text": rich(problem["core"])}
    return api.call("POST", "pages", {"parent": {"type": "data_source_id", "data_source_id": DATA_SOURCE},
                                     "icon": {"type": "emoji", "emoji": "💻"},
                                     "properties": properties, "children": initial_children(problem)})


def plain(items):
    return "".join(t.get("plain_text", t.get("text", {}).get("content", "")) for t in items)


def refresh_code(api, page, problem):
    matches = [b for b in api.children(page["id"]) if b["type"] == "toggle"
               and plain(b["toggle"]["rich_text"]) == MANAGED]
    if len(matches) != 1:
        print(f"Skipped '{problem['title']}': managed toggle was removed or duplicated.")
        return "skipped"
    codes = [b for b in api.children(matches[0]["id"]) if b["type"] == "code"]
    if len(codes) != 1:
        print(f"Skipped '{problem['title']}': managed code block was removed or duplicated.")
        return "skipped"
    language = "python" if problem["language"] == "Python" else "c"
    if plain(codes[0]["code"]["rich_text"]) == problem["code"] and codes[0]["code"]["language"] == language:
        return "unchanged"
    api.call("PATCH", f"blocks/{codes[0]['id']}", {"code": {"rich_text": rich(problem["code"]), "language": language}})
    # Never overwrite title, date, core concepts, understanding state or notes.
    return "updated"


def sync(api, problems):
    existing = {}
    for page in api.pages():
        value = page.get("properties", {}).get("GitHub 풀이", {}).get("url")
        if value:
            existing.setdefault(unquote(value).rstrip("/"), []).append(page)
    counts = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    for problem in problems:
        key = unquote(problem["url"]).rstrip("/")
        matches = existing.get(key, [])
        if len(matches) > 1:
            print(f"Skipped duplicate URL: {problem['title']}")
            counts["skipped"] += 1
        elif matches:
            counts[refresh_code(api, matches[0], problem)] += 1
        else:
            page = create_page(api, problem)
            existing[key] = [page]
            counts["created"] += 1
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    repo = os.environ["GITHUB_REPOSITORY"]
    if repo not in ("teaywood/coding-test", "teaywood/coding-test-C"):
        raise SystemExit("This sync is configured only for Taeyeon's two coding-test repositories.")
    problems = discover(repo, Path.cwd())
    if args.dry_run:
        print(json.dumps([{k: v for k, v in p.items() if k not in ("code", "notes")} for p in problems], ensure_ascii=False, indent=2))
        return
    token = os.environ.get("NOTION_TOKEN", "")
    if not token:
        raise SystemExit("Set the NOTION_TOKEN repository secret, then run this workflow again.")
    counts = sync(Notion(token), problems)
    print(json.dumps(counts))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as output:
            output.write("## Notion 공부 기록 동기화\n" + "\n".join(f"- {k}: {v}" for k, v in counts.items()) + "\n")
    if counts["skipped"]:
        raise SystemExit("Some pages need review; see skipped items above. No user notes were changed.")


if __name__ == "__main__":
    main()
