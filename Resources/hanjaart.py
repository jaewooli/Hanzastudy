import io
import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None


def _bundled_font_path():
    base = getattr(sys, "_MEIPASS", None)
    if not base:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "fonts", "HanjaFont.ttf")


_FONT_CANDIDATES = [
    _bundled_font_path(),
    r"C:\Windows\Fonts\malgun.ttf",
    r"C:\Windows\Fonts\malgunbd.ttf",
    r"C:\Windows\Fonts\batang.ttc",
    r"C:\Windows\Fonts\gulim.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]

_font_bytes_cache = {}
_font_cache = {}


def _read_font_bytes(path):
    """파일 경로를 FreeType에 그대로 넘기면 일부 환경(WSL의 /mnt/c 등)에서
    mmap 관련 충돌(Bus error)이 날 수 있어, 항상 바이트를 직접 읽어 넘긴다."""
    if path in _font_bytes_cache:
        return _font_bytes_cache[path]
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        data = None
    _font_bytes_cache[path] = data
    return data


def _load_fonts(size):
    """지정한 크기로 번들 폰트를 우선 시도하고, 없거나 글자가 없으면 시스템 폰트를 차례로 시도한다."""
    if size in _font_cache:
        return _font_cache[size]
    fonts = []
    if Image is not None:
        for path in _FONT_CANDIDATES:
            data = _read_font_bytes(path) if os.path.exists(path) else None
            if data is None:
                continue
            try:
                fonts.append(ImageFont.truetype(io.BytesIO(data), size))
            except OSError:
                continue
    _font_cache[size] = fonts
    return fonts


def _rasterize(hanja, font, width, height):
    image = Image.new("L", (width, height), color=0)
    draw = ImageDraw.Draw(image)
    bbox = draw.textbbox((0, 0), hanja, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (width - text_w) // 2 - bbox[0]
    y = (height - text_h) // 2 - bbox[1]
    draw.text((x, y), hanja, fill=255, font=font)
    if image.getbbox() is None:
        return None
    return image


# ---- Sixel: 실제 폰트 모양 그대로, 터미널이 지원하면 이미지로 그린다 ----
# 터미널 한 줄 높이를 대략 20px로 가정해 "4줄" 정도를 목표로 잡은 값.
_SIXEL_SIZE = 80
_SIXEL_COLOR = (0, 220, 0)
# 이진(켜짐/꺼짐) 대신 여러 단계의 밝기로 그려서, 안티에일리어싱된 얇은 획이
# 뭉개지지 않고 살아남게 한다(굵은 폰트로 억지로 두껍게 하지 않아도 됨).
_SIXEL_LEVELS = 8


def _bucket(value, levels):
    if value == 0:
        return 0
    return max(1, round(value / 255 * (levels - 1)))


def _encode_sixel(image):
    width, height = image.size
    pixels = image.load()
    levels = _SIXEL_LEVELS
    r0, g0, b0 = _SIXEL_COLOR
    parts = ["\x1bP0;1;0q", f'"1;1;{width};{height}']
    for i in range(1, levels):
        frac = i / (levels - 1)
        r, g, b = r0 * frac, g0 * frac, b0 * frac
        parts.append(f"#{i};2;{round(r * 100 / 255)};{round(g * 100 / 255)};{round(b * 100 / 255)}")

    for band_start in range(0, height, 6):
        band_h = min(6, height - band_start)
        buckets = [
            [_bucket(pixels[x, band_start + dy], levels) if dy < band_h else 0 for dy in range(6)]
            for x in range(width)
        ]
        for level in range(1, levels):
            chars = []
            any_set = False
            for col in buckets:
                bits = 0
                for dy in range(6):
                    if col[dy] == level:
                        bits |= 1 << dy
                        any_set = True
                chars.append(chr(63 + bits))
            if any_set:
                parts.append(f"#{level}" + "".join(chars) + "$")
        parts.append("-")
    parts.append("\x1b\\")
    return "".join(parts)


def render_sixel(hanja):
    """한자 한 글자를 실제 폰트 모양의 Sixel 그래픽으로 렌더링한다. 실패하면 None."""
    if not hanja or len(hanja) != 1:
        return None
    for font in _load_fonts(int(_SIXEL_SIZE * 0.88)):
        image = _rasterize(hanja, font, _SIXEL_SIZE, _SIXEL_SIZE)
        if image is not None:
            return _encode_sixel(image)
    return None


# ---- 블록 문자 아트: Sixel을 지원하지 않는 터미널을 위한 대체 표시 ----
_BLOCK_WIDTH = 16
_BLOCK_HEIGHT = 32


def _render_half_block(image):
    width, height = image.size
    pixels = image.load()
    lines = []
    for row in range(0, height, 2):
        chars = []
        for col in range(width):
            top = pixels[col, row] > 128
            bottom = row + 1 < height and pixels[col, row + 1] > 128
            if top and bottom:
                chars.append("\u2588")
            elif top:
                chars.append("\u2580")
            elif bottom:
                chars.append("\u2584")
            else:
                chars.append(" ")
        lines.append("".join(chars))
    if not any(line.strip() for line in lines):
        return None
    return "\n".join(lines)


def render(hanja):
    """한자 한 글자를 반블록 문자 아트 문자열로 렌더링한다. 실패하면 None."""
    if not hanja or len(hanja) != 1:
        return None
    for font in _load_fonts(int(_BLOCK_HEIGHT * 0.9)):
        image = _rasterize(hanja, font, _BLOCK_WIDTH, _BLOCK_HEIGHT)
        if image is None:
            continue
        art = _render_half_block(image)
        if art is not None:
            return art
    return None


def best(hanja):
    """현재 환경에서 가장 나은 한자 표시 문자열을 돌려준다(항상 폴백으로 원문 글자를 보장)."""
    if not os.environ.get("HANZA_NO_SIXEL"):
        art = render_sixel(hanja)
        if art is not None:
            return art
    return render(hanja) or hanja


# ---- 여러 글자를 한 줄로: 한자어, 골라맞히기 보기 ----
# 글자 사이 간격과 보기 번호 자리 (글자 칸 크기에 대한 비율)
_ROW_GAP = 0.25
_ROW_LABEL = 0.45
_BLOCK_ROW_GAP = 2


def _glyph(hanja, size):
    """size x size 칸에 그린 한 글자. 어느 폰트로도 못 그리면 None."""
    for font in _load_fonts(int(size * 0.88)):
        image = _rasterize(hanja, font, size, size)
        if image is not None:
            return image
    return None


def _label_font(size):
    """번들 폰트에는 숫자가 없어 보기 번호는 Pillow 기본 폰트로 그린다."""
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _render_row(chars, labels, size):
    """글자들을 가로로 이어 붙인 이미지. 한 글자라도 못 그리면 None."""
    glyphs = [_glyph(c, size) for c in chars]
    if any(g is None for g in glyphs):
        return None
    gap = int(size * _ROW_GAP)
    label_w = int(size * _ROW_LABEL) if labels else 0
    cell = label_w + size
    image = Image.new("L", (cell * len(chars) + gap * (len(chars) - 1), size), color=0)
    draw = ImageDraw.Draw(image)
    font = _label_font(int(size * 0.45)) if labels else None
    for i, glyph in enumerate(glyphs):
        x = i * (cell + gap)
        if labels:
            draw.text((x, 0), labels[i], fill=255, font=font)
        image.paste(glyph, (x + label_w, 0))
    return image


def render_row(chars, labels=None):
    """한 글자씩 그린 반블록 아트를 가로로 이어 붙인다. labels가 있으면 각 글자 왼쪽 위에 붙인다."""
    arts = [render(c) for c in chars]
    if not arts or any(a is None for a in arts):
        return None
    blocks = [a.split("\n") for a in arts]
    height = max(len(b) for b in blocks)
    pad = max(len(label) for label in labels) + 1 if labels else 0
    lines = []
    for n in range(height):
        parts = []
        for i, block in enumerate(blocks):
            head = (labels[i] if n == 0 else "").ljust(pad) if labels else ""
            parts.append(head + (block[n] if n < len(block) else "").ljust(_BLOCK_WIDTH))
        lines.append((" " * _BLOCK_ROW_GAP).join(parts).rstrip())
    return "\n".join(lines)


def best_row(chars, labels=None):
    """여러 글자(한자어, 보기)를 한 줄로 크게. 그릴 수 없으면 원문 글자를 늘어놓는다."""
    if not os.environ.get("HANZA_NO_SIXEL") and Image is not None and chars:
        image = _render_row(chars, labels, _SIXEL_SIZE)
        if image is not None:
            return _encode_sixel(image)
    art = render_row(chars, labels)
    if art is not None:
        return art
    if labels:
        return "    ".join(f"{label} {c}" for label, c in zip(labels, chars))
    return "  ".join(chars)
