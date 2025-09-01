import pygame
import sys
import random
import numpy as np
from pydub import AudioSegment

# ------------------------
# 配置
# ------------------------
WIDTH, HEIGHT = 1920, 1080
FPS = 60
MUSIC_FILE = r"D:\Project\py\音乐烟花\泡沫.mp3"  # 音乐路径
TEXT = "2025，你好！"
TEXT_COLOR = (255, 255, 255)
TEXT_ALPHA = 128
TEXT_FONT_SIZE = 96
TEXT_POS_RATIO = (0.5, 0.25)
MAX_FIREWORKS = 30

THRESHOLD_LARGE = 5.0  # 大烟花振幅阈值
THRESHOLD_SMALL = 1.0  # 小烟花振幅阈值

# ------------------------
# ffmpeg 配置（pydub）
# ------------------------
AudioSegment.converter = r"C:\ffmpeg\bin\ffmpeg.exe"
AudioSegment.ffprobe = r"C:\ffmpeg\bin\ffprobe.exe"

# ------------------------
# 初始化
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

pygame.mixer.init()
pygame.mixer.music.load(MUSIC_FILE)
pygame.mixer.music.play()

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
        if self.size_type == 'large':
            particle_count = 120
            speed_base = 5
        else:
            particle_count = 60
            speed_base = 2

        for _ in range(particle_count):
            angle = random.uniform(0, 2 * np.pi)
            speed = random.uniform(speed_base, speed_base + 5)
            dx = speed * np.cos(angle)
            dy = speed * np.sin(angle)
            color = random.choice([
                (255, 0, 0), (0, 255, 0), (0, 0, 255),
                (255, 255, 0), (255, 0, 255), (0, 255, 255)
            ])
            lifetime = int(random.randint(40, 80) * 1.2)
            size = (2 + self.amp*3)*0.6
            self.particles.append(Particle(self.x, self.y, dx, dy, color, lifetime, size))

    def draw(self, surface):
        if not self.exploded:
            pygame.draw.circle(surface, (255, 255, 255),
                               (int(self.x), int(self.y)),
                               max(3, int(4*self.amp*0.6)))
        else:
            for p in self.particles:
                p.draw(surface)

# ------------------------
# 音乐振幅分析（安全RMS）
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
# 主循环
# ------------------------
fireworks = []
frame_count = 0
running = True

while running and frame_count < TOTAL_FRAMES:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

    screen.fill((0, 0, 0))

    amp = get_amplitude(frame_count)

    # 根据振幅触发烟花
    if amp >= THRESHOLD_LARGE and len(fireworks) < MAX_FIREWORKS:
        fireworks.append(Firework(amp=amp, size_type='large'))
    elif amp >= THRESHOLD_SMALL and len(fireworks) < MAX_FIREWORKS:
        fireworks.append(Firework(amp=amp, size_type='small'))

    for fw in fireworks:
        fw.update()
        fw.draw(screen)
    fireworks = [fw for fw in fireworks if not (fw.exploded and len(fw.particles) == 0)]

    # 绘制文字
    screen.blit(text_surface, text_rect)

    # ------------------------
    # 可视化振幅条（调试用，可注释掉）
    # ------------------------
    #bar_width = WIDTH * 0.6
    #bar_height = 20
    #bar_x = WIDTH*0.2
    #bar_y = HEIGHT - 150
    #amp_norm = min(max(amp * 5, 0.05), 1.0)
    #pygame.draw.rect(screen, (255,0,0), (int(bar_x), int(bar_y), int(bar_width), int(bar_height)))
    #pygame.draw.rect(screen, (50,50,50), (int(bar_x), int(bar_y), int(bar_width*amp_norm), int(bar_height)))

    pygame.display.flip()
    clock.tick(FPS)
    frame_count += 1

pygame.mixer.music.stop()
pygame.quit()
sys.exit()
