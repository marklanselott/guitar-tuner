from PIL import Image, ImageDraw, ImageFont
import mmap
import os
import time
from threading import Thread, Lock


class FBDisplay:
    def __init__(self, width=1024, height=600):
        self.width = width
        self.height = height
        self.size = width * height * 4
        self.running = True
        self.lock = Lock()

        self.render_interval = 1 / 30
        self.dev_mode = os.getenv("FB_DEBUG_TIMING") == "1"
        self._last_render_debug_at = 0.0
        self._current_note = ""
        self._current_target = 0.0
        self._current_now = 0.0
        self._current_valid = False
        self._current_diff = 0.0
        self._current_spectrum = None
        self._signal_mix = 0.0
        self._visual_mix = 0.0
        self._last_visible_target = 0.0
        self._last_visible_current = 0.0
        self._fps_tick = 0
        self._fps_max = 25

        fb_path = os.getenv("FB0_PATH")
        font_path = os.getenv("font_path")

        try:
            self.fd = os.open(fb_path, os.O_RDWR)
            self.fb = mmap.mmap(self.fd, self.size, mmap.MAP_SHARED, mmap.PROT_WRITE)
        except Exception as exc:
            print(f"FB display error: {exc}")
            raise

        try:
            self.font_note = ImageFont.truetype(font_path, 150)
            self.font_info = ImageFont.truetype(font_path, 34)
            self.font_small = ImageFont.truetype(font_path, 24)
        except Exception:
            self.font_note = ImageFont.load_default()
            self.font_info = ImageFont.load_default()
            self.font_small = ImageFont.load_default()

        self.frame = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 255))
        self.draw = ImageDraw.Draw(self.frame)
        self._line_x1 = 120
        self._line_x2 = self.width - 120
        self._line_y = self.height // 2
        self._line_h = 18
        self._line_w = self._line_x2 - self._line_x1
        self._line_left = self._line_x1
        self._line_top = self._line_y - self._line_h // 2
        self._line_bg = Image.new("RGBA", (self._line_w, self._line_h), (86, 94, 108, 255))
        self._line_gray_mask = self._build_rounded_mask(self._line_w, self._line_h, self._line_h // 2)
        self._line_static = self._build_static_line()
        self._cached_note = None
        self._cached_current = None
        self._cached_target = None
        self._cached_diff = None
        self._cached_note_img = None
        self._cached_current_img = None
        self._cached_target_img = None
        self._cached_diff_img = None
        self.render_thread = Thread(target=self._render_loop, daemon=True)
        self.render_thread.start()

    def update(self, note, target, current, diff, is_valid, spectrum=None):
        with self.lock:
            self._current_note = note
            self._current_target = target
            self._current_now = current
            self._current_valid = is_valid
            self._current_diff = diff
            self._current_spectrum = spectrum
            target_signal = 1.0 if (target > 0.0 and current > 0.0) else 0.0
            if target_signal > 0.0:
                self._last_visible_target = target
                self._last_visible_current = current
            if target_signal > self._signal_mix:
                self._signal_mix = self._signal_mix * 0.90 + target_signal * 0.10
            else:
                self._signal_mix = self._signal_mix * 0.94 + target_signal * 0.06

    def _text_size(self, text, font):
        if hasattr(font, "getbbox"):
            box = font.getbbox(text)
            return box[2] - box[0], box[3] - box[1]
        return self.draw.textsize(text, font=font)

    def _build_rounded_mask(self, width, height, radius):
        mask = Image.new("L", (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=radius, fill=255)
        return mask

    def _build_static_line(self):
        static = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        shadow = Image.new("RGBA", (self._line_w, self._line_h + 4), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle([0, 2, self._line_w - 1, self._line_h + 1], radius=max(1, self._line_h // 2), fill=(0, 0, 0, 60))
        static.alpha_composite(shadow, (self._line_left, self._line_top + 2))

        base_bar = self._line_bg.copy()
        base_bar.putalpha(self._line_gray_mask)
        static.alpha_composite(base_bar, (self._line_left, self._line_top))
        return static

    def _make_text_image(self, text, font, fill):
        if not text:
            return None, 0, 0
        if hasattr(font, "getbbox"):
            box = font.getbbox(text)
            w = box[2] - box[0]
            h = box[3] - box[1]
            img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.text((-box[0], -box[1]), text, font=font, fill=fill)
            return img, w, h
        w, h = self._text_size(text, font)
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.text((0, 0), text, font=font, fill=fill)
        return img, w, h

    def _render_loop(self):
        last_tick = time.perf_counter()
        while self.running:
            now = time.perf_counter()
            if now - last_tick >= self.render_interval:
                delta_ms = (now - last_tick) * 1000.0
                started = time.perf_counter()
                self._render_frame()
                render_ms = (time.perf_counter() - started) * 1000.0
                last_tick = now
                if self.dev_mode:
                    current_time = time.perf_counter()
                    if current_time - self._last_render_debug_at >= 0.5:
                        print(
                            "dt={:.2f}ms render={:.2f}ms mix={:.2f} target={:.2f} current={:.2f}".format(
                                delta_ms,
                                render_ms,
                                self._visual_mix,
                                self._current_target,
                                self._current_now,
                            )
                        )
                        self._last_render_debug_at = current_time
            else:
                time.sleep(0.001)

    def _render_frame(self):
        with self.lock:
            note = self._current_note
            target = self._current_target if self._signal_mix > 0.001 else 0.0
            current = self._current_now if self._signal_mix > 0.001 else 0.0
            valid = self._current_valid
            diff = self._current_diff
            self._visual_mix = self._visual_mix * 0.90 + self._signal_mix * 0.10
            visual_mix = self._visual_mix

        self.frame.paste((0, 0, 0, 255), (0, 0, self.width, self.height))

        self.frame.alpha_composite(self._line_static)

        signal_mix = visual_mix
        if signal_mix > 0.001:
            diff_abs = abs(current - target)
            acc = max(0.0, min(1.0, 1.0 - (diff_abs / 5.0)))
            acc = acc * (0.35 + 0.65 * signal_mix)
            band_width = int(self._line_w * (0.10 + 0.55 * (acc ** 1.35)))
            band_width = max(10, min(self._line_w, band_width))
            center = self._line_left + self._line_w // 2
            band_left = max(self._line_left, center - band_width // 2)
            band_right = min(self._line_x2, center + band_width // 2)

            glow = int(130 + 110 * signal_mix)
            band_radius = max(1, self._line_h // 2)
            self.draw.rounded_rectangle(
                [band_left, self._line_top, band_right, self._line_top + self._line_h - 1],
                radius=band_radius,
                fill=(58, 245, 126, glow),
            )

        if note:
            if note != self._cached_note:
                self._cached_note = note
                self._cached_note_img, _, _ = self._make_text_image(note, self.font_note, (255, 255, 255, 255))
            if self._cached_note_img is not None:
                self.frame.alpha_composite(self._cached_note_img, ((self.width - self._cached_note_img.width) // 2, 28))
        else:
            self._cached_note = None
            self._cached_note_img = None

        target_str = "Target: {:.1f} Hz".format(target)
        current_str = "Now: {:.1f} Hz".format(current)
        if valid:
            info_color = (230, 230, 230, 255)
            current_color = (255, 255, 255, 255)
        else:
            info_color = (160, 170, 184, 255)
            current_color = (160, 170, 184, 255)

        if current_str != self._cached_current:
            self._cached_current = current_str
            self._cached_current_img, _, _ = self._make_text_image(current_str, self.font_info, current_color)
        if target_str != self._cached_target:
            self._cached_target = target_str
            self._cached_target_img, _, _ = self._make_text_image(target_str, self.font_info, info_color)

        if signal_mix > 0.001:
            if self._cached_current_img is not None:
                self.frame.alpha_composite(self._cached_current_img, (120, self.height - 92))
            if self._cached_target_img is not None:
                self.frame.alpha_composite(self._cached_target_img, (self.width - 120 - self._cached_target_img.width, self.height - 92))
        else:
            self._cached_current = None
            self._cached_current_img = None
            self._cached_target = None
            self._cached_target_img = None

        diff_str = "{:+.0f} cents".format(diff * 1200.0 / max(target, 1e-6)) if target > 0 else ""
        if diff_str:
            if diff_str != self._cached_diff:
                self._cached_diff = diff_str
                self._cached_diff_img, _, _ = self._make_text_image(diff_str, self.font_small, (120, 130, 145, 255))
            if self._cached_diff_img is not None:
                self.frame.alpha_composite(self._cached_diff_img, ((self.width - self._cached_diff_img.width) // 2, self.height - 52))
        else:
            self._cached_diff = None
            self._cached_diff_img = None

        if self.dev_mode:
            self._fps_tick = (self._fps_tick % self._fps_max) + 1
            fps_str = str(self._fps_tick)
            fps_img, _, _ = self._make_text_image(fps_str, self.font_small, (150, 160, 175, 255))
            if fps_img is not None:
                self.frame.alpha_composite(fps_img, (self.width - 28 - fps_img.width, 12))

        self.fb.seek(0)
        self.fb.write(self.frame.tobytes())

    def close(self):
        self.running = False
        if hasattr(self, "render_thread") and self.render_thread.is_alive():
            self.render_thread.join(timeout=1.0)
        try:
            self.fb.close()
        finally:
            os.close(self.fd)
