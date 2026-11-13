# Проверка задач PyWeb Guide. Работает в браузере (Pyodide) и в tools/check_tasks.py.
#
# Тесты задачи — обычный код Python. Каждая проверка записывается так:
#     case('greet("Анна")', "Привет, Анна!", "подсказка")
# Первый аргумент — выражение, которое вычисляется в коде ученика, второй — ожидаемый ответ.
# Если ответ не совпал, ученик видит выражение, ожидаемый и полученный результат.
# Что программа напечатала, возвращает printed(): case('printed()', "Привет!") — для первых уроков,
# где ученик знает print, но ещё не знает функций.
import sys

LABELS = {
    "ru": ("Проверка", "Ожидалось", "Получено", "Подсказка", "ошибка"),
    "kk": ("Тексеру", "Күтілгені", "Алынғаны", "Кеңес", "қате"),
    "en": ("Check", "Expected", "Got", "Hint", "error"),
}


class CaseFailed(AssertionError):
    pass


VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


def html_helpers(code):
    """Для HTML-задач (тесты начинаются с «# html»): код ученика — разметка, а не Python.
    count("li") — сколько тегов, text("h1") — текст внутри, attr("a", "href") — атрибут, style() — весь CSS."""
    from html.parser import HTMLParser

    elements, stack = [], []

    class Page(HTMLParser):
        def handle_starttag(self, tag, attrs):
            item = {"tag": tag, "attrs": dict(attrs), "text": ""}
            elements.append(item)
            if tag not in VOID:
                stack.append(item)

        def handle_endtag(self, tag):
            for i in range(len(stack) - 1, -1, -1):
                if stack[i]["tag"] == tag:
                    del stack[i:]
                    break

        def handle_data(self, data):
            for item in stack:
                item["text"] += data

    Page(convert_charrefs=True).feed(code)

    def found(name):
        return [e for e in elements if e["tag"] == name]

    def text(name, i=0):
        items = found(name)
        return " ".join(items[i]["text"].split()) if len(items) > i else None

    def attr(name, key, i=0):
        items = found(name)
        return items[i]["attrs"].get(key) if len(items) > i else None

    def style():
        return " ".join(" ".join(e["text"] for e in found("style")).split()).lower()

    return {"page": code, "count": lambda name: len(found(name)), "text": text, "attr": attr, "style": style}


def check(code, tests, lang="ru"):
    words = LABELS.get(lang, LABELS["ru"])
    # exec и eval здесь намеренно: это код самого ученика и тесты с сайта, всё выполняется
    # в его браузере (Pyodide) или в CI, чужие данные сюда не попадают
    ns: dict[str, object] = {"__name__": "__main__"}
    if tests.lstrip().startswith("# html"):
        # HTML-задача: разметку не выполняем, а разбираем
        ns.update(html_helpers(code))
    else:
        # Вывод ученика копируется: на экран он попадает как обычно, а копия нужна printed()
        printed_parts = []
        real_stdout = sys.stdout

        class Copy:
            def write(self, text):
                printed_parts.append(text)
                return real_stdout.write(text)

            def flush(self):
                real_stdout.flush()

        sys.stdout = Copy()
        try:
            exec(compile(code, "<code>", "exec"), ns)
        finally:
            sys.stdout = real_stdout
        ns["printed"] = lambda: "".join(printed_parts).rstrip("\n")

    def case(expr, expected, hint=""):
        try:
            got = eval(expr, ns)
            ok = got == expected
            shown = repr(got)
        except Exception as error:  # ошибка в коде ученика тоже ответ, её надо показать
            ok = False
            shown = f"{words[4]} {type(error).__name__}: {error}"
        if not ok:
            lines = [f"{words[0]}: {expr}", f"{words[1]}: {expected!r}", f"{words[2]}: {shown}"]
            if hint:
                lines.append(f"{words[3]}: {hint}")
            raise CaseFailed("\n".join(lines))

    ns["case"] = case
    exec(compile(tests, "<tests>", "exec"), ns)
