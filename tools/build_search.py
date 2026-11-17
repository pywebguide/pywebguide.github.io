"""Строит assets/search-index.js: один элемент на раздел (заголовок h2) каждой страницы."""
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {"404.html"}
SKIP_TAGS = {"pre", "script", "style", "template", "svg", "button", "textarea", "select", "legend"}


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.sections = []
        self.stack = []
        self.in_main = False
        self.in_title = False
        self.in_h2 = False
        self.skip = 0
        self.h2_count = 0
        self.current = {"id": "", "h": "", "x": []}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self.in_title = True
        if tag == "main":
            self.in_main = True
        if tag in SKIP_TAGS:
            self.skip += 1
        if self.in_main and tag == "h2":
            self.flush()
            self.h2_count += 1
            self.current = {"id": attrs.get("id") or f"sec-{self.h2_count}", "h": "", "x": []}
            self.in_h2 = True

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "main":
            self.flush()
            self.in_main = False
        if tag in SKIP_TAGS and self.skip:
            self.skip -= 1
        if tag == "h2":
            self.in_h2 = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        elif self.in_main and not self.skip:
            if self.in_h2:
                self.current["h"] += data
            else:
                self.current["x"].append(data)

    def flush(self):
        text = re.sub(r"\s+", " ", " ".join(self.current["x"])).strip()
        if text or self.current["h"]:
            self.sections.append({
                "id": self.current["id"],
                "h": re.sub(r"\s+", " ", self.current["h"]).strip(),
                "x": text[:1200],
            })


# Русские страницы лежат в корне, переводы — в kk/ и en/. Адреса в индексе относительные:
# поиск на казахской странице ведёт на страницы из kk/
LANGUAGES = {"ru": (ROOT, "search-index.js"), "kk": (ROOT / "kk", "search-index.kk.js"), "en": (ROOT / "en", "search-index.en.js")}


def build(folder):
    items = []
    for path in sorted(folder.glob("*.html")):
        # SKIP — страница «не найдено»; google<код>.html и yandex_<код>.html — файлы подтверждения прав
        if path.name in SKIP or re.match(r"(google[0-9a-f]+|yandex_[0-9a-f]+)\.html$", path.name):
            continue
        page = Page()
        page.feed(path.read_text(encoding="utf-8"))
        title = page.title.split(" — ")[0].strip()
        for section in page.sections:
            items.append({
                "u": f"{path.name}#{section['id']}" if section["h"] else path.name,
                "p": title,
                "h": section["h"] or title,
                "x": section["x"],
            })
    return items


def main():
    for lang, (folder, name) in LANGUAGES.items():
        if not folder.is_dir():
            continue
        items = build(folder)
        target = ROOT / "assets" / name
        target.write_text("window.PYWEB_SEARCH=" + json.dumps(items, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
        print(f"Индекс {lang}: {len(items)} разделов, {target.stat().st_size // 1024} КБ")


if __name__ == "__main__":
    main()
