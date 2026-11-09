"""Общая шапка и подвал для всех страниц на трёх языках.

Меню, выбор языка, ссылки подвала, hreflang и дата «Обновлено» описаны здесь один раз
и вписываются в каждую страницу. Запуск после любой правки меню или нового перевода:

    python tools/layout.py            # переписать страницы
    python tools/layout.py --check    # только проверить, что страницы совпадают с описанием (для CI)

Переведённая страница — это файл с тем же именем в kk/ или en/. Если перевода нет,
ссылка в меню kk/ и en/ ведёт на русскую страницу и помечена «(RU)», а кнопка языка
на русской странице оставляет ученика на месте и показывает подсказку (script.js).
"""
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://pywebguide.github.io/"
LANGS = ("ru", "kk", "en")
UPDATED = date(2026, 11, 9)

# slug: (ru, kk, en)
NAMES = {
    "index.html": ("Главная", "Басты бет", "Home"),
    "start.html": ("Python с нуля", "Python нөлден", "Python from scratch"),
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
    (("Начать", "Бастау", "Start"), ["start.html", "glossary.html", "playground.html"], False),
    (("Понять", "Түсіну", "Understand"), ["about.html", "frameworks.html", "databases.html", "templates.html", "auth.html", "api.html", "testing.html", "git.html"], True),
    (("Сделать", "Жасау", "Build"), ["project.html", "project2.html", "deploy.html"], True),
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
        target = m.group(1)
        return f'href="{target}"' if exists(lang, target.split("#")[0]) else m.group(0)

    def main(m):
        return re.sub(r'href="\.\./([a-z0-9]+\.html(?:#[^"]*)?)"\s+hreflang="ru"', fix, m.group(0))

    # Только внутри <main>: в шапке ссылка «РУС» должна вести на русскую страницу
    return re.sub(r"<main.*?</main>", main, text, count=1, flags=re.S)


def apply(path):
    lang, slug = page_lang(path)
    text = path.read_text(encoding="utf-8")
    new = re.sub(r'      <nav id="site-nav".*?\n      </nav>', lambda m: nav_html(lang, slug), text, count=1, flags=re.S)
    new = re.sub(r'      <div class="footer-links">.*?\n      </div>', lambda m: footer_links_html(lang), new, count=1, flags=re.S)
    # hreflang в <head>: старые строки убираем, новые ставим сразу после canonical
    new = re.sub(r'\n  <link rel="alternate" hreflang="[^"]+" href="[^"]+">', "", new)
    alt = alternates_html(slug) if slug != "404.html" else ""
    if alt:
        new = re.sub(r'(  <link rel="canonical" href="[^"]+">)', lambda m: m.group(1) + "\n" + alt, new, count=1)
    stamp = f'<time datetime="{UPDATED.isoformat()}">{UPDATED.strftime("%d.%m.%Y")}</time>'
    new = re.sub("(" + "|".join(UI["updated"]) + r'): <time datetime="[^"]+">[^<]+</time>', lambda m: f"{m.group(1)}: {stamp}", new)
    new = relink_body(new, lang)
    # Манифест PWA: сайт можно установить как приложение (sw.js регистрирует script.js)
    if 'rel="manifest"' not in new:
        prefix = "../" if lang != "ru" else ""
        new = re.sub(r'(\n  <link rel="apple-touch-icon" href="[^"]+">)', lambda m: m.group(1) + f'\n  <link rel="manifest" href="{prefix}manifest.webmanifest">', new, count=1)
    # Pagefind индексирует только содержимое <main>: меню и подвал в результаты не попадают
    if slug != "404.html":
        new = re.sub(r'<main id="content"(?![^>]*data-pagefind-body)', '<main id="content" data-pagefind-body', new, count=1)
    return text, new


def pages():
    return sorted([*ROOT.glob("*.html"), *ROOT.glob("kk/*.html"), *ROOT.glob("en/*.html")])


def main():
    check = "--check" in sys.argv
    changed = []
    for path in pages():
        old, new = apply(path)
        if old != new:
            changed.append(path.relative_to(ROOT).as_posix())
            if not check:
                path.write_text(new, encoding="utf-8", newline="\n")
    if check and changed:
        print("Шапка или подвал не совпадают с tools/layout.py. Запустите python tools/layout.py:")
        print("\n".join("  " + c for c in changed))
        sys.exit(1)
    print(("Нужно обновить: " if check else "Обновлено страниц: ") + str(len(changed)))


if __name__ == "__main__":
    main()
