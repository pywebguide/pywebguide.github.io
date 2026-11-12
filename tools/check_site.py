"""Проверка сайта без сети: ссылки, якоря, заголовки, описания, карта сайта. Код выхода 1 при ошибках."""
import posixpath
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.duplicates = []
        self.links = []
        self.h1 = 0
        self.has_description = False
        self.title = ""
        self.in_title = False
        self.h2_count = 0
        self.in_main = False
        self.lang = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            if attrs["id"] in self.ids:
                self.duplicates.append(attrs["id"])
            self.ids.add(attrs["id"])
        if tag == "html":
            self.lang = attrs.get("lang", "")
        if tag == "main":
            self.in_main = True
        if tag == "h1":
            self.h1 += 1
        if tag == "h2" and self.in_main:
            self.h2_count += 1
            self.ids.add(f"sec-{self.h2_count}")
        if tag == "title":
            self.in_title = True
        if tag == "meta" and attrs.get("name") == "description" and attrs.get("content"):
            self.has_description = True
        for name in ("href", "src"):
            value = attrs.get(name)
            if not value:
                continue
            # У <link> проверяем только файлы сайта: стили и иконки (не canonical, alternate, preload)
            if tag == "link" and not (name == "href" and attrs.get("rel") in ("stylesheet", "icon", "apple-touch-icon")):
                continue
            self.links.append(value)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "main":
            self.in_main = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


def resolve(name, path):
    """Путь ссылки относительно корня сайта. Переводы лежат в kk/ и en/, у 404.html база — корень
    (у en/404.html и kk/404.html — их папка, как у остальных переводов)."""
    if path.startswith("/"):
        path = path.lstrip("/")
        # Адрес папки (/en/) — это её index.html
        return path + "index.html" if path == "" or path.endswith("/") else path
    folder = "" if name == "404.html" else posixpath.dirname(name)
    target = posixpath.normpath(posixpath.join(folder, path))
    return "index.html" if target == "." else target


def main():
    pages = {}
    for path in sorted([*ROOT.glob("*.html"), *ROOT.glob("kk/*.html"), *ROOT.glob("en/*.html")]):
        page = Page()
        page.feed(path.read_text(encoding="utf-8"))
        pages[path.relative_to(ROOT).as_posix()] = page

    errors = []
    for name, page in pages.items():
        # Язык страницы совпадает с папкой: kk/ — казахский, en/ — английский, корень — русский
        expected_lang = name.split("/")[0] if "/" in name else "ru"
        if page.lang != expected_lang:
            errors.append(f"{name}: <html lang=\"{page.lang}\">, а нужен {expected_lang}")
        if page.h1 != 1:
            errors.append(f"{name}: заголовков h1 — {page.h1}, нужен один")
        for duplicate in page.duplicates:
            errors.append(f"{name}: повторяется id {duplicate}")
        if not page.title.strip():
            errors.append(f"{name}: нет title")
        if not page.has_description and posixpath.basename(name) != "404.html":
            errors.append(f"{name}: нет description")
        for link in page.links:
            parts = urlsplit(link)
            if parts.scheme or link.startswith(("//", "mailto:", "tel:", "data:")):
                continue
            target = resolve(name, unquote(parts.path)) if parts.path else name
            if target.startswith("..") or not (ROOT / target).is_file():
                errors.append(f"{name}: нет файла {link}")
            elif parts.fragment and target in pages and parts.fragment not in pages[target].ids:
                errors.append(f"{name}: нет якоря {link}")

    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    # «https://…/kk/» в карте сайта — это страница kk/index.html
    listed = {(urlsplit(url).path.lstrip("/") + ("index.html" if url.endswith("/") else "")) for url in re.findall(r"<loc>(.*?)</loc>", sitemap)}
    for name in pages:
        if posixpath.basename(name) != "404.html" and name not in listed:
            errors.append(f"sitemap.xml: нет страницы {name}")

    for error in errors:
        print("ОШИБКА", error)
    print(f"Страниц: {len(pages)}, ошибок: {len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
