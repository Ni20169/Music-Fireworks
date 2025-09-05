import pygame
import sys
import random
import math
import numpy as np
import tkinter as tk
from tkinter import filedialog, simpledialog
from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio
import threading
import time
import wave

# ------------------------ 弹窗选择音乐和输入文字 ------------------------
def choose_music_text():
    root = tk.Tk()
    root.withdraw()
    music_file = filedialog.askopenfilename(title="选择音乐文件", filetypes=[("MP3/ WAV Files","*.mp3;*.wav")])
    if not music_file:
        sys.exit("未选择音乐文件")
    text = simpledialog.askstring("输入文字","请输入要显示的文字：")
    if text is None:
        sys.exit("未输入文字")
    return music_file, text

MUSIC_FILE, TEXT = choose_music_text()

# ------------------------ Pygame 初始化 ------------------------
pygame.init()
infoObject = pygame.display.Info()
WIDTH, HEIGHT = infoObject.current_w, infoObject.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("音乐雪花堆积")
clock = pygame.time.Clock()
FPS = 60

font_size = 126
font = pygame.font.SysFont("Microsoft YaHei", font_size, bold=True)

# ------------------------ 雪花类 ------------------------
class Snowflake:
    def __init__(self, w, h, norm_energy_low, norm_energy_high, snow_layer, layer_override=None):
        # 雪花层：0远景 1中景 2近景 3超近景
        if layer_override is not None:
            self.layer = layer_override
        else:
            if norm_energy_high > 0.95:
                weights = [0.1, 0.15, 0.2, 0.05]  # 高音量时大雪花概率增加
            else:
                weights = [0.2, 0.2, 0.25, 0.03]
            self.layer = random.choices([0,1,2,3], weights=weights)[0]

        self.snow_layer = snow_layer

        if self.layer == 0:
            self.size = random.randint(1,2)
            self.base_speed = random.uniform(0.8,1.3)
            self.brightness = random.randint(10,50)
        elif self.layer == 1:
            self.size = random.randint(2,6)
            self.base_speed = random.uniform(1.6,1.8)
            self.brightness = random.randint(50,150)
        elif self.layer == 2:
            self.size = random.randint(8,12)
            self.base_speed = random.uniform(1.8,2.8)
            self.brightness = random.randint(150,230)
        else:
            self.size = random.randint(14,20)
            self.base_speed = random.uniform(3.0,4.0)
            self.brightness = random.randint(220,255)

        self.x = random.randint(0, w-1)
        self.y = random.randint(-h//2, 0)
        self.offset = random.uniform(-0.05,0.05)
        self.angle = random.uniform(0,360)
        self.fixed = False
        self.surface = self.create_surface()

    def create_surface(self):
        surf_size = self.size*3
        surf = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
        center = surf_size // 2
        pygame.draw.circle(surf, (self.brightness,self.brightness,self.brightness),
                           (center, center), max(1,int(self.size*0.3)))
        for i in range(6):
            angle = i*np.pi/3
            length = self.size*0.4 + random.uniform(0,1)
            x2 = center + length*np.cos(angle)
            y2 = center + length*np.sin(angle)
            pygame.draw.line(surf, (self.brightness,self.brightness,self.brightness),
                             (center, center), (x2, y2), 1)
        return pygame.transform.rotate(surf, self.angle)

    def update(self, norm_energy_low, norm_energy_high):
        if self.fixed:
            return
        speed_factor = 1 + 0.2 * norm_energy_high
        self.y += self.base_speed * speed_factor
        self.x += self.offset
        self.offset += random.uniform(-0.005,0.005)
        self.offset = max(-0.05, min(0.05, self.offset))
        if self.x < 0: self.x = WIDTH-1
        if self.x >= WIDTH: self.x = 0

        x_int = int(self.x)
        if self.y >= HEIGHT - self.snow_layer[x_int]:
            self.fixed = True
            self.y = HEIGHT - self.snow_layer[x_int] - self.size//2
            self.snow_layer[x_int] += self.size

        decay = 0.02 if self.layer>=2 else 0.05
        self.brightness = max(100, self.brightness - decay)
        self.surface = self.create_surface()

    def draw(self, screen):
        rect = self.surface.get_rect(center=(self.x,self.y))
        screen.blit(self.surface, rect)

# 雪人晃动参数
snowman_amplitude = 5     # 晃动幅度（像素）
snowman_speed = 2         # 晃动速度（弧度/s）

def draw_snowman(screen, offset_x=0):
    """在右下角绘制雪人，offset_x为水平偏移量"""
    x = WIDTH - 100 + offset_x
    y = HEIGHT - 100

    # 身体
    pygame.draw.circle(screen, (255, 255, 255), (x, y + 60), 30)
    pygame.draw.circle(screen, (255, 255, 255), (x, y + 30), 25)
    pygame.draw.circle(screen, (255, 255, 255), (x, y), 20)

    # 眼睛
    pygame.draw.circle(screen, (0, 0, 0), (x - 7, y - 2), 3)
    pygame.draw.circle(screen, (0, 0, 0), (x + 7, y - 2), 3)

    # 嘴巴
    for i in range(-2, 3):
        pygame.draw.circle(screen, (255, 165, 0), (x + i*3, y + 7), 2)

    # 手臂
    pygame.draw.line(screen, (139, 69, 19), (x - 25, y + 30), (x - 45, y + 15), 3)
    pygame.draw.line(screen, (139, 69, 19), (x + 25, y + 30), (x + 45, y + 15), 3)

    # 围巾
    pygame.draw.rect(screen, (255, 0, 0), (x - 20, y + 10, 40, 5))

# ------------------------ 音乐播放和能量分析 ------------------------
def play_music_and_analyze(filename):
    sound = AudioSegment.from_file(filename)
    _play_with_simpleaudio(sound)
    if filename.lower().endswith(".mp3"):
        wav_file = filename.replace(".mp3",".wav")
        sound.export(wav_file, format="wav")
    else:
        wav_file = filename
    wf = wave.open(wav_file,'rb')
    frame_rate = wf.getframerate()
    n_frames = wf.getnframes()
    raw_data = wf.readframes(n_frames)
    wf.close()
    data = np.frombuffer(raw_data, dtype=np.int16)
    if sound.channels>1:
        data = data[::sound.channels]
    return data, frame_rate

audio_data, frame_rate = play_music_and_analyze(MUSIC_FILE)
start_time = time.time()

# ------------------------ 堆积层 ------------------------
snow_layer = [0 for _ in range(WIDTH)]
snowflakes = []

# ------------------------ 主循环 ------------------------
running = True
while running:
    # 背景渐变 夜空黑底
    for i in range(HEIGHT):
        ratio = i/HEIGHT
        r = int(10*(1-ratio) + 0*ratio)
        g = int(10*(1-ratio) + 0*ratio)
        b = int(40*(1-ratio) + 0*ratio)
        pygame.draw.line(screen, (r,g,b), (0,i), (WIDTH,i))

    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE):
            running = False

    # 音乐能量分析
    t = time.time() - start_time
    idx = min(int(t*frame_rate), len(audio_data)-1)
    window = audio_data[idx:min(idx+1024,len(audio_data))]
    if len(window)==0: norm_energy_low = norm_energy_high = 0
    else:
        fft = np.fft.rfft(window)
        freq = np.fft.rfftfreq(len(window), d=1/frame_rate)
        low_mask = (freq<400)
        high_mask = (freq>=400)
        norm_energy_low = np.abs(fft[low_mask]).mean()/1e4
        norm_energy_high = np.abs(fft[high_mask]).mean()/1e4
        norm_energy_low = min(norm_energy_low,1.0)
        norm_energy_high = min(norm_energy_high,1.0)

    # ------------------------ 生成雪花 ------------------------
    new_flakes = max(1, int(norm_energy_high*0.05))
    for _ in range(new_flakes):
        snowflakes.append(Snowflake(WIDTH, HEIGHT, norm_energy_low, norm_energy_high, snow_layer))
    if norm_energy_high > 0.95 and random.random() < 0.001:
        snowflakes.append(Snowflake(WIDTH, HEIGHT, norm_energy_low, norm_energy_high, snow_layer, layer_override=3))

    # ------------------------ 更新雪花 ------------------------
    for s in snowflakes:
        s.update(norm_energy_low, norm_energy_high)

    # ------------------------ 绘制雪花 ------------------------
    for s in snowflakes:
        s.draw(screen)

    # ------------------------ 绘制文字 ------------------------
    text_surface = font.render(TEXT, True, (255,255,255))
    screen.blit(text_surface, (WIDTH*0.5 - text_surface.get_width()/2, HEIGHT*0.25))

    # 计算雪人水平偏移（正弦晃动）
    #elapsed = time.time() - start_time
    #offset = snowman_amplitude * math.sin(elapsed * snowman_speed)

    # 绘制雪人
    draw_snowman(screen, offset_x=0)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()
