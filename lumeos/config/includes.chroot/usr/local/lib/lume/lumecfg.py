"""Configuracao e funcoes puras do LumeOS (widgets e cor do sistema).

Nao importa GTK: tudo aqui roda e e testado sem tela (tests/test_lumecfg.py).
"""
import copy
import json
import math
import os
import re
import tempfile
import time

CONFIG_HOME = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
CONFIG_DIR = os.path.join(CONFIG_HOME, "lume")
WIDGETS_FILE = os.path.join(CONFIG_DIR, "widgets.json")
ACCENT_FILE = os.path.join(CONFIG_DIR, "accent.json")
FIRST_RUN_MARK = os.path.join(CONFIG_DIR, "first-run-done")

MAX_WIDGETS = 12
CASES = ("normal", "upper", "lower", "first")
DISPLAY_NAMES = {"hora": "Hora", "data": "Data"}

ACCENT_BEGIN = "/* >>> lume-accent (gerado pelo LumeOS; edite so fora deste bloco) */"
ACCENT_END = "/* <<< lume-accent */"

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
_ID_RE = re.compile(r"[^a-z0-9_-]+")
# Codigos de strftime que mudam a cada segundo (ou mostram segundos).
_SECONDS_RE = re.compile(r"%[SsTXcr+]")


# ---------- valores basicos ----------

def clamp_float(value, lo, hi, default):
    """Converte para float finito dentro de [lo, hi]; qualquer outra coisa vira default."""
    if isinstance(value, bool):
        return default
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(v):
        return default
    return max(lo, min(hi, v))


def valid_hex(value, default):
    if isinstance(value, str) and _HEX_RE.match(value):
        return value.lower()
    return default


def hex_to_rgb(h):
    h = valid_hex(h, "#000000")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5))


def rgb_to_hex(r, g, b):
    return "#%02x%02x%02x" % tuple(
        max(0, min(255, int(round(c * 255)))) for c in (r, g, b))


def _lin(c):
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(h):
    r, g, b = hex_to_rgb(h)
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast_fg(h):
    """Preto ou branco, o que ler melhor sobre a cor h."""
    return "#000000" if luminance(h) > 0.179 else "#ffffff"


def shade(h, amount):
    """amount > 0 clareia, amount < 0 escurece (mistura com branco ou preto)."""
    r, g, b = hex_to_rgb(h)
    target = 1.0 if amount > 0 else 0.0
    a = min(1.0, abs(amount))
    return rgb_to_hex(*(c + (target - c) * a for c in (r, g, b)))


# ---------- widgets ----------

def new_widget(wid, **over):
    w = {
        "id": wid,
        "enabled": True,
        "format": "%H:%M",
        "font": "Inter 24",
        "color": "#ffffff",
        "alpha": 1.0,
        "shadow": True,
        "case": "normal",
        "x": 0.5,
        "y": 0.5,
    }
    w.update(over)
    return w


def default_config():
    return {
        "version": 1,
        "locked": False,
        "widgets": [
            new_widget("hora", format="%H:%M", font="Inter Light 64",
                       x=0.94, y=0.06),
            new_widget("data", format="%A, %d de %B", font="Inter 18",
                       alpha=0.85, x=0.94, y=0.20),
        ],
    }


def display_name(w):
    return DISPLAY_NAMES.get(w["id"], w["id"])


def normalize_widget(raw, fallback_id):
    base = new_widget(fallback_id)
    if not isinstance(raw, dict):
        return base
    wid = raw.get("id")
    wid = _ID_RE.sub("-", wid.strip().lower())[:32].strip("-") if isinstance(wid, str) else ""
    base["id"] = wid or fallback_id
    base["enabled"] = raw.get("enabled", True) is not False
    fmt = raw.get("format")
    base["format"] = fmt[:200] if isinstance(fmt, str) and fmt else base["format"]
    font = raw.get("font")
    base["font"] = font[:100] if isinstance(font, str) and font.strip() else base["font"]
    base["color"] = valid_hex(raw.get("color"), base["color"])
    base["alpha"] = clamp_float(raw.get("alpha"), 0.05, 1.0, 1.0)
    base["shadow"] = raw.get("shadow", True) is not False
    base["case"] = raw.get("case") if raw.get("case") in CASES else "normal"
    base["x"] = clamp_float(raw.get("x"), 0.0, 1.0, 0.5)
    base["y"] = clamp_float(raw.get("y"), 0.0, 1.0, 0.5)
    return base


def normalize_config(raw):
    if not isinstance(raw, dict):
        return default_config()
    items = raw.get("widgets")
    if not isinstance(items, list):
        return default_config()
    widgets, seen = [], set()
    for i, item in enumerate(items[:MAX_WIDGETS]):
        w = normalize_widget(item, "widget-%d" % (i + 1))
        base, n = w["id"], 2
        while w["id"] in seen:
            w["id"] = "%s-%d" % (base[:28], n)
            n += 1
        seen.add(w["id"])
        widgets.append(w)
    return {"version": 1, "locked": raw.get("locked") is True, "widgets": widgets}


def unused_id(cfg, stem="texto"):
    used = {w["id"] for w in cfg["widgets"]}
    n = 1
    while "%s-%d" % (stem, n) in used:
        n += 1
    return "%s-%d" % (stem, n)


def save_json_atomic(path, data):
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_widgets(path=None):
    """Devolve (config normalizada, aviso ou None). Arquivo ausente ou quebrado vira o padrao."""
    path = path or WIDGETS_FILE
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        return default_config(), None
    except (OSError, ValueError) as e:
        return default_config(), "widgets.json ilegivel (%s); usando o padrao" % e
    return normalize_config(raw), None


def render_text(fmt, case="normal", now=None):
    """Formata o texto do widget. '\\n' digitado vira quebra de linha."""
    fmt = fmt.replace("\\n", "\n")
    try:
        s = time.strftime(fmt, now if now is not None else time.localtime())
    except (ValueError, OverflowError):
        s = fmt
    if case == "upper":
        s = s.upper()
    elif case == "lower":
        s = s.lower()
    elif case == "first":
        s = s[:1].upper() + s[1:]
    return s


def uses_seconds(fmt):
    return bool(_SECONDS_RE.search(fmt.replace("%%", "")))


def ms_until_next_tick(formats, now):
    """Tempo ate a proxima atualizacao: virada do segundo se algum widget mostra segundos,
    senao virada do minuto. Nunca menos de 50 ms."""
    frac = now - math.floor(now)
    if any(uses_seconds(f) for f in formats):
        ms = (1.0 - frac) * 1000.0
    else:
        ms = (60 - (int(now) % 60) - frac) * 1000.0
    return max(50, int(ms) + 5)


# ---------- posicao (fracao da area livre da tela) ----------

def fraction_to_px(frac, screen, size):
    return int(round(clamp_float(frac, 0.0, 1.0, 0.0) * max(0, screen - size)))


def px_to_fraction(px, screen, size):
    free = screen - size
    if free <= 0:
        return 0.0
    return clamp_float(px / free, 0.0, 1.0, 0.0)


def clamp_px(px, screen, size):
    return max(0, min(px, max(0, screen - size)))


# ---------- cor de destaque ----------

def accent_css_gtk3(c):
    fg = contrast_fg(c)
    hover = shade(c, 0.12)
    dim = shade(c, -0.25)
    return "\n".join([
        "@define-color accent_color %s;" % c,
        "@define-color accent_bg_color %s;" % c,
        "@define-color accent_fg_color %s;" % fg,
        "@define-color theme_selected_bg_color %s;" % c,
        "@define-color theme_selected_fg_color %s;" % fg,
        "@define-color selected_bg_color %s;" % c,
        "@define-color selected_fg_color %s;" % fg,
        "@define-color theme_unfocused_selected_bg_color %s;" % dim,
        "selection, *:selected { background-color: %s; color: %s; }" % (c, fg),
        "button.suggested-action { background-image: none; background-color: %s; color: %s; }" % (c, fg),
        "button.suggested-action:hover { background-image: none; background-color: %s; }" % hover,
        "switch:checked { background-image: none; background-color: %s; }" % c,
        "check:checked, radio:checked, check:indeterminate, radio:indeterminate "
        "{ background-image: none; background-color: %s; border-color: %s; color: %s; }" % (c, c, fg),
        "progressbar progress, scale highlight, scale trough highlight "
        "{ background-image: none; background-color: %s; }" % c,
    ])


def accent_css_gtk4(c):
    fg = contrast_fg(c)
    return "\n".join([
        "@define-color accent_color %s;" % c,
        "@define-color accent_bg_color %s;" % c,
        "@define-color accent_fg_color %s;" % fg,
    ])


def set_block(existing, body):
    """Poe (ou troca) o bloco gerenciado dentro do texto de um gtk.css, sem tocar no resto."""
    block = "%s\n%s\n%s\n" % (ACCENT_BEGIN, body, ACCENT_END)
    cleaned = remove_block(existing)
    if cleaned and not cleaned.endswith("\n"):
        cleaned += "\n"
    return cleaned + block


def remove_block(text):
    b = text.find(ACCENT_BEGIN)
    if b == -1:
        return text
    e = text.find(ACCENT_END, b)
    if e == -1:
        return text[:b].rstrip("\n") + ("\n" if text[:b].strip() else "")
    tail = text[e + len(ACCENT_END):].lstrip("\n")
    head = text[:b]
    return head + tail


def _read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _write_text_atomic(path, text):
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def apply_accent(hex_color, config_home=None):
    """Grava a cor nos gtk.css do usuario (GTK3 e GTK4) e em accent.json. Devolve a cor normalizada."""
    c = valid_hex(hex_color, None)
    if c is None:
        raise ValueError("cor invalida: %r" % (hex_color,))
    home = config_home or CONFIG_HOME
    for sub, fn in (("gtk-3.0", accent_css_gtk3), ("gtk-4.0", accent_css_gtk4)):
        path = os.path.join(home, sub, "gtk.css")
        _write_text_atomic(path, set_block(_read_text(path), fn(c)))
    save_json_atomic(os.path.join(home, "lume", "accent.json"), {"accent": c})
    return c


def reset_accent(config_home=None):
    home = config_home or CONFIG_HOME
    for sub in ("gtk-3.0", "gtk-4.0"):
        path = os.path.join(home, sub, "gtk.css")
        text = _read_text(path)
        if ACCENT_BEGIN in text:
            _write_text_atomic(path, remove_block(text))
    try:
        os.unlink(os.path.join(home, "lume", "accent.json"))
    except FileNotFoundError:
        pass


def load_accent(config_home=None):
    path = os.path.join(config_home or CONFIG_HOME, "lume", "accent.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return valid_hex(json.load(f).get("accent"), None)
    except (OSError, ValueError, AttributeError):
        return None


def clone(cfg):
    return copy.deepcopy(cfg)
