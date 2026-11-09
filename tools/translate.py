"""Перевод страниц на казахский (kk/) и английский (en/) с памятью переводов.

Русская страница — источник. Из неё берутся текстовые фрагменты (заголовки, абзацы, подписи,
alt, aria-label, meta), в которых есть кириллица. Перевод каждого фрагмента хранится в
tools/i18n/<язык>.json: ключ — русский фрагмент, значение — перевод с той же разметкой внутри.
Одинаковые фрагменты на разных страницах переводятся один раз, поэтому термины совпадают.

    python tools/translate.py seed                 # пополнить память из уже переведённых страниц
    python tools/translate.py missing kk about.html  # что ещё не переведено -> tools/i18n/todo-kk.json
    python tools/translate.py add kk файл.json     # добавить переводы {номер из todo: перевод}
    python tools/translate.py build kk about.html  # собрать kk/about.html
    python tools/translate.py check                # собранные переводы совпадают с русскими страницами

После сборки: python tools/layout.py (меню, подвал, hreflang, карта сайта) и tools/check_site.py.
Код в <pre>, <textarea> и <template> не переводится. Задачи practice.html собирает tools/build_practice.py.
"""
import difflib
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMORY = ROOT / "tools" / "i18n"
SITE = "https://pywebguide.github.io/"
MARK = "<!-- Перевод собран tools/translate.py из {src}. Правьте tools/i18n/{lang}.json, а не этот файл. -->"
LOCALE = {"kk": "kk_KZ", "en": "en_GB"}
PRELOAD_RU = '<link rel="preload" href="assets/fonts/sofia-sans-extra-condensed-cyrillic-wght-normal.woff2" as="font" type="font/woff2" crossorigin>'
PRELOAD = {
    # В Sofia Sans нет казахских букв: заголовки на kk/ набраны Fira Sans Extra Condensed
    "kk": '<link rel="preload" href="../assets/fonts/fira-sans-extra-condensed-cyrillic-900-normal.woff2" as="font" type="font/woff2" crossorigin>\n'
          '  <link rel="preload" href="../assets/fonts/fira-sans-extra-condensed-cyrillic-ext-900-normal.woff2" as="font" type="font/woff2" crossorigin>',
    "en": '<link rel="preload" href="../assets/fonts/sofia-sans-extra-condensed-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>',
}

CYRILLIC = re.compile(r"[А-Яа-яЁё]")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
# Блоки: их содержимое делится на фрагменты; всё, что не блок, остаётся внутри фрагмента как разметка
BLOCK = {"html", "head", "body", "title", "header", "footer", "main", "nav", "section", "article", "aside", "div",
         "p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "dl", "dt", "dd", "table", "thead", "tbody",
         "tr", "td", "th", "caption", "figure", "figcaption", "details", "summary", "form", "fieldset", "legend",
         "label", "button", "blockquote", "select", "option", "dialog", "canvas"}
SKIP = {"script", "style", "pre", "textarea", "template", "svg", "noscript"}
ATTRS = {"alt", "title", "aria-label", "placeholder"}
META = {("name", "description"), ("property", "og:title"), ("property", "og:description"), ("property", "og:image:alt")}


TIME = re.compile(r'<time datetime="[^"]*">[^<]*</time>')


def norm(text):
    # Даты (<time>) в ключ не входят: перевод не теряется, когда меняется дата обновления
    return TIME.sub("<time>", re.sub(r"\s+", " ", text).strip())


class Units(HTMLParser):
    """Находит переводимые фрагменты и их места в исходном тексте страницы."""

    def __init__(self, source, any_text=False):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.any_text = any_text  # для сопоставления с готовым переводом: любой текст, не только кириллица
        self.lines = [0]
        for match in re.finditer("\n", source):
            self.lines.append(match.end())
        self.stack = []      # открытые блоки: [тег, начало текущего отрезка, есть ли в нём кириллица, путь]
        self.skip = 0        # глубина внутри <pre>, <script> и подобных
        self.skip_tag = []
        self.layout = 0      # меню и ссылки подвала собирает tools/layout.py
        self.layout_tag = []
        self.tasks = False   # задачи собирает tools/build_practice.py
        self.text_units = []  # (начало, конец, путь)
        self.attr_units = []  # (начало тега, сырой тег)

    def pos(self):
        line, col = self.getpos()
        return self.lines[line - 1] + col

    def close_run(self, end):
        if not self.stack:
            return
        top = self.stack[-1]
        if top[1] is not None and top[2] and not self.skip and not self.layout and not self.tasks:
            self.text_units.append((top[1], end, top[3]))
        top[1] = None
        top[2] = False

    def handle_starttag(self, tag, attrs):
        start = self.pos()
        raw = self.get_starttag_text()
        attrs_d = dict(attrs)
        if self.tasks:
            return
        if self.skip:
            if tag in SKIP:
                self.skip_tag.append(tag)
                self.skip += 1
            return
        if not self.layout:
            self.attr_units.append((start, raw))
        if tag in SKIP:
            self.close_run(start)
            self.skip += 1
            self.skip_tag.append(tag)
            return
        is_layout = attrs_d.get("id") == "site-nav" or "footer-links" in (attrs_d.get("class") or "").split()
        if tag in BLOCK:
            self.close_run(start)
            path = (self.stack[-1][3] + "/" if self.stack else "") + tag
            self.stack.append([tag, None, False, path])
            if is_layout:
                self.layout += 1
                self.layout_tag.append(len(self.stack))
        elif tag not in VOID and self.stack and self.stack[-1][1] is None:
            # Отрезок внутри блока начинается с тега: <code>, <a>, <strong>...
            self.stack[-1][1] = start

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        end = self.pos()
        if self.tasks:
            return
        if self.skip:
            if self.skip_tag and self.skip_tag[-1] == tag:
                self.skip_tag.pop()
                self.skip -= 1
            return
        if tag in BLOCK:
            # Закрываем всё до этого блока (браузеры прощают незакрытые теги, мы тоже)
            while self.stack:
                self.close_run(end)
                top = self.stack.pop()
                if self.layout and self.layout_tag and self.layout_tag[-1] == len(self.stack) + 1:
                    self.layout_tag.pop()
                    self.layout -= 1
                if top[0] == tag:
                    break

    def handle_data(self, data):
        if self.skip or self.tasks or not self.stack:
            return
        top = self.stack[-1]
        if top[1] is None:
            if not data.strip():
                return
            top[1] = self.pos()
        if CYRILLIC.search(data) or (self.any_text and data.strip()):
            top[2] = True

    def handle_entityref(self, name):
        self.handle_data("&" + name + ";")

    def handle_charref(self, name):
        self.handle_data("&#" + name + ";")

    def handle_comment(self, data):
        if "tasks:start" in data:
            self.close_run(self.pos())
            self.tasks = True
        elif "tasks:end" in data:
            self.tasks = False


def parse(source, any_text=False):
    parser = Units(source, any_text)
    parser.feed(source)
    parser.close()
    units = []
    for start, end, path in parser.text_units:
        raw = source[start:end]
        lead = len(raw) - len(raw.lstrip())
        trail = len(raw) - len(raw.rstrip())
        units.append(("text", start + lead, end - trail, raw.strip(), path))
    for start, raw in parser.attr_units:
        tag = re.match(r"<([a-zA-Z0-9]+)", raw).group(1).lower()
        for match in re.finditer(r'\s([a-zA-Z:-]+)="([^"]*)"', raw):
            name, value = match.group(1).lower(), html.unescape(match.group(2))
            if not CYRILLIC.search(value) and not (any_text and value.strip()):
                continue
            is_meta = tag == "meta" and name == "content" and any(f' {k}="{v}"' in raw for k, v in META)
            if name in ATTRS or is_meta:
                units.append(("attr", start + match.start(2), start + match.end(2), value, tag + "@" + name))
    units.sort(key=lambda unit: unit[1])
    return units


def load(lang):
    path = MEMORY / f"{lang}.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return {norm(k): norm(v) if "<time" in v else v for k, v in data.items()}


def save(lang, memory):
    MEMORY.mkdir(parents=True, exist_ok=True)
    data = dict(sorted(memory.items()))
    (MEMORY / f"{lang}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")


def tags_of(fragment):
    return sorted(re.findall(r"<[^>]+>", fragment))


def localize_links(page):
    """Ссылки русской страницы с точки зрения папки kk/ или en/; ссылки на страницы — на русские (hreflang)."""
    def fix(match):
        tag = match.group(0)
        name = re.match(r"<([a-zA-Z0-9]+)", tag).group(1).lower()

        def attr(m):
            key, value = m.group(1), m.group(2)
            if value == "" or re.match(r"(#|[a-z]+:|//|/)", value):
                return m.group(0)
            return f' {key}="../{value}"'

        new = re.sub(r'\s(href|src|action)="([^"]*)"', attr, tag)
        if name == "a" and re.search(r'\shref="\.\./[^"#]+\.html(#[^"]*)?"', new) and "hreflang=" not in new:
            new = new[:-1] + ' hreflang="ru">'
        return new

    return re.sub(r"<(?:a|img|link|script|source|form|iframe)\b[^>]*>", fix, page)


def build(lang, slug, memory=None, write=True):
    memory = load(lang) if memory is None else memory
    source = (ROOT / slug).read_text(encoding="utf-8")
    missing = []
    out = []
    last = 0
    units = parse(source)
    texts = [(u[1], u[2]) for u in units if u[0] == "text"]

    def inner_attrs(fragment):
        # Атрибут тега внутри переводимого фрагмента (placeholder у <input> в <label>) переводится из памяти тут же
        def fix(m):
            name, value = m.group(1), html.unescape(m.group(2))
            if name.lower() not in ATTRS or not CYRILLIC.search(value):
                return m.group(0)
            translated = memory.get(norm(value))
            if translated is None:
                missing.append(norm(value))
                return m.group(0)
            return f' {name}="{html.escape(translated, quote=True)}"'
        return re.sub(r"<[a-zA-Z][^>]*>", lambda t: re.sub(r'\s([a-zA-Z:-]+)="([^"]*)"', fix, t.group(0)), fragment)

    for kind, start, end, text, _ in units:
        key = norm(html.unescape(text)) if kind == "attr" else norm(text)
        if kind == "attr" and any(s <= start < e for s, e in texts):
            # Переведётся вместе с фрагментом, в который входит; в список на перевод попадает сам
            if key not in memory and key not in missing:
                missing.append(key)
            continue
        value = memory.get(key)
        if value is None:
            missing.append(key)
            continue
        if kind == "attr":
            value = html.escape(value, quote=True)
        else:
            dates = iter(TIME.findall(text))
            value = inner_attrs(re.sub(r"<time>", lambda m: next(dates), value))
        out.append(source[last:start])
        out.append(value)
        last = end
    out.append(source[last:])
    if missing:
        return None, missing
    page = "".join(out)
    page = page.replace('<html lang="ru">', f'<html lang="{lang}">', 1)
    page = page.replace("<!doctype html>", "<!doctype html>\n" + MARK.format(src=slug, lang=lang), 1)
    page = localize_links(page)
    page = re.sub(r'(<link rel="canonical" href=")' + re.escape(SITE), lambda m: f"{m.group(1)}{SITE}{lang}/", page, count=1)
    page = re.sub(r'(<meta property="og:url" content=")' + re.escape(SITE), lambda m: f"{m.group(1)}{SITE}{lang}/", page, count=1)
    page = page.replace('<meta property="og:locale" content="ru_RU">', f'<meta property="og:locale" content="{LOCALE[lang]}">', 1)
    page = page.replace(PRELOAD_RU.replace('href="', 'href="../'), PRELOAD[lang], 1)
    if "<!-- tasks:start -->" in page:
        # Задачи на языке страницы собирает build_practice.py (тексты из tools/i18n/practice.json)
        sys.path.insert(0, str(ROOT / "tools"))
        import build_practice
        page = re.sub(r"<!-- tasks:start -->.*?<!-- tasks:end -->",
                      lambda m: "<!-- tasks:start -->\n" + build_practice.build(lang) + "\n<!-- tasks:end -->", page, flags=re.S)
    if "assets/i18n.js" not in page:
        page = page.replace('  <script src="../script.js"></script>', '  <script src="../assets/i18n.js"></script>\n  <script src="../script.js"></script>', 1)
    if write:
        (ROOT / lang / slug).write_text(page, encoding="utf-8", newline="\n")
    return page, []


def todo(lang, slugs):
    memory = load(lang)
    seen = []
    for slug in slugs:
        _, missing = build(lang, slug, memory, write=False)
        for key in missing:
            if key not in seen:
                seen.append(key)
    items = {str(i): key for i, key in enumerate(seen, 1)}
    MEMORY.mkdir(parents=True, exist_ok=True)
    (MEMORY / f"todo-{lang}.json").write_text(json.dumps(items, ensure_ascii=False, indent=0) + "\n", encoding="utf-8", newline="\n")
    return items


def add(lang, path):
    memory = load(lang)
    items = json.loads((MEMORY / f"todo-{lang}.json").read_text(encoding="utf-8"))
    given = json.loads(Path(path).read_text(encoding="utf-8"))
    problems = []
    for number, value in given.items():
        key = items[str(number)]
        if tags_of(key) != tags_of(value):
            problems.append(f"{number}: разметка перевода не совпадает с оригиналом\n  ru: {key}\n  {lang}: {value}")
            continue
        memory[key] = value
    save(lang, memory)
    for problem in problems:
        print(problem)
    print(f"Добавлено: {len(given) - len(problems)}, с ошибками: {len(problems)}")
    return 1 if problems else 0


def seed():
    """Пары «русский — перевод» из страниц, которые уже переведены вручную (одинаковая структура)."""
    for lang in ("kk", "en"):
        memory = load(lang)
        added = 0
        for path in sorted((ROOT / lang).glob("*.html")):
            text = path.read_text(encoding="utf-8")
            if "tools/translate.py" in text:
                continue
            ru = parse((ROOT / path.name).read_text(encoding="utf-8"), any_text=True)
            tr = parse(text, any_text=True)
            # Пары по одинаковой структуре: лишние блоки в переводе (например, плашка «сайт переводится») пропускаются
            matcher = difflib.SequenceMatcher(None, [u[4] for u in ru], [u[4] for u in tr], autojunk=False)
            pairs = [(ru[block.a + k], tr[block.b + k]) for block in matcher.get_matching_blocks() for k in range(block.size)]
            for a, b in pairs:
                if not CYRILLIC.search(a[3]):
                    continue
                key = norm(html.unescape(a[3])) if a[0] == "attr" else norm(a[3])
                value = norm(html.unescape(b[3])) if b[0] == "attr" else norm(b[3])
                if b[0] == "text":
                    value = re.sub(r'(href="[^"]*")\s+hreflang="ru"', r"\1", value)
                    value = value.replace('href="../', 'href="')
                if key not in memory and value != key and tags_of(key) == tags_of(value):
                    memory[key] = value
                    added += 1
        save(lang, memory)
        print(f"{lang}: добавлено из готовых страниц {added}, всего в памяти {len(memory)}")


def generated(lang):
    return sorted(p.name for p in (ROOT / lang).glob("*.html") if "tools/translate.py" in p.read_text(encoding="utf-8"))


def check():
    """Переводы, собранные этим инструментом, не отстали от русских страниц."""
    sys.path.insert(0, str(ROOT / "tools"))
    import layout  # шапку и подвал собирает layout.py, сравниваем после него
    stale = []
    for lang in ("kk", "en"):
        memory = load(lang)
        for slug in generated(lang):
            page, missing = build(lang, slug, memory, write=False)
            if missing:
                stale.append(f"{lang}/{slug}: нет перевода для {len(missing)} фрагментов")
                continue
            current = (ROOT / lang / slug).read_text(encoding="utf-8")
            tmp = ROOT / lang / slug
            tmp.write_text(page, encoding="utf-8", newline="\n")
            try:
                _, rebuilt = layout.apply(tmp)
            finally:
                tmp.write_text(current, encoding="utf-8", newline="\n")
            if rebuilt != current:
                stale.append(f"{lang}/{slug}: устарел, запустите python tools/translate.py build {lang} {slug} и tools/layout.py")
    for line in stale:
        print(line)
    print(f"Переводов проверено: {sum(len(generated(l)) for l in ('kk', 'en'))}, устарело: {len(stale)}")
    return 1 if stale else 0


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 0
    command = args[0]
    if command == "seed":
        seed()
        return 0
    if command == "missing":
        items = todo(args[1], args[2:])
        print(f"Не переведено: {len(items)} -> tools/i18n/todo-{args[1]}.json")
        for number, key in items.items():
            print(f"{number}\t{key}")
        return 0
    if command == "add":
        return add(args[1], args[2])
    if command == "build":
        lang = args[1]
        for slug in args[2:]:
            _, missing = build(lang, slug)
            if missing:
                print(f"{lang}/{slug}: нет перевода для {len(missing)} фрагментов (python tools/translate.py missing {lang} {slug})")
                return 1
            print(f"{lang}/{slug}: собрано")
        return 0
    if command == "check":
        return check()
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
