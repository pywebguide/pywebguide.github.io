# Проверка задач PyWeb Guide. Работает в браузере (Pyodide) и в tools/check_tasks.py.
#
# Тесты задачи — обычный код Python. Каждая проверка записывается так:
#     case('greet("Анна")', "Привет, Анна!", "подсказка")
# Первый аргумент — выражение, которое вычисляется в коде ученика, второй — ожидаемый ответ.
# Если ответ не совпал, ученик видит выражение, ожидаемый и полученный результат.

LABELS = {
    "ru": ("Проверка", "Ожидалось", "Получено", "Подсказка", "ошибка"),
    "kk": ("Тексеру", "Күтілгені", "Алынғаны", "Кеңес", "қате"),
    "en": ("Check", "Expected", "Got", "Hint", "error"),
}


class CaseFailed(AssertionError):
    pass


def check(code, tests, lang="ru"):
    words = LABELS.get(lang, LABELS["ru"])
    # exec и eval здесь намеренно: это код самого ученика и тесты с сайта, всё выполняется
    # в его браузере (Pyodide) или в CI, чужие данные сюда не попадают
    ns: dict[str, object] = {"__name__": "__main__"}
    exec(compile(code, "<code>", "exec"), ns)

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
