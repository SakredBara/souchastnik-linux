#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"


def load_json(name):
    with (DATA / name).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def normalize(text):
    return re.sub(r"\s+", " ", text.lower().replace("ё", "е")).strip()


def load_articles():
    root = load_json("articles.json")
    return {str(a["code"]): a for a in root.get("articles", [])}


def law_candidates(text):
    t = normalize(text)
    root = load_json("triggers.json")
    found = []
    seen = set()
    for group in root.get("groups", []):
        words = [normalize(x) for x in group.get("words", [])]
        if not any(w and w in t for w in words):
            continue
        for code in group.get("codes", []):
            code = str(code)
            if code not in seen:
                seen.add(code)
                found.append(code)
    return found


def labels_for_text(text):
    root = load_json("agents.json")
    templates = dict(root.get("templates", {}))
    if root.get("template"):
        templates.setdefault("agent", root["template"])
    results = []
    lowered = text.lower()
    for section in ("agents", "services"):
        for item in root.get(section, []):
            strict = bool(item.get("strict", False))
            haystack = text if strict else lowered
            forms = item.get("forms", [])
            exact = item.get("exact", [])
            hit = False
            for form in forms:
                needle = form if strict else form.lower()
                if " " in needle:
                    hit = haystack.endswith(needle) or (needle in haystack)
                else:
                    hit = bool(re.search(r"(?<![\w-])" + re.escape(needle) + r"[\w-]*", haystack))
                if hit:
                    break
            if not hit:
                words = re.findall(r"[A-Za-zА-Яа-яЁё'-]+", text)
                for word in words:
                    probe = word if strict else word.lower()
                    if any(probe == (x if strict else x.lower()) for x in exact):
                        hit = True
                        break
            if hit:
                kind = item.get("kind", "agent")
                template = templates.get(kind, "{NAME}")
                marker = template.replace("{NAME}", str(item.get("name", "")).upper())
                results.append({"name": item.get("name", ""), "kind": kind, "marker": marker})
    return results


def format_article(article):
    return f"ст. {article['code']} {article.get('act', '')} · {article.get('title', '')} · {article.get('penalty', '')}"


def main():
    parser = argparse.ArgumentParser(description="Соучастник для Arch Linux/CachyOS: проверка законов и меток без экранной клавиатуры")
    parser.add_argument("text", nargs="*", help="текст для проверки; если не указан, читается stdin")
    parser.add_argument("--json", action="store_true", dest="as_json", help="машиночитаемый вывод")
    args = parser.parse_args()
    text = " ".join(args.text).strip() if args.text else __import__("sys").stdin.read().strip()
    articles = load_articles()
    codes = law_candidates(text)
    candidate_articles = [articles[c] for c in codes if c in articles]
    labels = labels_for_text(text)
    result = {"text": text, "law_candidates": candidate_articles, "labels": labels}
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if candidate_articles:
        print("Возможные статьи по словарю триггеров:")
        for article in candidate_articles:
            print(" - " + format_article(article))
        print("\nВажно: это кандидаты по ключевым словам, а не юридическое заключение.")
    else:
        print("По локальному словарю триггеров кандидаты статей не найдены.")
    if labels:
        print("\nМетки:")
        for label in labels:
            print(" - " + label["marker"])


if __name__ == "__main__":
    main()
