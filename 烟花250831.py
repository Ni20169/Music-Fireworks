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
MUSIC_FILE = r"E:\Project\烟花250831\泡沫.mp3"
TEXT = "2025，你好！"
TEXT_COLOR = (255, 255, 255)  # 白色
TEXT_ALPHA = 128               # 透明度60%
TEXT_FONT_SIZE = 96           # 字体大小96
TEXT_POS_RATIO = (0.5, 0.25)  # 屏幕相对位置（左右中间，上方1/4）

# ------------------------
# 初始化
# ------------------------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("音乐烟花秀")
clock = pygame.time.Clock()

# 加粗字体
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
        self.size *= 0.96  # 渐隐效果

    def draw(self, surface):
        if self.lifetime > 0:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), max(1,int(self.size)))

class Firework:
    def __init__(self, amp=1.0):
        self.x = random.randint(200, WIDTH - 200)
        self.y = HEIGHT
        self.height = random.randint(400, 800)
        self.exploded = False
        self.particles = []
        self.amp = amp

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
        for _ in range(80):
            angle = random.uniform(0, 2 * np.pi)
            speed = random.uniform(2, 8) + self.amp*2
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
            pygame.draw.circle(surface, (255, 255, 255), (self.x, self.y), max(3,int(4*self.amp*0.6)))
        else:
            for p in self.particles:
                p.draw(surface)

# ------------------------
# 音乐振幅分析
# ------------------------
audio = AudioSegment.from_mp3(MUSIC_FILE)
samples = np.array(audio.get_array_of_samples())
if audio.channels > 1:
    samples = samples.reshape((-1, audio.channels))
left_channel = samples[:,0]

def get_amplitude(frame):
    start = int(frame*1024)
    end = start + 1024
    if end >= len(left_channel):
        end = len(left_channel)-1
    return np.abs(left_channel[start:end]).mean()/1000

# ------------------------
# 主循环
# ------------------------
fireworks = []
frame_count = 0
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

    screen.fill((0, 0, 0))

    amp = get_amplitude(frame_count)

    # 创建烟花
    if random.random() < min(0.05 + amp/50, 0.2):
        fireworks.append(Firework(amp=amp))

    # 更新绘制烟花
    for fw in fireworks:
        fw.update()
        fw.draw(screen)
    fireworks = [fw for fw in fireworks if not (fw.exploded and len(fw.particles)==0)]

    # 绘制文字
    screen.blit(text_surface, text_rect)

    pygame.display.flip()
    clock.tick(FPS)
    frame_count += 1

pygame.mixer.music.stop()
pygame.quit()
sys.exit()
