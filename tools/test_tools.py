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
        for slug in (p.name for p in ROOT.glob("*.html") if p.name != "404.html"):
            self.assertIn(slug, layout.NAMES)
            self.assertEqual(len(layout.NAMES[slug]), 3)

    def test_apply_is_stable(self):
        path = ROOT / "about.html"
        _, once = layout.apply(path)
        _, twice = layout.apply(path, once)
        self.assertEqual(once, twice)


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


class ServiceWorker(unittest.TestCase):
    def test_version_ignores_files_that_are_not_published(self):
        files = set(build_sw.site_files())
        self.assertIn("index.html", files)
        self.assertNotIn("README.txt", files)
        self.assertNotIn("sw.js", files)
        self.assertFalse(any(name.startswith(("tools/", "docs/", "examples/")) or "__pycache__" in name for name in files))


if __name__ == "__main__":
    unittest.main()
