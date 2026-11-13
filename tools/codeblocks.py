"""Блоки кода со страниц сайта: <div class="code-block"> с подписью в первом <span> и кодом в <code>.

Общий разбор для tools/check_examples.py и tools/check_django.py.
"""
from html.parser import HTMLParser


class Blocks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self.depth = 0
        self.block = None
        self.in_label = False
        self.in_code = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div" and "code-block" in (attrs.get("class") or "").split():
            # lang: что запускает кнопка блока — "python" или "html" (предпросмотр страницы); пусто, если кнопки нет
            self.block = {"run": "data-run" in attrs, "lang": attrs.get("data-run") or "", "label": "", "code": "", "depth": self.depth}
        if tag == "div":
            self.depth += 1
        if self.block is not None and tag == "span" and not self.block["label"]:
            self.in_label = True
        if self.block is not None and tag == "code":
            self.in_code = True

    def handle_endtag(self, tag):
        if tag == "span":
            self.in_label = False
        if tag == "code":
            self.in_code = False
        if tag == "div":
            self.depth -= 1
            if self.block is not None and self.depth == self.block["depth"]:
                self.blocks.append(self.block)
                self.block = None

    def handle_data(self, data):
        if self.block is None:
            return
        if self.in_label:
            self.block["label"] += data
        elif self.in_code:
            self.block["code"] += data


def read(path):
    """Блоки кода страницы: список словарей {"run": bool, "label": str, "code": str}."""
    parser = Blocks()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.blocks
