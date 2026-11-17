"""Картинки превью ссылок (Open Graph) 1200×630 для каждой страницы на трёх языках.

Стиль плаката сайта: жёлтое поле, крупный заголовок чёрным шрифтом заголовков (Sofia Sans Extra Condensed,
на kk/ — Fira Sans Extra Condensed: в Sofia Sans нет казахских букв), снизу розовая полоса с названием сайта и языком.
Надпись — card из tools/seo.json или название страницы из меню (tools/layout.py). Картинки лежат в
assets/og/<язык>/<страница>.png, ссылки на них (og:image, twitter:image) вписывает tools/layout.py.

    python tools/build_og.py           # нарисовать все картинки
    python tools/build_og.py --check   # проверить, что картинки есть и совпадают с текстами (для CI)

Нужен Pillow (tools/requirements.txt). Важное держится в центральном квадрате 630×630 не полностью — заголовок
длинный, — поэтому название сайта и язык стоят на всю ширину полосы, а заголовок начинается слева, как на сайте:
в Telegram и WhatsApp картинка 1,91:1 показывается целиком.
"""
import hashlib
import io
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout  # noqa: E402

ROOT = layout.ROOT
FONTS = ROOT / "assets" / "fonts"
W, H = 1200, 630
BAND = 150            # розовая полоса снизу
PAD = 64              # поля слева и справа
YELLOW, PINK, INK = (255, 210, 73), (255, 196, 239), (10, 10, 10)
LANG_LINE = {"ru": "На русском языке", "kk": "Қазақ тілінде", "en": "In English"}
STAMP = "pyweb-og"    # в PNG хранится хеш входных данных: --check видит устаревшие картинки без перерисовки


def subset(ch):
    """Какой файл шрифта содержит букву (шрифты сайта разбиты по unicode-range, как в styles.css)."""
    cp = ord(ch)
    if 0x0400 <= cp <= 0x045F or cp in (0x0490, 0x0491, 0x04B0, 0x04B1, 0x2116):
        return "cyrillic"
    if 0x0460 <= cp <= 0x052F:
        return "cyrillic-ext"
    return "latin"


class Face:
    """Шрифт заголовков нужного размера: по букве выбирается файл с нужным алфавитом."""

    def __init__(self, lang, size):
        self.size = size
        self.fonts = {}
        for part in ("latin", "cyrillic", "cyrillic-ext"):
            if lang == "kk":
                font = ImageFont.truetype(str(FONTS / f"fira-sans-extra-condensed-{part}-900-normal.woff2"), size)
            else:
                font = ImageFont.truetype(str(FONTS / f"sofia-sans-extra-condensed-{part}-wght-normal.woff2"), size)
                font.set_variation_by_axes([900])
            self.fonts[part] = font

    def runs(self, text):
        out = []
        for ch in text:
            part = subset(ch) if ch.strip() else (out[-1][0] if out else "latin")
            if out and out[-1][0] == part:
                out[-1][1] += ch
            else:
                out.append([part, ch])
        return out

    def width(self, text):
        return sum(self.fonts[p].getlength(t) for p, t in self.runs(text))

    def draw(self, draw, xy, text, fill):
        x, y = xy
        for part, chunk in self.runs(text):
            draw.text((x, y), chunk, font=self.fonts[part], fill=fill)
            x += self.fonts[part].getlength(chunk)


def body_face(lang, size):
    """Onest для подписи языка: кириллица, казахские буквы и латиница из трёх файлов."""
    face = Face.__new__(Face)
    face.size = size
    face.fonts = {}
    for part in ("latin", "cyrillic", "cyrillic-ext"):
        font = ImageFont.truetype(str(FONTS / f"onest-{part}-wght-normal.woff2"), size)
        font.set_variation_by_axes([600])
        face.fonts[part] = font
    return face


def wrap(face, text, width):
    lines = []
    for word in text.split():
        if lines and face.width(lines[-1] + " " + word) <= width:
            lines[-1] += " " + word
        else:
            lines.append(word)
    return lines


def layout_title(lang, text):
    """Самый крупный размер, при котором заголовок помещается в жёлтое поле (не больше трёх строк)."""
    box_w, box_h = W - 2 * PAD, H - BAND - 2 * 48
    for size in range(240, 59, -4):
        face = Face(lang, size)
        lines = wrap(face, text, box_w)
        # У казахских букв (Қ, Ұ, Й в Fira Sans) выносные элементы длиннее: строки чуть свободнее
        line_h = size * (1.12 if lang == "kk" else 0.92)
        if len(lines) <= 3 and all(face.width(l) <= box_w for l in lines) and line_h * len(lines) <= box_h:
            return face, lines, line_h
    raise SystemExit(f"Заголовок не помещается на картинку: {text}")


def render(lang, slug):
    title = layout.card_text(lang, slug).upper()
    img = Image.new("RGB", (W, H), YELLOW)
    draw = ImageDraw.Draw(img)
    face, lines, line_h = layout_title(lang, title)
    # Заголовок по вертикали в середине жёлтого поля; базовая линия считается по высоте прописных
    ascent, _ = face.fonts["latin"].getmetrics()
    cap = face.fonts["latin"].getbbox("H")[1]
    block = line_h * (len(lines) - 1) + (ascent - cap)
    y = (H - BAND - block) / 2 - cap
    for line in lines:
        face.draw(draw, (PAD, y), line, INK)
        y += line_h
    draw.rectangle((0, H - BAND, W, H), fill=PINK)
    brand = Face(lang, 84)
    by = H - BAND + (BAND - 84 * 0.72) / 2 - brand.fonts["latin"].getbbox("H")[1]
    brand.draw(draw, (PAD, by), "PYWEB GUIDE", INK)
    small = body_face(lang, 34)
    label = LANG_LINE[lang]
    small.draw(draw, (W - PAD - small.width(label), H - BAND + 38), label, INK)
    site = "pywebguide.github.io"
    small.draw(draw, (W - PAD - small.width(site), H - BAND + 84), site, INK)
    # Палитра из 32 цветов: файл в несколько раз меньше, сглаживание букв сохраняется
    return img.quantize(colors=32, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)


def fingerprint(lang, slug):
    sources = [Path(__file__), *sorted(FONTS.glob("*.woff2"))]
    digest = hashlib.sha256(json.dumps([lang, slug, layout.card_text(lang, slug)], ensure_ascii=False).encode())
    for path in sources:
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()[:16]


def targets():
    for lang in layout.LANGS:
        for path in layout.pages():
            page_lang, slug = layout.page_lang(path)
            if page_lang == lang:
                yield lang, slug, ROOT / layout.og_image(lang, slug)


def stamp_of(path):
    try:
        with Image.open(path) as img:
            return img.info.get(STAMP), img.size
    except (OSError, ValueError):
        return None, None


def main():
    check = "--check" in sys.argv
    stale, written = [], 0
    for lang, slug, path in targets():
        want = fingerprint(lang, slug)
        stamp, size = stamp_of(path)
        if stamp == want and size == (W, H):
            continue
        if check:
            stale.append(path.relative_to(ROOT).as_posix())
            continue
        meta = PngImagePlugin.PngInfo()
        meta.add_text(STAMP, want)
        buffer = io.BytesIO()
        render(lang, slug).save(buffer, "PNG", optimize=True, pnginfo=meta)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(buffer.getvalue())
        written += 1
    expected = {p for _, _, p in targets()}
    extra = [p for p in (ROOT / "assets" / "og").rglob("*.png") if p not in expected]
    for path in extra:
        if check:
            stale.append(path.relative_to(ROOT).as_posix() + " (лишняя)")
        else:
            path.unlink()
    if check:
        if stale:
            print("Картинки превью устарели, запустите python tools/build_og.py:")
            print("\n".join("  " + s for s in stale))
            sys.exit(1)
        print(f"Картинки превью актуальны: {len(expected)}")
        return
    print(f"Нарисовано картинок: {written}, удалено лишних: {len(extra)}, всего: {len(expected)}")


if __name__ == "__main__":
    main()
