import pygame
import sys
import random
import numpy as np
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from scipy.fft import rfft, rfftfreq

# ------------------------
# 弹窗选择音乐和输入文字
# ------------------------
def choose_music_text():
    root = tk.Tk()
    root.withdraw()
    music_file = filedialog.askopenfilename(title="选择音乐文件", filetypes=[("MP3 Files","*.mp3")])
    if not music_file:
        messagebox.showerror("错误", "未选择音乐文件")
        sys.exit()
    text = simpledialog.askstring("输入文字", "请输入要显示的文字：")
    if text is None:
        messagebox.showerror("错误", "未输入文字")
        sys.exit()
    return music_file, text

MUSIC_FILE, TEXT = choose_music_text()

# ------------------------
# 初始化 Pygame
# ------------------------
pygame.init()
infoObject = pygame.display.Info()
WIDTH, HEIGHT = infoObject.current_w, infoObject.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("音乐雨落")

# ------------------------
# 配置
# ------------------------
FPS = 60
RAIN_COLOR = (192, 192, 192)
TEXT_COLOR = (255, 255, 255)
TEXT_ALPHA = 120
TEXT_FONT_SIZE = 86
TEXT_POS_RATIO = (0.5, 0.25)
MAX_RAIN = 250
MIN_RAIN = 20

# ------------------------
# 字体
# ------------------------
font = pygame.font.SysFont("Microsoft YaHei", TEXT_FONT_SIZE, bold=True)

# ------------------------
# 渐变背景
# ------------------------
def draw_gradient(surface, top_color, bottom_color):
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(top_color[0] * (1-ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1-ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1-ratio) + bottom_color[2] * ratio)
        pygame.draw.line(surface, (r, g, b), (0, y), (WIDTH, y))

# ------------------------
# 雨滴类
# ------------------------
class Raindrop:
    def __init__(self, w, h):
        self.x = random.randint(0, w)
        self.y = random.randint(-h, 0)
        if random.random() < 0.6:
            self.length = random.randint(8, 15)
            self.speed = random.uniform(3, 6)
            self.thickness = 1
        else:
            self.length = random.randint(15, 30)
            self.speed = random.uniform(7, 15)
            self.thickness = 2

    def update(self, h, w, norm_energy, splashes, low_energy, high_energy):
        self.y += self.speed * (1 + norm_energy * 1.5)
        if self.y > h - 60:
            # 调整水花概率：低音多，高音略少
            low_ratio = low_energy / (low_energy + high_energy + 1e-6)
            prob = 0.5 + 0.5 * low_ratio  # 低音比例越高，水花越多
            if random.random() < prob:
                splashes.append(Splash(self.x, h - 60, low_ratio, norm_energy))
            self.y = random.randint(-30, 0)
            # X 坐标根据低/高频分布
            self.x = get_rain_x(low_energy, high_energy, w)

    def draw(self, screen):
        start = (int(self.x), int(self.y))
        end = (int(self.x), int(self.y + self.length))
        pygame.draw.line(screen, RAIN_COLOR, start, end, self.thickness)

# ------------------------
# 水花类
# ------------------------
class Splash:
    def __init__(self, x, y, low_ratio, energy):
        self.x = x
        self.y = y
        # 半径根据低音比例决定，低音时略大，高音时略少
        self.radius = 4 + int(8 * min(1, low_ratio * energy))
        self.max_radius = int(self.radius + 20 + 15 * min(1, low_ratio * energy))
        self.growth = 1.5
        self.alpha = 220
        # 圈数随低音比例调整，低音多圈，高音少圈
        self.rings = random.randint(2, max(2, int(4 * low_ratio)))
        self.ring_offsets = [i*0.25 for i in range(self.rings)]

    def update(self):
        self.radius += self.growth
        self.alpha -= 4
        if self.alpha < 0:
            self.alpha = 0

    def draw(self, screen):
        if self.alpha > 0:
            surface = pygame.Surface((self.max_radius*2, self.max_radius*2), pygame.SRCALPHA)
            for i in range(self.rings):
                radius = int(self.radius * (0.6 + self.ring_offsets[i]))
                if radius < self.max_radius:
                    alpha = max(0, self.alpha - i*30)
                    pygame.draw.circle(surface, (180, 200, 255, alpha), (self.max_radius, self.max_radius), radius, 2)
            screen.blit(surface, (self.x - self.max_radius, self.y - self.max_radius))

    def is_dead(self):
        return self.alpha <= 0

# ------------------------
# 读取音频能量数组
# ------------------------
from pydub import AudioSegment
sound = AudioSegment.from_file(MUSIC_FILE)
samples = np.array(sound.get_array_of_samples())
samples = samples.reshape((-1, sound.channels))
samples = samples.mean(axis=1)
chunk_size = int(sound.frame_rate * 0.05)  # 50ms
energy_array = []
fft_chunks = []
for i in range(0, len(samples), chunk_size):
    chunk = samples[i:i+chunk_size]
    energy_array.append(np.sqrt(np.mean(chunk**2)))
    yf = np.abs(rfft(chunk))
    xf = rfftfreq(len(chunk), 1/sound.frame_rate)
    low_energy = np.sum(yf[(xf>=20)&(xf<=250)])
    high_energy = np.sum(yf[(xf>250)&(xf<=2000)])
    fft_chunks.append((low_energy, high_energy))
energy_array = np.array(energy_array)

# ------------------------
# 获取雨滴x位置：低频集中，高频稀疏
# ------------------------
def get_rain_x(low_energy, high_energy, w):
    ratio = low_energy / (low_energy + high_energy + 1e-6)
    center = int(w * 0.5)
    spread = int(w * (0.2 + 0.5*(1-ratio)))  # 低频集中, spread小，高频稀疏
    return random.randint(max(0, center - spread), min(w, center + spread))

# ------------------------
# 播放音乐
# ------------------------
pygame.mixer.init()
pygame.mixer.music.load(MUSIC_FILE)
pygame.time.wait(1000)  # 缓冲1秒
pygame.mixer.music.play()

# ------------------------
# 主循环
# ------------------------
clock = pygame.time.Clock()
rain = []
splashes = []

smooth_energy = 0
prev_energy = 0
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

    # 播放位置同步
    ms = pygame.mixer.music.get_pos()
    if ms < 0:
        running = False
        break
    chunk_index = int(ms / 50)
    if chunk_index >= len(energy_array):
        norm_energy = 0
        low_energy, high_energy = 0,0
    else:
        norm_energy = energy_array[chunk_index] / 5000
        low_energy, high_energy = fft_chunks[chunk_index]

    smooth_energy = 0.9 * smooth_energy + 0.1 * norm_energy

    # 节拍触发额外雨滴
    if prev_energy > 0 and norm_energy / (prev_energy + 1e-6) > 1.6:
        extra_drops = random.randint(3, 7)
        for _ in range(extra_drops):
            drop = Raindrop(WIDTH, HEIGHT)
            drop.x = get_rain_x(low_energy, high_energy, WIDTH)
            rain.append(drop)
    prev_energy = norm_energy

    # 计算雨滴数量
    target_rain = int(MAX_RAIN * smooth_energy)
    target_rain = max(MIN_RAIN, target_rain)
    while len(rain) < target_rain:
        drop = Raindrop(WIDTH, HEIGHT)
        drop.x = get_rain_x(low_energy, high_energy, WIDTH)
        rain.append(drop)
    if len(rain) > target_rain:
        rain = rain[:target_rain]

    # 更新雨滴和水花
    for drop in rain:
        drop.update(HEIGHT, WIDTH, smooth_energy, splashes, low_energy, high_energy)
    for splash in splashes:
        splash.update()
    splashes = [s for s in splashes if not s.is_dead()]

    # 绘制
    draw_gradient(screen, (10,10,40), (0,0,0))
    for drop in rain:
        drop.draw(screen)
    for splash in splashes:
        splash.draw(screen)

    # 绘制文字
    text_surface = font.render(TEXT, True, TEXT_COLOR)
    text_surface.set_alpha(TEXT_ALPHA)
    rect = text_surface.get_rect(center=(WIDTH*TEXT_POS_RATIO[0], HEIGHT*TEXT_POS_RATIO[1]))
    screen.blit(text_surface, rect)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()
