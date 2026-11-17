"""Тесты инструментов сборки: python tools/test_tools.py"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_practice  # noqa: E402
import build_sw  # noqa: E402
import check_site  # noqa: E402
import codeblocks  # noqa: E402
import layout  # noqa: E402
import sync_examples  # noqa: E402
import translate  # noqa: E402


class CodeBlocks(unittest.TestCase):
    def parse(self, html):
        parser = codeblocks.Blocks()
        parser.feed(html)
        return parser.blocks

    def test_label_code_and_run_flag(self):
        blocks = self.parse('<div class="code-block" data-run><div class="code-head"><span>app.py</span>'
                            '<button>Копировать</button></div><pre><code>print(&quot;a&quot;)\nx = 1 &lt; 2</code></pre></div>'
                            '<div class="code-block"><span>Терминал</span><pre><code>pip install flask</code></pre></div>')
        self.assertEqual([(b["label"], b["run"]) for b in blocks], [("app.py", True), ("Терминал", False)])
        self.assertEqual(blocks[0]["code"], 'print("a")\nx = 1 < 2')

    def test_nested_div_does_not_close_block_early(self):
        blocks = self.parse('<div class="code-block"><div><span>a.py</span></div><pre><code>x</code></pre></div><p><code>y</code></p>')
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["code"], "x")


class SiteLinks(unittest.TestCase):
    def test_resolve(self):
        self.assertEqual(check_site.resolve("about.html", "styles.css"), "styles.css")
        self.assertEqual(check_site.resolve("kk/about.html", "../styles.css"), "styles.css")
        self.assertEqual(check_site.resolve("kk/about.html", "start.html"), "kk/start.html")
        self.assertEqual(check_site.resolve("en/index.html", "/"), "index.html")
        self.assertEqual(check_site.resolve("404.html", "index.html"), "index.html")
        self.assertTrue(check_site.resolve("about.html", "../secret.txt").startswith(".."))


class Layout(unittest.TestCase):
    def test_href_between_languages(self):
        self.assertEqual(layout.href("ru", "ru", "a.html"), "a.html")
        self.assertEqual(layout.href("ru", "kk", "a.html"), "kk/a.html")
        self.assertEqual(layout.href("kk", "ru", "a.html"), "../a.html")
        self.assertEqual(layout.href("kk", "en", "a.html"), "../en/a.html")

    def test_every_page_has_a_name_in_three_languages(self):
        for slug in (p.name for p in ROOT.glob("*.html") if p.name != "404.html" and not layout.is_service(p)):
            self.assertIn(slug, layout.NAMES)
            self.assertEqual(len(layout.NAMES[slug]), 3)

    def test_apply_is_stable(self):
        path = ROOT / "about.html"
        _, once = layout.apply(path)
        _, twice = layout.apply(path, once)
        self.assertEqual(once, twice)

    def test_verification_tags_only_when_code_is_set(self):
        saved = dict(layout.SEO["verification"])
        try:
            layout.SEO["verification"].update(google="", yandex="")
            self.assertNotIn("verification", layout.head_html("ru", "index.html"))
            layout.SEO["verification"].update(google="abc123", yandex="")
            head = layout.head_html("ru", "index.html")
            self.assertIn('<meta name="google-site-verification" content="abc123">', head)
            self.assertNotIn("yandex-verification", head)
            self.assertNotIn("verification", layout.head_html("ru", "about.html"))
        finally:
            layout.SEO["verification"].update(saved)

    def test_404_is_noindex_without_canonical(self):
        head = layout.head_html("en", "404.html")
        self.assertIn('<meta name="robots" content="noindex">', head)
        self.assertNotIn("canonical", head)
        self.assertIn("assets/og/en/404.png", head)

    def test_faq_takes_visible_questions_and_answers(self):
        page = ('<section class="section faq" id="errors"><details><summary>Ошибка <code>x</code></summary>'
                '<p>Выполните <code>py -m venv .venv</code>, потом <a href="a.html">шаг 2</a>.</p></details></section>'
                '<section class="section faq" aria-label="Словарь"><details><summary>Термин</summary><p>Не FAQ</p></details></section>')
        self.assertEqual(layout.faq(page), [("Ошибка x", "Выполните py -m venv .venv, потом шаг 2.")])

    def test_breadcrumbs_follow_visible_trail(self):
        page = '<nav class="breadcrumb" aria-label="x"><a href="index.html">Басты бет</a><span aria-hidden="true">/</span><span>Git</span></nav>'
        self.assertEqual(layout.breadcrumbs(page, "kk", "git.html"),
                         [("Басты бет", "https://pywebguide.github.io/kk/"), ("Git", "https://pywebguide.github.io/kk/git.html")])

    def test_service_files_are_not_pages(self):
        self.assertTrue(layout.is_service("google782fb83ab40c9a14.html"))
        self.assertTrue(layout.is_service("yandex_0123abcd.html"))
        self.assertFalse(layout.is_service("glossary.html"))
        self.assertFalse(any(layout.is_service(p) for p in layout.pages()))


class Translate(unittest.TestCase):
    def test_norm_ignores_spaces_and_dates(self):
        a = translate.norm('Обновлено:\n   <time datetime="2026-11-09">09.11.2026</time>')
        b = translate.norm('Обновлено: <time datetime="2026-11-10">10.11.2026</time>')
        self.assertEqual(a, b)

    def test_parse_finds_text_and_attributes_but_skips_code(self):
        source = ('<html lang="ru"><body><main><p>Привет, <b>мир</b>!</p><pre><code>print("код не переводится")</code></pre>'
                  '<img src="a.png" alt="Схема запроса"><p>No Cyrillic here</p></main></body></html>')
        units = translate.parse(source)
        found = [(kind, text) for kind, _, _, text, _ in units]
        self.assertIn(("text", "Привет, <b>мир</b>!"), found)
        self.assertIn(("attr", "Схема запроса"), found)
        self.assertFalse(any("код не переводится" in text or "No Cyrillic" in text for _, text in found))
        for _, start, end, text, _ in units:
            self.assertEqual(source[start:end], text)

    def test_tags_of_compares_markup_only(self):
        self.assertEqual(translate.tags_of("Напишите <code>x</code> и <a href=\"a.html\">сюда</a>"),
                         translate.tags_of("<a href=\"a.html\">Here</a>: write <code>x</code>"))
        self.assertNotEqual(translate.tags_of("<code>x</code>"), translate.tags_of("<b>x</b>"))

    def test_localize_links(self):
        page = translate.localize_links('<a href="about.html#top">a</a><img src="assets/x.png"><a href="https://example.com">b</a><a href="#id">c</a>')
        self.assertIn('<a href="../about.html#top" hreflang="ru">', page)
        self.assertIn('<img src="../assets/x.png">', page)
        self.assertIn('<a href="https://example.com">', page)
        self.assertIn('<a href="#id">', page)

    def test_memory_keeps_markup_of_the_original(self):
        for lang in ("kk", "en"):
            for key, value in translate.load(lang).items():
                self.assertEqual(translate.tags_of(key), translate.tags_of(value), f"{lang}: {key[:60]}")


class Practice(unittest.TestCase):
    def test_sections_and_tasks_match(self):
        listed = [slug for section in build_practice.SECTIONS for slug in section["tasks"]]
        self.assertEqual(len(listed), len(set(listed)), "задача стоит в двух разделах")
        self.assertEqual(set(listed), set(build_practice.TASKS))

    def test_every_task_is_translated(self):
        data = json.loads((ROOT / "tools" / "i18n" / "practice.json").read_text(encoding="utf-8"))
        for lang in ("kk", "en"):
            for slug, task in build_practice.TASKS.items():
                tr = data[lang]["tasks"].get(slug)
                self.assertIsNotNone(tr, f"{lang}: нет перевода задачи {slug}")
                self.assertTrue(tr["title"] and tr["text"], f"{lang}/{slug}")
                self.assertEqual(len(tr["hints"]), len(task["hints"]["ru"]), f"{lang}/{slug}: число подсказок")

    def test_translated_page_has_no_russian_task_text(self):
        page = build_practice.build("en")
        for slug, task in build_practice.TASKS.items():
            self.assertNotIn(task["title"]["ru"] + "</h3>", page, slug)


class StepSnapshots(unittest.TestCase):
    def test_snapshots_only_for_steps_that_change_files(self):
        steps = sorted(sync_examples.snapshots())
        self.assertEqual([n for p, n in steps if p == "flask-todo"], [2, 5])
        self.assertEqual([n for p, n in steps if p == "django-todo"], [1, 2, 3, 4, 5, 7, 8, 9])

    def test_links_are_stable(self):
        page = (ROOT / "project.html").read_text(encoding="utf-8")
        snaps = sync_examples.snapshots()
        once = sync_examples.page_with_links(page, snaps)
        self.assertEqual(once, sync_examples.page_with_links(once, snaps))
        self.assertEqual(once.count(sync_examples.LINK_TEXT), len(snaps))

    def test_zip_does_not_depend_on_order(self):
        a = sync_examples.pack_files("x", {"b.py": b"1", "A.txt": b"2\r\n"})
        b = sync_examples.pack_files("x", {"A.txt": b"2\n", "b.py": b"1"})
        self.assertEqual(a, b)


class ServiceWorker(unittest.TestCase):
    def test_version_ignores_files_that_are_not_published(self):
        files = set(build_sw.site_files())
        self.assertIn("index.html", files)
        self.assertNotIn("README.txt", files)
        self.assertNotIn("sw.js", files)
        self.assertFalse(any(name.startswith(("tools/", "docs/", "examples/")) or "__pycache__" in name for name in files))


if __name__ == "__main__":
    unittest.main()
