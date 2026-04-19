from PIL import Image, ImageDraw, ImageFilter
import math
import time

TILE_MASKS_CACHE = []

def precompute_masks(width, height, render_scale):
    """Генерирует маски плиток один раз"""
    global TILE_MASKS_CACHE
    print("Precomputing masks...")
    
    center_x = width // 2
    center_y = height - (20 * render_scale)
    outer_radius = (width // 2) - (20 * render_scale)
    stone_thickness = 160 * render_scale
    inner_radius = outer_radius - stone_thickness
    
    num_stones = 11
    gap_angle = 1.1 
    angle_per_stone = 180.0 / num_stones
    
    for i in range(num_stones):
        tile_mask = Image.new("L", (width, height), 0)
        tile_draw = ImageDraw.Draw(tile_mask)
        
        start_angle = (180.0 - (i * angle_per_stone)) - (gap_angle / 2.0)
        end_angle = (180.0 - ((i + 1) * angle_per_stone)) + (gap_angle / 2.0)
        
        points = []
        for a in range(int(start_angle * 10), int(end_angle * 10) - 1, -1):
            rad = math.radians(a / 10.0)
            points.append((center_x + outer_radius * math.cos(rad), center_y - outer_radius * math.sin(rad)))
        for a in range(int(end_angle * 10), int(start_angle * 10) + 1):
            rad = math.radians(a / 10.0)
            points.append((center_x + inner_radius * math.cos(rad), center_y - inner_radius * math.sin(rad)))
            
        tile_draw.polygon(points, fill=255)
        
        tile_mask = tile_mask.filter(ImageFilter.MedianFilter(size=9))
        tile_mask = tile_mask.filter(ImageFilter.GaussianBlur(radius=2 * render_scale))
        tile_mask = tile_mask.point(lambda p: 255 if p >= 140 else 0).convert("L")
        
        TILE_MASKS_CACHE.append(tile_mask)

def generate_tuner_arch_fast(active_count=0):
    render_scale = 4
    base_width, base_height = 800, 500
    width, height = base_width * render_scale, base_height * render_scale
    
    bg_color = (255, 255, 255)
    default_stone_color = (215, 215, 215)
    perfect_color = (144, 238, 144)
    palette = [(150, 0, 0), (220, 0, 0), (255, 100, 0), (255, 165, 0), (255, 215, 0), 
               (255, 255, 0), (255, 215, 0), (255, 165, 0), (255, 100, 0), (220, 0, 0), (150, 0, 0)]

    if not TILE_MASKS_CACHE:
        precompute_masks(width, height, render_scale)

    final_img = Image.new("RGB", (width, height), bg_color)
    
    for i in range(len(TILE_MASKS_CACHE)):
        current_color = default_stone_color
        if i < active_count:
            current_color = perfect_color if (i == 5 and active_count == 6) else palette[i]
        
        final_img.paste(current_color, (0, 0), TILE_MASKS_CACHE[i])

    final_output = final_img.resize((base_width, base_height), resample=Image.BILINEAR) 
    return final_output

if __name__ == "__main__":
    st = time.time()
    img = generate_tuner_arch_fast(active_count=7)
    print(f"First run (with precompute): {(time.time() - st):.4f} sec.")

    st = time.time()
    img = generate_tuner_arch_fast(active_count=3)
    print(f"Second run (cached): {(time.time() - st):.4f} sec.")

    st = time.time()
    img = generate_tuner_arch_fast(active_count=5)
    print(f"Second run (cached): {(time.time() - st):.4f} sec.")

    st = time.time()
    img = generate_tuner_arch_fast(active_count=6)
    print(f"Second run (cached): {(time.time() - st):.4f} sec.")

    img.show()