"""Проверка разметки для поисковых систем и мессенджеров без сети. Код выхода 1 при ошибках.

Для каждой страницы трёх языков: title до 60 символов и description 120–160 без повторов между страницами,
canonical на свой адрес, hreflang на ru, kk, en и x-default, og:image и twitter:image указывают на картинку
1200×630, которая есть в assets/og/, JSON-LD разбирается и устроен по schema.org (обязательные поля типов),
все страницы есть в sitemap.xml, а 404 закрыта noindex и в карту не попала; llms.txt ссылается на все страницы.

    python tools/check_seo.py
"""
import json
import re
import struct
import sys
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout  # noqa: E402

ROOT = layout.ROOT
SITE = layout.SITE
TITLE_MAX = 60
DESCRIPTION = (120, 160)
ISO_DURATION = re.compile(r"^P(?!$)(\d+D)?(T(?=\d)(\d+H)?(\d+M)?(\d+S)?)?$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Обязательные и разрешённые свойства типов, которые использует сайт (по schema.org и требованиям Google)
REQUIRED = {
    "WebSite": {"name", "url"},
    "WebPage": {"name", "url"},
    "ContactPage": {"name", "url"},
    "LearningResource": {"name", "url", "description", "inLanguage", "educationalLevel", "learningResourceType", "author", "dateModified"},
    "Course": {"name", "description", "provider", "url", "hasPart"},
    "BreadcrumbList": {"itemListElement"},
    "FAQPage": {"mainEntity"},
}
ALLOWED = {
    "WebSite": {"@id", "name", "url", "inLanguage", "description", "author"},
    "WebPage": {"@id", "name", "description", "url", "inLanguage", "dateModified", "isPartOf"},
    "LearningResource": {"@id", "name", "description", "url", "inLanguage", "educationalLevel", "learningResourceType",
                         "timeRequired", "isAccessibleForFree", "dateModified", "image", "isPartOf", "author"},
    "Course": {"@id", "name", "description", "url", "inLanguage", "educationalLevel", "isAccessibleForFree", "provider",
               "author", "dateModified", "image", "offers", "hasCourseInstance", "hasPart"},
    "BreadcrumbList": {"@id", "itemListElement"},
    "FAQPage": {"@id", "url", "inLanguage", "mainEntity"},
}
ALLOWED["ContactPage"] = ALLOWED["WebPage"]


class Head(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.in_title = False
        self.meta = defaultdict(list)
        self.links = defaultdict(list)
        self.alternates = {}
        self.json_ld = []
        self.in_ld = False
        self.lang = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "title":
            self.in_title = True
        elif tag == "meta":
            key = a.get("name") or a.get("property")
            if key:
                self.meta[key].append(a.get("content", ""))
        elif tag == "link":
            if a.get("rel") == "alternate" and a.get("hreflang"):
                self.alternates[a["hreflang"]] = a.get("href")
            elif a.get("rel"):
                self.links[a["rel"]].append(a.get("href"))
        elif tag == "script" and a.get("type") == "application/ld+json":
            self.in_ld = True
            self.json_ld.append("")

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "script":
            self.in_ld = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.in_ld:
            self.json_ld[-1] += data


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def local(url):
    """Файл сайта для абсолютного адреса https://pywebguide.github.io/..."""
    if not url.startswith(SITE):
        return None
    path = urlsplit(url).path.lstrip("/")
    return ROOT / (path + "index.html" if path == "" or path.endswith("/") else path)


def check_node(node, where, errors, lang):
    kind = node.get("@type")
    if kind not in REQUIRED:
        errors.append(f"{where}: тип {kind!r} не проверяется — добавьте его в tools/check_seo.py")
        return
    missing = REQUIRED[kind] - node.keys()
    if missing:
        errors.append(f"{where}: у {kind} нет {', '.join(sorted(missing))}")
    unknown = node.keys() - ALLOWED[kind] - {"@type"}
    if unknown:
        errors.append(f"{where}: у {kind} неизвестные свойства {', '.join(sorted(unknown))}")
    if "inLanguage" in node and node["inLanguage"] != lang:
        errors.append(f"{where}: {kind}.inLanguage = {node['inLanguage']}, а страница на {lang}")
    for key in ("url",):
        if key in node and (local(node[key]) is None or not local(node[key]).is_file()):
            errors.append(f"{where}: {kind}.{key} ведёт не на страницу сайта: {node[key]}")
    if "dateModified" in node and not ISO_DATE.match(node["dateModified"]):
        errors.append(f"{where}: dateModified не в формате ГГГГ-ММ-ДД: {node['dateModified']}")
    if "timeRequired" in node and not ISO_DURATION.match(node["timeRequired"]):
        errors.append(f"{where}: timeRequired не в формате ISO 8601: {node['timeRequired']}")
    for key in ("author", "provider"):
        if key in node and (node[key].get("@type") not in ("Person", "Organization") or not node[key].get("name")):
            errors.append(f"{where}: {kind}.{key} должен быть Person или Organization с name")
    if kind == "BreadcrumbList":
        items = node["itemListElement"]
        if len(items) < 2:
            errors.append(f"{where}: в BreadcrumbList меньше двух элементов")
        for n, item in enumerate(items, 1):
            if item.get("@type") != "ListItem" or item.get("position") != n or not item.get("name") or not item.get("item"):
                errors.append(f"{where}: элемент {n} BreadcrumbList должен быть ListItem с position {n}, name и item")
            elif local(item["item"]) is None or not local(item["item"]).is_file():
                errors.append(f"{where}: хлебная крошка ведёт не на страницу сайта: {item['item']}")
    if kind == "FAQPage":
        for q in node["mainEntity"]:
            answer = q.get("acceptedAnswer") or {}
            if q.get("@type") != "Question" or not q.get("name") or answer.get("@type") != "Answer" or not answer.get("text"):
                errors.append(f"{where}: в FAQPage вопрос без name или без acceptedAnswer.text")
    if kind == "Course":
        for part in node["hasPart"]:
            target = local(part.get("url", ""))
            if part.get("@type") != "LearningResource" or not part.get("name") or not target or not target.is_file():
                errors.append(f"{where}: урок курса без name или с адресом не на страницу сайта: {part.get('url')}")
        instance = node.get("hasCourseInstance", {})
        if instance and (instance.get("@type") != "CourseInstance" or not instance.get("courseMode")):
            errors.append(f"{where}: hasCourseInstance должен быть CourseInstance с courseMode")


def visible_text(html_text):
    body = re.search(r"<body\b.*</body>", html_text, re.S)
    return layout.plain(re.sub(r"<(script|style|template)\b.*?</\1>", "", body.group(0) if body else "", flags=re.S))


def main():
    errors = []
    titles, descriptions = defaultdict(list), defaultdict(list)
    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    in_sitemap = set(re.findall(r"<loc>(.*?)</loc>", sitemap))
    llms = (ROOT / "llms.txt").read_text(encoding="utf-8") if (ROOT / "llms.txt").exists() else ""
    if not llms:
        errors.append("llms.txt: нет файла, запустите python tools/layout.py")
    elif not llms.startswith("# ") or "\n> " not in llms:
        errors.append("llms.txt: по llmstxt.org файл начинается с заголовка # и краткого описания в цитате >")
    for path in layout.pages():
        lang, slug = layout.page_lang(path)
        name = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        head = Head()
        head.feed(text)
        title = head.title.strip()
        description = (head.meta.get("description") or [""])[0]
        url = layout.page_url(lang, slug)

        if not title:
            errors.append(f"{name}: нет title")
        elif len(title) > TITLE_MAX:
            errors.append(f"{name}: title {len(title)} символов, нужно до {TITLE_MAX}: {title}")
        if not description:
            errors.append(f"{name}: нет description")
        elif not DESCRIPTION[0] <= len(description) <= DESCRIPTION[1]:
            errors.append(f"{name}: description {len(description)} символов, нужно {DESCRIPTION[0]}–{DESCRIPTION[1]}")
        titles[title].append(name)
        descriptions[description].append(name)

        for key in ("og:image", "twitter:image"):
            values = head.meta.get(key) or []
            if len(values) != 1:
                errors.append(f"{name}: {key} — {len(values)} шт., нужен один")
                continue
            target = local(values[0])
            if target is None or not target.is_file():
                errors.append(f"{name}: {key} — нет файла {values[0]}")
            elif png_size(target) != (1200, 630):
                errors.append(f"{name}: {key} — картинка не 1200×630: {values[0]}")
            elif target.stat().st_size > 300_000:
                errors.append(f"{name}: {key} — больше 300 КБ, WhatsApp может не показать превью")
        for key in ("og:title", "og:description", "og:image:alt", "twitter:card"):
            if not (head.meta.get(key) or [""])[0]:
                errors.append(f"{name}: нет {key}")
        for key, values in head.meta.items():
            if len(values) > 1 and key != "og:locale:alternate":
                errors.append(f"{name}: meta {key} повторяется {len(values)} раза")

        if slug == "404.html":
            if "noindex" not in (head.meta.get("robots") or [""])[0]:
                errors.append(f"{name}: страница 404 без noindex")
            if url in in_sitemap:
                errors.append(f"sitemap.xml: в карте сайта страница 404 {url}")
            continue

        canonical = head.links.get("canonical") or []
        if canonical != [url]:
            errors.append(f"{name}: canonical {canonical}, нужен {url}")
        if (head.meta.get("og:url") or [""])[0] != url:
            errors.append(f"{name}: og:url не совпадает с canonical")
        for other in (*layout.LANGS, "x-default"):
            want = layout.page_url("ru" if other == "x-default" else other, slug)
            got = head.alternates.get(other)
            if got != want:
                errors.append(f"{name}: hreflang {other} = {got}, нужен {want}")
            elif not local(got).is_file():
                errors.append(f"{name}: hreflang {other} ведёт на несуществующую страницу {got}")
        if url not in in_sitemap:
            errors.append(f"sitemap.xml: нет страницы {url}")
        if f"]({url})" not in llms:
            errors.append(f"llms.txt: нет ссылки на {url}")

        if not head.json_ld:
            errors.append(f"{name}: нет JSON-LD")
        seen = visible_text(text)
        for block in head.json_ld:
            try:
                data = json.loads(block)
            except json.JSONDecodeError as error:
                errors.append(f"{name}: JSON-LD не разбирается: {error}")
                continue
            if data.get("@context") != "https://schema.org":
                errors.append(f"{name}: в JSON-LD @context не https://schema.org")
            for node in data.get("@graph", [data]):
                check_node(node, name, errors, lang)
                # FAQ — только то, что читатель видит на странице
                if node.get("@type") == "FAQPage":
                    for q in node["mainEntity"]:
                        if q["name"] not in seen or q["acceptedAnswer"]["text"] not in seen:
                            errors.append(f"{name}: вопрос FAQ не найден в тексте страницы: {q['name'][:60]}")

    for value, names in titles.items():
        if len(names) > 1:
            errors.append(f"title повторяется на {', '.join(names)}: {value}")
    for value, names in descriptions.items():
        if len(names) > 1 and value:
            errors.append(f"description повторяется на {', '.join(names)}")
    pages = {layout.page_url(*layout.page_lang(p)) for p in layout.pages() if p.name != "404.html"}
    for url in in_sitemap - pages:
        errors.append(f"sitemap.xml: страницы нет на сайте: {url}")

    for error in errors:
        print("ОШИБКА", error)
    print(f"Страниц: {len(layout.pages())}, ошибок: {len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
