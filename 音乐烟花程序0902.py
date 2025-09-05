import pygame
import sys
import os
import random
import numpy as np
import time
import threading
import ctypes
import pygame
from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio
import tkinter as tk
from tkinter import Tk, filedialog, simpledialog

# ------------------------
# 兼容 PyInstaller 打包后的 ffmpeg 路径
# ------------------------
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.abspath(".")

ffmpeg_path = os.path.join(base_path, "ffmpeg", "bin", "ffmpeg.exe")
ffprobe_path = os.path.join(base_path, "ffmpeg", "bin", "ffprobe.exe")

AudioSegment.converter = ffmpeg_path
AudioSegment.ffprobe = ffprobe_path

# ------------------------
# 弹窗选择音乐和输入文字
# ------------------------
def choose_music_text():
    root = tk.Tk()
    root.withdraw()
    music_file = filedialog.askopenfilename(title="选择音乐文件", filetypes=[("MP3 Files","*.mp3")])
    if not music_file:
        messagebox.showerror("错误","未选择音乐文件")
        sys.exit()
    text = simpledialog.askstring("输入文字","请输入要显示的文字：")
    if text is None:
        messagebox.showerror("错误","未输入文字")
        sys.exit()
    return music_file, text

MUSIC_FILE, TEXT = choose_music_text()



# 强制 DPI 感知（防止 Windows 缩放影响）
try:
    ctypes.windll.user32.SetProcessDPIAware()
except:
    pass

pygame.init()
infoObject = pygame.display.Info()
WIDTH, HEIGHT = infoObject.current_w, infoObject.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT))
# ------------------------
# 配置
# ------------------------
WIDTH, HEIGHT = 1920, 1080
FPS = 60
MUSIC_FILE = MUSIC_FILE
TEXT = TEXT
TEXT_COLOR = (255, 255, 255)
TEXT_ALPHA = 100
TEXT_FONT_SIZE = 126
TEXT_POS_RATIO = (0.5, 0.25)
MAX_FIREWORKS = 30

THRESHOLD_LARGE = 5.0
THRESHOLD_SMALL = 1.0

# ------------------------
# 播放音乐（延迟 0.1 秒）
# ------------------------
def play_audio():
    time.sleep(0.02)
    sound = AudioSegment.from_file(MUSIC_FILE)
    _play_with_simpleaudio(sound).wait_done()
    pygame.event.post(pygame.event.Event(pygame.QUIT))  # 音乐结束 → 退出

threading.Thread(target=play_audio, daemon=True).start()

# ------------------------
# 初始化 Pygame
# ------------------------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("音乐烟花秀")
clock = pygame.time.Clock()

font = pygame.font.SysFont("Microsoft YaHei", TEXT_FONT_SIZE, bold=True)
text_surface = font.render(TEXT, True, TEXT_COLOR)
text_surface = text_surface.convert_alpha()
text_surface.set_alpha(TEXT_ALPHA)
text_rect = text_surface.get_rect(center=(int(WIDTH*TEXT_POS_RATIO[0]), int(HEIGHT*TEXT_POS_RATIO[1])))

# ------------------------
# 烟花类
# ------------------------
class Particle:
    def __init__(self, x, y, dx, dy, color, lifetime, size):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.color = color
        self.lifetime = lifetime
        self.size = size

    def update(self):
        self.x += self.dx
        self.y += self.dy
        self.dy += 0.05
        self.lifetime -= 1
        self.size *= 0.96

    def draw(self, surface):
        if self.lifetime > 0:
            pygame.draw.circle(surface, self.color,
                               (int(self.x), int(self.y)),
                               max(1, int(self.size)))

class Firework:
    def __init__(self, amp=1.0, size_type='small'):
        self.x = random.randint(200, WIDTH - 200)
        self.y = HEIGHT
        self.height = random.randint(400, 800)
        self.exploded = False
        self.particles = []
        self.amp = amp
        self.size_type = size_type

    def update(self):
        if not self.exploded:
            self.y -= 10 + self.amp*5
            if self.y <= self.height:
                self.explode()
        else:
            for p in self.particles:
                p.update()
            self.particles = [p for p in self.particles if p.lifetime > 0]

    def explode(self):
        self.exploded = True
        particle_count = 120 if self.size_type=='large' else 60
        speed_base = 5 if self.size_type=='large' else 2
        for _ in range(particle_count):
            angle = random.uniform(0, 2 * np.pi)
            speed = random.uniform(speed_base, speed_base + 5)
            dx = speed * np.cos(angle)
            dy = speed * np.sin(angle)
            color = random.choice([
                (255,0,0),(0,255,0),(0,0,255),
                (255,255,0),(255,0,255),(0,255,255)
            ])
            lifetime = int(random.randint(40,80) * 1.2)
            size = (2 + self.amp*3)*0.6
            self.particles.append(Particle(self.x, self.y, dx, dy, color, lifetime, size))

    def draw(self, surface):
        if not self.exploded:
            pygame.draw.circle(surface, (255,255,255),(int(self.x), int(self.y)), max(3,int(4*self.amp*0.6)))
        else:
            for p in self.particles:
                p.draw(surface)

# ------------------------
# 音乐振幅分析（用 pydub）
# ------------------------
audio = AudioSegment.from_mp3(MUSIC_FILE)
samples = np.array(audio.get_array_of_samples())
if audio.channels > 1:
    samples = samples.reshape((-1, audio.channels))
left_channel = samples[:,0]

SAMPLES_PER_FRAME = int(audio.frame_rate / FPS)
TOTAL_FRAMES = int(len(left_channel) / SAMPLES_PER_FRAME)

def get_amplitude(frame):
    start = frame * SAMPLES_PER_FRAME
    end = start + SAMPLES_PER_FRAME
    if start >= len(left_channel):
        return 0
    end = min(end, len(left_channel))
    slice_data = left_channel[start:end]
    if slice_data.size == 0:
        return 0
    slice_data = slice_data.astype(np.float32)
    mean_sq = np.mean(slice_data**2)
    if mean_sq <= 0:
        return 0
    return np.sqrt(mean_sq) / 1000

# ------------------------
# 主循环（同步：逐帧推进）
# ------------------------
fireworks = []
frame_count = 0
running = True
fullscreen = False

while running and frame_count < TOTAL_FRAMES:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:  # ESC 退出
                running = False
            elif event.key == pygame.K_RETURN:  # 回车切换全屏
                fullscreen = not fullscreen
                if fullscreen:
                    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                else:
                    screen = pygame.display.set_mode((WIDTH, HEIGHT))

    screen.fill((0,0,0))

    amp = get_amplitude(frame_count)

    if amp >= THRESHOLD_LARGE and len(fireworks) < MAX_FIREWORKS:
        fireworks.append(Firework(amp=amp, size_type='large'))
    elif amp >= THRESHOLD_SMALL and len(fireworks) < MAX_FIREWORKS:
        fireworks.append(Firework(amp=amp, size_type='small'))

    for fw in fireworks:
        fw.update()
        fw.draw(screen)
    fireworks = [fw for fw in fireworks if not (fw.exploded and len(fw.particles)==0)]

    screen.blit(text_surface, text_rect)
    pygame.display.flip()
    clock.tick(FPS)
    frame_count += 1

pygame.quit()
sys.exit()
