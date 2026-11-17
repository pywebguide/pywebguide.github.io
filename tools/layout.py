"""Общая шапка и подвал для всех страниц на трёх языках.

Меню, выбор языка, ссылки подвала, hreflang и дата «Обновлено» описаны здесь один раз
и вписываются в каждую страницу. Здесь же <head> для поисковиков и мессенджеров (title, description,
canonical, Open Graph, коды подтверждения — из tools/seo.json), JSON-LD, sitemap.xml и llms.txt. Запуск после любой правки меню или нового перевода:

    python tools/layout.py            # переписать страницы
    python tools/layout.py --check    # только проверить, что страницы совпадают с описанием (для CI)

Переведённая страница — это файл с тем же именем в kk/ или en/. Если перевода нет,
ссылка в меню kk/ и en/ ведёт на русскую страницу и помечена «(RU)», а кнопка языка
на русской странице оставляет ученика на месте и показывает подсказку (script.js).
"""
import hashlib
import html
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://pywebguide.github.io/"
LANGS = ("ru", "kk", "en")
# Title, description, надпись на картинке превью, тип разметки schema.org и коды подтверждения в поисковиках
SEO = json.loads((ROOT / "tools" / "seo.json").read_text(encoding="utf-8"))
# Файлы подтверждения прав в Google и Яндексе (google<код>.html, yandex_<код>.html) — не страницы сайта:
# их не трогают меню, карта сайта, поиск и проверки, а содержимое должно остаться ровно таким, каким его выдал поисковик
SERVICE = re.compile(r"^(google[0-9a-f]+|yandex_[0-9a-f]+)\.html$")


def is_service(path):
    return bool(SERVICE.match(Path(path).name))

# Статистика GoatCounter без cookies (описана в privacy.html).
# TODO(автор): проверьте код счётчика — адрес вида https://<код>.goatcounter.com.
# Пустая строка убирает счётчик со всех страниц. После правки: python tools/layout.py
GOATCOUNTER = "pywebguide"
GOATCOUNTER_SRI = "sha384-nRw6qfbWyJha9LhsOtSb2YJDyZdKvvCFh0fJYlkquSFjUxp9FVNugbfy8q1jdxI+"

# slug: (ru, kk, en)
NAMES = {
    "index.html": ("Главная", "Басты бет", "Home"),
    "start.html": ("Python с нуля", "Python нөлден", "Python from scratch"),
    "html-css.html": ("HTML и CSS", "HTML және CSS", "HTML and CSS"),
    "setup.html": ("Подготовка компьютера", "Компьютерді дайындау", "Setting up your computer"),
    "glossary.html": ("Словарь", "Сөздік", "Glossary"),
    "playground.html": ("Песочница", "Құмсалғыш", "Sandbox"),
    "course.html": ("Весь курс", "Бүкіл курс", "Full course"),
    "about.html": ("О Python", "Python туралы", "About Python"),
    "frameworks.html": ("Фреймворки", "Фреймворктер", "Frameworks"),
    "databases.html": ("Базы данных", "Дерекқорлар", "Databases"),
    "templates.html": ("Шаблоны и формы", "Үлгілер мен формалар", "Templates and forms"),
    "auth.html": ("Авторизация", "Авторизация", "Authentication"),
    "api.html": ("REST API", "REST API", "REST API"),
    "testing.html": ("Тесты", "Тесттер", "Testing"),
    "git.html": ("Git", "Git", "Git"),
    "project.html": ("Первый проект", "Алғашқы жоба", "First project"),
    "django-next.html": ("Django дальше", "Django: келесі қадам", "Django next steps"),
    "fastapi.html": ("API на FastAPI", "FastAPI-дағы API", "API with FastAPI"),
    "project2.html": ("Второй проект", "Екінші жоба", "Second project"),
    "deploy.html": ("Публикация", "Жариялау", "Deployment"),
    "practice.html": ("Задачи", "Есептер", "Exercises"),
    "cheatsheet.html": ("Шпаргалка", "Қысқаша анықтама", "Cheat sheet"),
    "exam.html": ("Финальный тест", "Қорытынды тест", "Final test"),
    "progress.html": ("Мой прогресс", "Менің прогресім", "My progress"),
    "contacts.html": ("Контакты", "Байланыс", "Contact"),
    "privacy.html": ("Политика конфиденциальности", "Құпиялылық саясаты", "Privacy policy"),
    "terms.html": ("Условия использования", "Пайдалану шарттары", "Terms of use"),
}

# Верхняя строка меню; у первого пункта короткая подпись
TOP = [
    ("start.html", ("С нуля", "Нөлден", "From scratch")),
    ("course.html", None),
    ("project.html", None),
    ("playground.html", None),
    ("glossary.html", None),
]

# Группы меню «Ещё» (третий элемент True) и колонки подвала
GROUPS = [
    (("Начать", "Бастау", "Start"), ["start.html", "html-css.html", "glossary.html", "playground.html"], False),
    (("Понять", "Түсіну", "Understand"), ["about.html", "frameworks.html", "databases.html", "templates.html", "auth.html", "api.html", "testing.html", "git.html"], True),
    (("Сделать", "Жасау", "Build"), ["setup.html", "project.html", "django-next.html", "fastapi.html", "project2.html", "deploy.html"], True),
    (("Практика", "Практика", "Practice"), ["practice.html", "cheatsheet.html", "exam.html"], True),
    (("Сайт", "Сайт", "Site"), ["course.html", "progress.html", "contacts.html"], True),
]

UI = {
    "nav": ("Основная навигация", "Негізгі навигация", "Main navigation"),
    "more": ("Ещё", "Тағы", "More"),
    "lang": ("Язык сайта", "Сайт тілі", "Site language"),
    "updated": ("Обновлено", "Жаңартылды", "Updated"),
}
LANG_LABEL = {"ru": "РУС", "kk": "ҚАЗ", "en": "ENG"}
RU_MARK = ' <span class="ru-mark">(RU)</span>'


def i(lang):
    return LANGS.index(lang)


def exists(lang, slug):
    if not (ROOT / slug).exists():
        return False
    return lang == "ru" or (ROOT / lang / slug).exists()


def href(from_lang, to_lang, slug):
    """Относительная ссылка со страницы языка from_lang на страницу slug языка to_lang."""
    if from_lang == to_lang:
        return slug
    prefix = "" if from_lang == "ru" else "../"
    return prefix + ("" if to_lang == "ru" else to_lang + "/") + slug


def link_to(lang, slug):
    """Ссылка из меню: на перевод, если он есть, иначе на русскую страницу с пометкой (RU)."""
    if exists(lang, slug):
        return href(lang, lang, slug), "", ""
    return href(lang, "ru", slug), ' hreflang="ru"', RU_MARK


def page_lang(path):
    rel = path.relative_to(ROOT).as_posix()
    return (rel.split("/")[0] if "/" in rel else "ru"), path.name


def nav_html(lang, slug):
    n = i(lang)
    out = [f'      <nav id="site-nav" class="site-nav" aria-label="{UI["nav"][n]}">', '        <ul class="nav-menu">']
    top_slugs = [s for s, _ in TOP]
    for s, short in TOP:
        url, attr, mark = link_to(lang, s)
        label = (short or NAMES[s])[n] + mark
        current = s == slug
        cls = "nav-link active" if current else "nav-link"
        cur = ' aria-current="page"' if current else ""
        out.append(f'          <li><a class="{cls}" href="{url}"{attr}{cur}>{label}</a></li>')
    in_more = slug not in top_slugs and any(slug in pages for _, pages, more in GROUPS if more)
    out.append('          <li class="nav-more"><details>')
    out.append(f'          <summary class="{"nav-link active" if in_more else "nav-link"}">{UI["more"][n]} <span class="caret" aria-hidden="true"></span></summary>')
    out.append('          <div class="nav-more-list">')
    for gi, (title, group, more) in enumerate(GROUPS):
        items = [p for p in group if (ROOT / p).exists() and p not in top_slugs]
        if not more or not items:
            continue
        gid = f"nav-group-{gi}"
        out.append(f'            <div class="nav-group"><p class="nav-group-title" id="{gid}">{title[n]}</p><ul aria-labelledby="{gid}">')
        for p in items:
            url, attr, mark = link_to(lang, p)
            cur = ' aria-current="page"' if p == slug else ""
            out.append(f'              <li><a href="{url}"{attr}{cur}>{NAMES[p][n]}{mark}</a></li>')
        out.append("            </ul></div>")
    out.append("          </div>")
    out.append("        </details></li>")
    out.append(f'          <li class="nav-lang" aria-label="{UI["lang"][n]}">')
    for other in LANGS:
        if other == lang:
            out.append(f'            <a href="{slug}" hreflang="{other}" lang="{other}" aria-current="true">{LANG_LABEL[other]}</a>')
        elif exists(other, slug) and exists(lang, slug):
            out.append(f'            <a href="{href(lang, other, slug)}" hreflang="{other}" lang="{other}">{LANG_LABEL[other]}</a>')
        else:
            # Перевода нет: без JavaScript ссылка ведёт на главную языка, со скриптом — подсказка на месте
            out.append(f'            <a href="{href(lang, other, "index.html")}" hreflang="{other}" lang="{other}" data-untranslated="{other}">{LANG_LABEL[other]}</a>')
    out.append("          </li>")
    out.append("        </ul>")
    out.append("      </nav>")
    return "\n".join(out)


def footer_links_html(lang):
    n = i(lang)
    cols = []
    for title, group, _ in GROUPS:
        lis = []
        for p in group:
            if not (ROOT / p).exists():
                continue
            url, attr, mark = link_to(lang, p)
            lis.append(f'<li><a href="{url}"{attr}>{NAMES[p][n]}{mark}</a></li>')
        cols.append(f'        <div><strong>{title[n]}</strong><ul>{"".join(lis)}</ul></div>')
    return '      <div class="footer-links">\n' + "\n".join(cols) + "\n      </div>"


def alternates_html(slug):
    langs = [l for l in LANGS if exists(l, slug)]
    if len(langs) < 2:
        return ""

    def url(l):
        return SITE + ("" if l == "ru" else l + "/") + ("" if slug == "index.html" else slug)

    lines = [f'  <link rel="alternate" hreflang="{l}" href="{url(l)}">' for l in langs]
    lines.append(f'  <link rel="alternate" hreflang="x-default" href="{url("ru")}">')
    return "\n".join(lines)


def relink_body(text, lang):
    """На страницах kk/ и en/ ссылки на русские страницы ведут на перевод, когда он появился."""
    if lang == "ru":
        return text

    def fix(m):
        tag = m.group(0)
        target = re.search(r'\shref="\.\./([a-z0-9]+\.html)(#[^"]*)?"', tag)
        if 'hreflang="ru"' not in tag or not target or not exists(lang, target.group(1)):
            return tag
        tag = tag.replace(target.group(0), f' href="{target.group(1)}{target.group(2) or ""}"', 1)
        return re.sub(r'\s+hreflang="ru"', "", tag, count=1)

    # Везде, кроме выбора языка: там ссылка «РУС» должна вести на русскую страницу
    parts = re.split(r'(<li class="nav-lang".*?</li>)', text, maxsplit=1, flags=re.S)
    return "".join(part if part.startswith('<li class="nav-lang"') else re.sub(r"<a\b[^>]*>", fix, part) for part in parts)


# --- Дата изменения страницы -------------------------------------------------------------------------------------
# Дата «Обновлено» в подвале, lastmod в sitemap.xml и dateModified в JSON-LD — день последнего коммита, который
# поменял содержимое страницы (то, что внутри <main>). Правки меню, подвала и <head> дату не сдвигают: иначе любая
# правка layout.py «обновляла» бы все страницы, а сама дата, вписанная в страницу, меняла бы дату следующего коммита.
# Если <main> изменён и ещё не закоммичен — сегодняшний день. Нужна вся история git (в CI: fetch-depth: 0).
MAIN = re.compile(r"<main\b[^>]*>(.*)</main>", re.S)
_DATES = {}


def main_hash(text):
    m = MAIN.search(text)
    return hashlib.sha1((m.group(1) if m else text).encode()).hexdigest()


def _git(*args, data=None):
    return subprocess.run(["git", *args], cwd=ROOT, input=data, capture_output=True, check=True).stdout


def _load_dates():
    rels = [p.relative_to(ROOT).as_posix() for p in pages()]
    try:
        if _git("rev-parse", "--is-shallow-repository").strip() == b"true":
            print("layout.py: история git неполная (shallow clone), даты страниц будут неверны: git fetch --unshallow", file=sys.stderr)
        log = _git("log", "--format=%x00%H %cs", "--name-only", "--", *rels).decode()
    except (OSError, subprocess.CalledProcessError):
        log = ""
    history = {}
    for entry in log.split("\0")[1:]:
        head, _, files = entry.partition("\n")
        sha, day = head.split()
        for rel in files.split():
            history.setdefault(rel, []).append((sha, day))
    wanted = [(rel, sha) for rel, versions in history.items() for sha, _ in versions]
    blobs = {}
    if wanted:
        out = _git("cat-file", "--batch", data="".join(f"{sha}:{rel}\n" for rel, sha in wanted).encode())
        pos = 0
        for key in wanted:
            end = out.index(b"\n", pos)
            header = out[pos:end].split()
            pos = end + 1
            if header[-1] == b"missing":
                continue
            size = int(header[2])
            blobs[key] = main_hash(out[pos:pos + size].decode("utf-8", "replace"))
            pos += size + 1
    today = date.today()
    for rel in rels:
        current = main_hash((ROOT / rel).read_text(encoding="utf-8"))
        versions = [(blobs.get((rel, sha)), day) for sha, day in history.get(rel, [])]
        if not versions or versions[0][0] != current:
            _DATES[rel] = today
            continue
        day = versions[0][1]
        for (newer, _), (older, older_day) in zip(versions, versions[1:]):
            if newer != older:
                break
            day = older_day
        _DATES[rel] = date.fromisoformat(day)


def updated(path):
    """Дата изменения содержимого страницы path (файл в корне, kk/ или en/)."""
    if not _DATES:
        _load_dates()
    return _DATES.get(Path(path).relative_to(ROOT).as_posix(), date.today())


# --- Поисковые системы: <head>, картинка превью, JSON-LD ----------------------------------------------------------
LOCALE = {"ru": "ru_RU", "kk": "kk_KZ", "en": "en_GB"}
LEVEL = {"ru": "Начальный", "kk": "Бастауыш", "en": "Beginner"}
RESOURCE = {
    "lesson": ("Урок", "Сабақ", "Lesson"),
    "project": ("Пошаговое руководство", "Қадамдық нұсқаулық", "Step-by-step guide"),
    "exercise": ("Упражнения", "Жаттығулар", "Exercises"),
    "quiz": ("Тест", "Тест", "Quiz"),
    "reference": ("Шпаргалка", "Анықтамалық", "Cheat sheet"),
    "glossary": ("Словарь", "Сөздік", "Glossary"),
    "tool": ("Интерактивная среда", "Интерактивті орта", "Interactive environment"),
}
SEO_HEAD = re.compile(r"  <title>.*?\n(?=  <meta name=\"theme-color\")", re.S)
JSON_LD = re.compile(r"\n  <script type=\"application/ld\+json\">.*?</script>", re.S)


def page_url(lang, slug):
    return SITE + ("" if lang == "ru" else lang + "/") + ("" if slug == "index.html" else slug)


def seo(lang, slug):
    return SEO["pages"][slug][lang]


def card_text(lang, slug):
    """Крупная надпись на картинке превью."""
    return seo(lang, slug).get("card") or NAMES[slug][i(lang)]


def og_image(lang, slug):
    """Путь картинки превью от корня сайта (рисует tools/build_og.py)."""
    return f"assets/og/{lang}/{slug[:-5]}.png"


def attr(value):
    return html.escape(value, quote=True)


def plain(fragment):
    """Текст фрагмента HTML без тегов, как его видит читатель."""
    # Строчные теги (code, a, strong) убираются без пробела, блочные (p, li, br) разделяют текст пробелом
    text = re.sub(r"</?(?:a|code|strong|em|b|i|kbd|span|abbr|time|small|mark|sub|sup)\b[^>]*>", "", fragment)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def head_html(lang, slug):
    data = seo(lang, slug)
    title, desc = data["title"], data["description"]
    image = SITE + og_image(lang, slug)
    alt = f"{card_text(lang, slug)} — PyWeb Guide"
    out = [f"  <title>{html.escape(title, quote=False)}</title>", f'  <meta name="description" content="{attr(desc)}">']
    if slug == "index.html":
        # Подтверждение прав в Google Search Console и Яндекс Вебмастере: коды в tools/seo.json, пустой — тега нет
        for name, key in (("google-site-verification", "google"), ("yandex-verification", "yandex")):
            if SEO["verification"].get(key):
                out.append(f'  <meta name="{name}" content="{attr(SEO["verification"][key])}">')
    if slug == "404.html":
        out.append('  <meta name="robots" content="noindex">')
    else:
        out.append(f'  <link rel="canonical" href="{page_url(lang, slug)}">')
        alt_links = alternates_html(slug)
        if alt_links:
            out.append(alt_links)
    out.append('  <meta property="og:type" content="website">')
    out.append(f'  <meta property="og:locale" content="{LOCALE[lang]}">')
    if slug != "404.html":
        out += [f'  <meta property="og:locale:alternate" content="{LOCALE[o]}">' for o in LANGS if o != lang and exists(o, slug)]
    out.append('  <meta property="og:site_name" content="PyWeb Guide">')
    # В превью мессенджеры показывают og:site_name отдельно, поэтому в og:title название сайта не повторяется
    out.append(f'  <meta property="og:title" content="{attr(title.split(" — PyWeb Guide")[0])}">')
    out.append(f'  <meta property="og:description" content="{attr(desc)}">')
    if slug != "404.html":
        out.append(f'  <meta property="og:url" content="{page_url(lang, slug)}">')
    out += [f'  <meta property="og:image" content="{image}">',
            '  <meta property="og:image:type" content="image/png">',
            '  <meta property="og:image:width" content="1200">',
            '  <meta property="og:image:height" content="630">',
            f'  <meta property="og:image:alt" content="{attr(alt)}">',
            '  <meta name="twitter:card" content="summary_large_image">',
            f'  <meta name="twitter:image" content="{image}">',
            f'  <meta name="twitter:image:alt" content="{attr(alt)}">']
    return "\n".join(out) + "\n"


def breadcrumbs(text, lang, slug):
    """Хлебные крошки, которые видны на странице (nav.breadcrumb): [(название, адрес)]."""
    m = re.search(r'<nav class="breadcrumb"[^>]*>(.*?)</nav>', text, re.S)
    if not m:
        return []
    base = page_url(lang, slug)
    items = []
    for tag in re.finditer(r'<a href="([^"]+)"[^>]*>(.*?)</a>|<span>(.*?)</span>', m.group(1), re.S):
        if tag.group(1):
            url = urljoin(base, tag.group(1))
            items.append((plain(tag.group(2)), url[:-len("index.html")] if url.endswith("/index.html") else url))
        else:
            items.append((plain(tag.group(3)), base))
    return items


def faq(text):
    """Вопросы и ответы из разделов «Частые вопросы» и «Частые ошибки» — только то, что видно на странице."""
    pairs = []
    for section in re.finditer(r'<section\b[^>]*(?:id="(?:errors|faq)"|aria-labelledby="faq-title")[^>]*>(.*?)</section>', text, re.S):
        body = section.group(1)
        for d in re.finditer(r"<details\b[^>]*>\s*<summary[^>]*>(.*?)</summary>(.*?)</details>", body, re.S):
            pairs.append((plain(d.group(1)), plain(d.group(2))))
        for d in re.finditer(r"<h3\b[^>]*>(.*?)</h3>\s*<p\b[^>]*>(.*?)</p>", body, re.S):
            pairs.append((plain(d.group(1)), plain(d.group(2))))
    return [(q, a) for q, a in pairs if q and a]


def course_parts(text, lang):
    """Уроки из программы на course.html (ol.course-list) в том порядке, в каком они показаны."""
    m = re.search(r'<ol class="course-list">(.*?)</ol>', text, re.S)
    parts = []
    for li in re.finditer(r'<a href="([^"]+)"[^>]*><strong>(.*?)</strong><span>(.*?)</span></a>', m.group(1) if m else "", re.S):
        parts.append({"@type": "LearningResource", "name": plain(li.group(2)), "description": plain(li.group(3)),
                      "url": urljoin(page_url(lang, "course.html"), li.group(1))})
    return parts


def json_ld(text, lang, slug):
    """Разметка schema.org для страницы: тип страницы, хлебные крошки и FAQ, собранные из её же текста."""
    kind = SEO["pages"][slug]["kind"]
    if kind == "notfound":
        return None
    data = seo(lang, slug)
    url = page_url(lang, slug)
    h1 = re.search(r"<h1\b[^>]*>(.*?)</h1>", text, re.S)
    name = plain(h1.group(1)) if h1 else data["title"].split(" — ")[0]
    author = {"@type": "Person", "name": SEO["author"][lang], "url": page_url(lang, "contacts.html")}
    website = {"@type": "WebSite", "name": "PyWeb Guide", "url": page_url(lang, "index.html")}
    when = updated(ROOT / ("" if lang == "ru" else lang) / slug).isoformat()
    time = SEO["pages"][slug].get("time")
    graph = []
    if kind == "website":
        graph.append({"@type": "WebSite", "@id": url + "#website", "name": "PyWeb Guide", "url": url, "inLanguage": lang,
                      "description": data["description"], "author": author})
    elif kind == "course":
        node = {"@type": "Course", "@id": url + "#course", "name": data["title"].split(" — ")[0], "description": data["description"],
                "url": url, "inLanguage": lang, "educationalLevel": LEVEL[lang], "isAccessibleForFree": True,
                "provider": author, "author": author, "dateModified": when, "image": SITE + og_image(lang, slug),
                "offers": {"@type": "Offer", "price": 0, "priceCurrency": "USD", "category": "Free"},
                "hasCourseInstance": {"@type": "CourseInstance", "courseMode": "Online", "courseWorkload": time},
                "hasPart": course_parts(text, lang)}
        graph.append(node)
    elif kind in RESOURCE:
        node = {"@type": "LearningResource", "@id": url + "#resource", "name": name, "description": data["description"],
                "url": url, "inLanguage": lang, "educationalLevel": LEVEL[lang],
                "learningResourceType": RESOURCE[kind][i(lang)]}
        if time:
            node["timeRequired"] = time
        node.update({"isAccessibleForFree": True, "dateModified": when, "image": SITE + og_image(lang, slug),
                     "isPartOf": website, "author": author})
        graph.append(node)
    else:
        graph.append({"@type": "ContactPage" if kind == "contact" else "WebPage", "@id": url + "#webpage", "name": name,
                      "description": data["description"], "url": url, "inLanguage": lang, "dateModified": when,
                      "isPartOf": website})
    crumbs = breadcrumbs(text, lang, slug)
    if crumbs:
        graph.append({"@type": "BreadcrumbList", "@id": url + "#breadcrumbs", "itemListElement": [
            {"@type": "ListItem", "position": n, "name": crumb, "item": link} for n, (crumb, link) in enumerate(crumbs, 1)]})
    questions = faq(text)
    if questions:
        graph.append({"@type": "FAQPage", "@id": url + "#faq", "url": url, "inLanguage": lang, "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in questions]})
    body = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=1).replace("</", "<\\/")
    return '  <script type="application/ld+json">\n' + "\n".join("  " + line for line in body.split("\n")) + "\n  </script>"


def apply(path, text=None):
    """Страница path с актуальной шапкой и подвалом. text — содержимое вместо файла (для проверок без записи)."""
    lang, slug = page_lang(path)
    if text is None:
        text = path.read_text(encoding="utf-8")
    new = re.sub(r'      <nav id="site-nav".*?\n      </nav>', lambda m: nav_html(lang, slug), text, count=1, flags=re.S)
    new = re.sub(r'      <div class="footer-links">.*?\n      </div>', lambda m: footer_links_html(lang), new, count=1, flags=re.S)
    day = updated(path)
    stamp = f'<time datetime="{day.isoformat()}">{day.strftime("%d.%m.%Y")}</time>'
    # «Жаңартылған күні» — подпись на страницах kk/, переведённых вручную
    new = re.sub("(" + "|".join((*UI["updated"], "Жаңартылған күні")) + r'): <time datetime="[^"]+">[^<]+</time>', lambda m: f"{m.group(1)}: {stamp}", new)
    new = relink_body(new, lang)
    # <head> для поисковых систем и мессенджеров: title, description, canonical, hreflang, Open Graph (tools/seo.json)
    if not SEO_HEAD.search(new):
        raise SystemExit(f"{path}: в <head> нет блока от <title> до <meta name=\"theme-color\">")
    new = SEO_HEAD.sub(lambda m: head_html(lang, slug), new, count=1)
    # JSON-LD собирается из текста страницы: хлебные крошки, FAQ и программа курса всегда совпадают с видимыми
    new = JSON_LD.sub("", new)
    ld = json_ld(new, lang, slug)
    if ld:
        new = new.replace("\n</head>", "\n" + ld + "\n</head>", 1)
    # Счётчик GoatCounter: один код на все страницы
    counter = (f'<script data-goatcounter="https://{GOATCOUNTER}.goatcounter.com/count" async src="https://gc.zgo.at/count.v4.js" '
               f'crossorigin="anonymous" integrity="{GOATCOUNTER_SRI}"></script>') if GOATCOUNTER else ""
    new = re.sub(r'  <script data-goatcounter="[^"]*"[^>]*></script>\n', lambda m: ("  " + counter + "\n") if counter else "", new)
    # Манифест PWA: сайт можно установить как приложение (sw.js регистрирует script.js)
    if 'rel="manifest"' not in new:
        prefix = "../" if lang != "ru" else ""
        new = re.sub(r'(\n  <link rel="apple-touch-icon" href="[^"]+">)', lambda m: m.group(1) + f'\n  <link rel="manifest" href="{prefix}manifest.webmanifest">', new, count=1)
    # Pagefind индексирует только содержимое <main>: меню и подвал в результаты не попадают
    if slug != "404.html":
        new = re.sub(r'<main id="content"(?![^>]*data-pagefind-body)', '<main id="content" data-pagefind-body', new, count=1)
    return text, new


def pages():
    return sorted(p for p in [*ROOT.glob("*.html"), *ROOT.glob("kk/*.html"), *ROOT.glob("en/*.html")] if not is_service(p))


def site_slugs():
    """Русские страницы сайта в порядке меню (без 404 и файлов подтверждения)."""
    order = list(NAMES)
    return sorted((p.name for p in ROOT.glob("*.html") if p.name != "404.html" and not is_service(p)),
                  key=lambda s: (order.index(s) if s in order else len(order), s))


def sitemap_xml():
    """Карта сайта: все страницы трёх языков, у переведённых — ссылки на другие языки (hreflang).
    lastmod — дата изменения содержимого страницы на этом языке (см. updated)."""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for lang in LANGS:
        for slug in site_slugs():
            if not exists(lang, slug):
                continue
            day = updated(ROOT / ("" if lang == "ru" else lang) / slug)
            lines.append(f"  <url><loc>{page_url(lang, slug)}</loc><lastmod>{day.isoformat()}</lastmod>")
            langs = [l for l in LANGS if exists(l, slug)]
            if len(langs) > 1:
                for other in langs:
                    lines.append(f'    <xhtml:link rel="alternate" hreflang="{other}" href="{page_url(other, slug)}"/>')
                lines.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{page_url("ru", slug)}"/>')
            lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


# llms.txt (https://llmstxt.org): краткое описание сайта для ИИ-поисковиков и ассистентов со ссылками на все разделы
LLMS_INTRO = """# PyWeb Guide

> Бесплатный учебный сайт на трёх языках (русский, казахский, английский) для тех, кто никогда не программировал: Python с нуля прямо в браузере, затем веб-разработка на Flask, Django и FastAPI — от первого приложения до публикации в интернете.

Для кого: школьники, студенты и взрослые без опыта программирования, которые хотят сделать свой первый сайт или веб-приложение на Python. Регистрация не нужна, прогресс хранится в браузере. Код примеров запускается на странице (Pyodide) и проверен на Python 3.13, Flask 3.1, Django 6.1 и FastAPI 0.163; у первого проекта есть готовый код после каждого шага, у «Django дальше» и API на FastAPI — итоговый код архивом. Автор курса — Жангужин Е. Е.

Қазақша: Python-ды нөлден үйренуге және Flask, Django, FastAPI-да алғашқы сайт жасауға арналған тегін курс. Барлық беттер /kk/ бөлімінде.

In English: a free course for complete beginners — Python from scratch in the browser, then a first web app with Flask, Django and FastAPI. All pages are under /en/.
"""
LLMS_LANG = {"ru": "русский", "kk": "қазақша", "en": "English"}
# Служебные страницы — в разделе Optional: их можно пропустить, если контекст ограничен
LLMS_OPTIONAL = ("progress.html", "contacts.html", "privacy.html", "terms.html")


def llms_txt():
    out = [LLMS_INTRO]
    for lang in LANGS:
        n = i(lang)
        home = seo(lang, "index.html")
        out.append(f"## {NAMES['index.html'][n]} ({LLMS_LANG[lang]})\n\n- [{home['title']}]({page_url(lang, 'index.html')}): {home['description']}\n")
        for title, group, _ in GROUPS:
            items = [p for p in group if exists(lang, p) and p not in LLMS_OPTIONAL]
            if not items:
                continue
            lines = [f"- [{NAMES[p][n]}]({page_url(lang, p)}): {seo(lang, p)['description']}" for p in items]
            out.append(f"## {title[n]} ({LLMS_LANG[lang]})\n\n" + "\n".join(lines) + "\n")
    lines = [f"- [{NAMES[p][i(lang)]} ({LLMS_LANG[lang]})]({page_url(lang, p)}): {seo(lang, p)['description']}"
             for p in LLMS_OPTIONAL for lang in LANGS if exists(lang, p)]
    out.append("## Optional\n\n" + "\n".join(lines) + "\n")
    return "\n".join(out)


GENERATED = {"sitemap.xml": sitemap_xml, "llms.txt": llms_txt}


def main():
    check = "--check" in sys.argv
    changed = []
    for path in pages():
        old, new = apply(path)
        if old != new:
            changed.append(path.relative_to(ROOT).as_posix())
            if not check:
                path.write_text(new, encoding="utf-8", newline="\n")
    for name, make in GENERATED.items():
        target = ROOT / name
        text = make()
        if not target.exists() or target.read_text(encoding="utf-8").replace("\r\n", "\n") != text:
            changed.append(name)
            if not check:
                target.write_text(text, encoding="utf-8", newline="\n")
    if check and changed:
        print("Шапка, подвал, sitemap.xml или llms.txt не совпадают с tools/layout.py и tools/seo.json. Запустите python tools/layout.py:")
        print("\n".join("  " + c for c in changed))
        sys.exit(1)
    print(("Нужно обновить: " if check else "Обновлено файлов: ") + str(len(changed)))


if __name__ == "__main__":
    main()
