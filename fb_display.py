from PIL import Image, ImageDraw, ImageFont
import os, mmap, time
import numpy as np
import threading

class FBDisplay:
    def __init__(self, width=1024, height=600):
        self.width = width
        self.height = height
        self.size = width * height * 4
        
        try:
            self.fd = os.open(os.getenv("FB0_PATH"), os.O_RDWR)
            self.fb = mmap.mmap(self.fd, self.size, mmap.MAP_SHARED, mmap.PROT_WRITE)
        except Exception as e:
            print(f"Ошибка FB: {e}")
            raise

        self.current_diff = 0.0
        self.target_diff = 0.0
        self.smoothing = 0.12 
        
        self.data = {"note": "", "target": 0.0, "current": 0.0, "is_valid": False}
        self.running = True
        
        try:
            self.font_main = ImageFont.truetype(os.getenv("font_path"), 120)
            self.font_info = ImageFont.truetype(os.getenv("font_path"), 35)
            self.font_waiting = ImageFont.truetype(os.getenv("font_path"), 90)
        except:
            self.font_main = ImageFont.load_default()
            self.font_info = ImageFont.load_default()
            self.font_waiting = ImageFont.load_default()

        self.render_thread = threading.Thread(target=self._render_loop, daemon=True)
        self.render_thread.start()

    def update(self, note, target, current, diff, is_valid):
        self.data = {"note": note, "target": target, "current": current, "is_valid": is_valid}
        self.target_diff = diff if is_valid else 0.0

    def _render_loop(self):
        while self.running:
            start_time = time.time()
            self.current_diff += (self.target_diff - self.current_diff) * self.smoothing
            self._draw_frame()
            elapsed = time.time() - start_time
            time.sleep(max(0, 1/60 - elapsed))

    def _get_text_size(self, draw, text, font):
        if hasattr(font, 'getbbox'):
            bbox = font.getbbox(text)
            return bbox[2] - bbox[0], bbox[3] - bbox[1]
        else:
            return draw.textsize(text, font=font)

    def _draw_frame(self):
        img = Image.new('RGB', (self.width, self.height), color=(15, 15, 20))
        draw = ImageDraw.Draw(img)
        
        if self.data["is_valid"]:
            note_str = self.data["note"]
            w_n, h_n = self._get_text_size(draw, note_str, self.font_main)
            draw.text(((self.width - w_n)//2, 60), note_str, font=self.font_main, fill=(255, 255, 255))

            scale_w = 700
            scale_x = (self.width - scale_w) // 2
            scale_y = 400
            center_x = self.width // 2

            draw.rectangle([scale_x, scale_y, scale_x + scale_w, scale_y + 6], fill=(70, 70, 90))
            draw.rectangle([center_x - 2, scale_y - 40, center_x + 2, scale_y + 40], fill=(0, 255, 255))

            target_str = f"Target: {self.data['target']:.1f} Hz"
            current_str = f"Now: {self.data['current']:.2f} Hz"
            text_y = scale_y + 60

            draw.text((scale_x, text_y), target_str, font=self.font_info, fill=(160, 160, 160))

            w_curr, _ = self._get_text_size(draw, current_str, self.font_info)

            draw.text((scale_x + scale_w - w_curr, text_y), current_str, font=self.font_info, fill=(255, 255, 255))

            is_perfect = abs(self.target_diff) < 1.2
            pointer_color = (0, 255, 120) if is_perfect else (255, 50, 50)
            offset = int(np.clip(self.current_diff * 25, -scale_w//2, scale_w//2))
            px = center_x + offset
            
            draw.polygon([
                (px, scale_y - 10), 
                (px - 25, scale_y - 60),
                (px + 25, scale_y - 60)
            ], fill=pointer_color)
            
        else:
            text = "Waiting..."
            w, h = self._get_text_size(draw, text, self.font_waiting)
            draw.text(((self.width - w)//2, (self.height - h)//2), text, font=self.font_waiting, fill=(50, 50, 70))

        r, g, b = img.split()
        final_img = Image.merge("RGBA", (b, g, r, r))
        self.fb.seek(0)
        self.fb.write(final_img.tobytes())

    def close(self):
        self.running = False
        self.fb.close()
        os.close(self.fd)