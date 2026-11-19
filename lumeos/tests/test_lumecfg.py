"""Testes das funcoes puras de lumecfg (sem GTK, sem tela).

Rodar da pasta do projeto:  python3 -m unittest discover -s tests -v
"""
import json
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "config", "includes.chroot", "usr", "local", "lib", "lume"))
import lumecfg as C  # noqa: E402


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class Basics(unittest.TestCase):
    def test_clamp_float_rejects_non_finite_and_bool(self):
        self.assertEqual(C.clamp_float(float("nan"), 0, 1, 0.5), 0.5)
        self.assertEqual(C.clamp_float(float("inf"), 0, 1, 0.5), 0.5)
        self.assertEqual(C.clamp_float(True, 0, 1, 0.5), 0.5)
        self.assertEqual(C.clamp_float("abc", 0, 1, 0.5), 0.5)
        self.assertEqual(C.clamp_float(7, 0, 1, 0.5), 1.0)
        self.assertEqual(C.clamp_float(-7, 0, 1, 0.5), 0.0)

    def test_hex(self):
        self.assertEqual(C.valid_hex("#AABBCC", None), "#aabbcc")
        self.assertIsNone(C.valid_hex("AABBCC", None))
        self.assertIsNone(C.valid_hex("#abc", None))
        self.assertEqual(C.rgb_to_hex(*C.hex_to_rgb("#3b82f6")), "#3b82f6")

    def test_contrast_fg(self):
        self.assertEqual(C.contrast_fg("#ffffff"), "#000000")
        self.assertEqual(C.contrast_fg("#000000"), "#ffffff")
        self.assertEqual(C.contrast_fg("#3b82f6"), "#000000")
        self.assertEqual(C.contrast_fg("#1e3a8a"), "#ffffff")

    def test_shade(self):
        self.assertEqual(C.shade("#808080", 1.0), "#ffffff")
        self.assertEqual(C.shade("#808080", -1.0), "#000000")


class Widgets(unittest.TestCase):
    def test_default_config_is_stable_under_normalize(self):
        d = C.default_config()
        self.assertEqual(C.normalize_config(d), d)

    def test_normalize_repairs_garbage(self):
        raw = {"widgets": [
            {"id": "Hora!!", "format": "", "font": 5, "color": "red", "alpha": 9,
             "x": float("nan"), "y": -3, "case": "zzz", "shadow": "nope"},
            "lixo", None,
            {"id": "hora"},
        ], "locked": "sim"}
        cfg = C.normalize_config(raw)
        w = cfg["widgets"][0]
        self.assertEqual(w["id"], "hora")
        self.assertEqual(w["format"], "%H:%M")
        self.assertEqual(w["color"], "#ffffff")
        self.assertEqual(w["alpha"], 1.0)
        self.assertEqual((w["x"], w["y"]), (0.5, 0.0))
        self.assertEqual(w["case"], "normal")
        self.assertFalse(cfg["locked"])
        ids = [x["id"] for x in cfg["widgets"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 4)

    def test_normalize_limits_widget_count(self):
        raw = {"widgets": [{"id": "w%d" % i} for i in range(50)]}
        self.assertEqual(len(C.normalize_config(raw)["widgets"]), C.MAX_WIDGETS)

    def test_normalize_non_dict(self):
        self.assertEqual(C.normalize_config([1, 2]), C.default_config())
        self.assertEqual(C.normalize_config({"widgets": 3}), C.default_config())

    def test_unused_id(self):
        cfg = {"widgets": [{"id": "texto-1"}, {"id": "texto-2"}]}
        self.assertEqual(C.unused_id(cfg), "texto-3")

    def test_load_missing_and_broken(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "widgets.json")
            cfg, warn = C.load_widgets(p)
            self.assertEqual(cfg, C.default_config())
            self.assertIsNone(warn)
            with open(p, "w") as f:
                f.write("{quebrado")
            cfg, warn = C.load_widgets(p)
            self.assertEqual(cfg, C.default_config())
            self.assertIsNotNone(warn)

    def test_save_roundtrip_and_no_temp_left(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "sub", "widgets.json")
            cfg = C.default_config()
            cfg["widgets"][0]["color"] = "#112233"
            C.save_json_atomic(p, cfg)
            loaded, warn = C.load_widgets(p)
            self.assertIsNone(warn)
            self.assertEqual(loaded, cfg)
            self.assertEqual(os.listdir(os.path.dirname(p)), ["widgets.json"])


class TextAndTime(unittest.TestCase):
    NOW = time.struct_time((2026, 11, 18, 9, 5, 7, 2, 322, -1))  # quarta, 18 nov 2026 09:05:07

    def test_render(self):
        self.assertEqual(C.render_text("%H:%M", now=self.NOW), "09:05")
        self.assertEqual(C.render_text("%d/%m/%Y", now=self.NOW), "18/11/2026")
        self.assertEqual(C.render_text("%H:%M\\n%d", now=self.NOW), "09:05\n18")
        self.assertEqual(C.render_text("%%", now=self.NOW), "%")

    def test_case(self):
        self.assertEqual(C.render_text("abc de", "upper", self.NOW), "ABC DE")
        self.assertEqual(C.render_text("ABC", "lower", self.NOW), "abc")
        self.assertEqual(C.render_text("abc de", "first", self.NOW), "Abc de")
        self.assertEqual(C.render_text("", "first", self.NOW), "")

    def test_uses_seconds(self):
        self.assertTrue(C.uses_seconds("%H:%M:%S"))
        self.assertTrue(C.uses_seconds("%T"))
        self.assertFalse(C.uses_seconds("%H:%M"))
        self.assertFalse(C.uses_seconds("100%%S"))

    def test_tick_delay(self):
        # 10:00:30.250 -> sem segundos espera ate 10:01:00 (29,75 s); com segundos, 0,75 s
        now = 1700000000.0
        now = now - (now % 60) + 30.25
        self.assertAlmostEqual(C.ms_until_next_tick(["%H:%M"], now), 29750 + 5, delta=2)
        self.assertAlmostEqual(C.ms_until_next_tick(["%H:%M:%S"], now), 750 + 5, delta=2)
        self.assertAlmostEqual(C.ms_until_next_tick(["%H:%M", "%S"], now), 750 + 5, delta=2)
        self.assertGreaterEqual(C.ms_until_next_tick([], now - 0.0001), 50)


class Position(unittest.TestCase):
    def test_roundtrip(self):
        for frac in (0.0, 0.25, 0.94, 1.0):
            px = C.fraction_to_px(frac, 1920, 300)
            back = C.px_to_fraction(px, 1920, 300)
            self.assertAlmostEqual(back, frac, delta=1 / 1620)

    def test_widget_bigger_than_screen(self):
        self.assertEqual(C.fraction_to_px(0.7, 100, 500), 0)
        self.assertEqual(C.px_to_fraction(40, 100, 500), 0.0)

    def test_clamp_px(self):
        self.assertEqual(C.clamp_px(-5, 1920, 300), 0)
        self.assertEqual(C.clamp_px(1900, 1920, 300), 1620)
        self.assertEqual(C.clamp_px(50, 100, 500), 0)


class Accent(unittest.TestCase):
    def test_block_replace_is_idempotent_and_keeps_user_css(self):
        user = "/* meu css */\nwindow { border: 0; }\n"
        a = C.set_block(user, "AAA")
        b = C.set_block(a, "BBB")
        self.assertIn("meu css", b)
        self.assertIn("BBB", b)
        self.assertNotIn("AAA", b)
        self.assertEqual(b.count(C.ACCENT_BEGIN), 1)
        self.assertEqual(C.remove_block(b).strip(), user.strip())

    def test_remove_block_keeps_text_after_block(self):
        text = "antes\n" + C.ACCENT_BEGIN + "\nX\n" + C.ACCENT_END + "\ndepois\n"
        out = C.remove_block(text)
        self.assertIn("antes", out)
        self.assertIn("depois", out)
        self.assertNotIn("X", out)

    def test_remove_block_without_end_marker(self):
        text = "antes\n" + C.ACCENT_BEGIN + "\nlixo sem fim\n"
        self.assertEqual(C.remove_block(text), "antes\n")

    def test_apply_and_reset(self):
        with tempfile.TemporaryDirectory() as home:
            g3 = os.path.join(home, "gtk-3.0", "gtk.css")
            os.makedirs(os.path.dirname(g3))
            with open(g3, "w") as f:
                f.write("window { color: red; }\n")
            c = C.apply_accent("#3B82F6", config_home=home)
            self.assertEqual(c, "#3b82f6")
            css3 = read(g3)
            css4 = read(os.path.join(home, "gtk-4.0", "gtk.css"))
            self.assertIn("window { color: red; }", css3)
            self.assertIn("@define-color accent_bg_color #3b82f6;", css3)
            self.assertIn("@define-color accent_bg_color #3b82f6;", css4)
            self.assertIn("@define-color accent_fg_color #000000;", css4)
            self.assertEqual(C.load_accent(home), "#3b82f6")
            C.apply_accent("#1e3a8a", config_home=home)
            self.assertEqual(read(g3).count(C.ACCENT_BEGIN), 1)
            self.assertIn("#ffffff;", C.accent_css_gtk4("#1e3a8a"))
            C.reset_accent(config_home=home)
            self.assertEqual(read(g3).strip(), "window { color: red; }")
            self.assertNotIn(C.ACCENT_BEGIN, read(os.path.join(home, "gtk-4.0", "gtk.css")))
            self.assertIsNone(C.load_accent(home))

    def test_apply_rejects_bad_color(self):
        with tempfile.TemporaryDirectory() as home:
            with self.assertRaises(ValueError):
                C.apply_accent("vermelho", config_home=home)
            self.assertFalse(os.path.exists(os.path.join(home, "gtk-3.0")))

    def test_json_files_are_valid(self):
        with tempfile.TemporaryDirectory() as home:
            C.apply_accent("#22c55e", config_home=home)
            with open(os.path.join(home, "lume", "accent.json")) as f:
                self.assertEqual(json.load(f), {"accent": "#22c55e"})


if __name__ == "__main__":
    unittest.main()
