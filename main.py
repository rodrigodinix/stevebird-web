import pygame
import random
import asyncio
import sys
import json
import platform

# Configurações
WIDTH, HEIGHT = 400, 600
FPS = 60
BASE_GAP = 150
MIN_GAP = 100
PIPE_SPEED = 3.5
GRAVITY = 0.4
JUMP_FORCE = -7

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Steve Bird - Versão Otimizada")
clock = pygame.time.Clock()

class GameAssets:
    def __init__(self):
        self.images = {}
        self.sounds = {}
    
    async def load(self):
        await asyncio.gather(
            self._load_image("background.png"),
            self._load_image("steve.png", scale=0.8),
            self._load_image("pipe.png"),
            self._load_sound("jump.wav"),
            self._load_sound("score.wav"),
            self._load_sound("game_over.wav")
        )
    
    async def _load_image(self, filename, scale=1):
        try:
            image = pygame.image.load(f"assets/{filename}").convert_alpha()
            if scale != 1:
                size = image.get_size()
                image = pygame.transform.scale(image, (int(size[0]*scale), int(size[1]*scale)))
            self.images[filename.split('.')[0]] = image
        except Exception as e:
            print(f"Erro ao carregar {filename}: {e}")
            surf = pygame.Surface((50, 50), pygame.SRCALPHA)
            color = (255,0,0) if "steve" in filename else (0,255,0)
            pygame.draw.rect(surf, color, (0,0,50,50))
            self.images[filename.split('.')[0]] = surf
    
    async def _load_sound(self, filename):
        try:
            self.sounds[filename.split('.')[0]] = pygame.mixer.Sound(f"assets/{filename}")
        except:
            print(f"Erro ao carregar som {filename}")
            self.sounds[filename.split('.')[0]] = None

class Player:
    def __init__(self, image):
        self.image = image
        self.rect = self.image.get_rect(center=(100, HEIGHT//2))
        self.velocity = 0
        self.gravity = GRAVITY
        self.jump_power = JUMP_FORCE
    
    def update(self):
        self.velocity += self.gravity
        self.rect.y += self.velocity

    def check_out_of_bounds(self):
        return self.rect.bottom >= HEIGHT or self.rect.top <= -50

    def jump(self, sound):
        self.velocity = self.jump_power
        if sound:
            sound.play()
    
    def draw(self, surface):
        surface.blit(self.image, self.rect)

class PipeSystem:
    def __init__(self, pipe_image):
        self.pipe_image = pipe_image
        self.pipes = []
        self.gap = BASE_GAP
        self.speed = PIPE_SPEED
        self.score = 0
        self.last_pipe_time = 0
        self.pipe_frequency = 1800
    
    def update(self, current_time, player_rect):
        self.gap = max(MIN_GAP, BASE_GAP - (self.score // 5))
        if current_time - self.last_pipe_time > self.pipe_frequency:
            self._add_pipe()
            self.last_pipe_time = current_time
            self.pipe_frequency = max(1200, 1800 - (self.score * 10))
        
        for pipe in self.pipes[:]:
            pipe['x'] -= self.speed
            if not pipe['scored'] and pipe['x'] + 50 < player_rect.left:
                pipe['scored'] = True
                self.score += 1
                if assets.sounds.get('score'):
                    assets.sounds['score'].play()
            if pipe['x'] < -100:
                self.pipes.remove(pipe)
    
    def _add_pipe(self):
        height = random.randint(int(HEIGHT * 0.2), int(HEIGHT * 0.65))
        self.pipes.append({
            'x': WIDTH,
            'top_height': height,
            'bottom_height': height + self.gap,
            'scored': False
        })
    
    def check_collision(self, player_rect):
        for pipe in self.pipes:
            top_rect = pygame.Rect(pipe['x'], 0, self.pipe_image.get_width(), pipe['top_height'])
            bottom_rect = pygame.Rect(pipe['x'], pipe['bottom_height'], self.pipe_image.get_width(), HEIGHT - pipe['bottom_height'])
            if player_rect.colliderect(top_rect) or player_rect.colliderect(bottom_rect):
                if assets.sounds.get('game_over'):
                    assets.sounds['game_over'].play()
                return True
        return False
    
    def draw(self, surface):
        for pipe in self.pipes:
            top_pipe = pygame.transform.flip(self.pipe_image, False, True)
            surface.blit(top_pipe, (pipe['x'], pipe['top_height'] - top_pipe.get_height()))
            surface.blit(self.pipe_image, (pipe['x'], pipe['bottom_height']))

def get_rankings(current_score):
    rankings = []
    try:
        if platform.system() == "Emscripten":
            import js
            stored = js.window.localStorage.getItem("steve_bird_scores")
            if stored:
                rankings = json.loads(stored)
    except Exception as e:
        print("Erro ao carregar rankings:", e)

    rankings.append(current_score)
    rankings.sort(reverse=True)
    rankings = rankings[:100]

    try:
        if platform.system() == "Emscripten":
            import js
            js.window.localStorage.setItem("steve_bird_scores", json.dumps(rankings))
    except Exception as e:
        print("Erro ao salvar rankings:", e)

    current_position = rankings.index(current_score) + 1
    top_3 = rankings[:3]
    return current_position, top_3

async def game_loop():
    global assets
    player = Player(assets.images['steve'])
    pipes = PipeSystem(assets.images['pipe'])
    background = assets.images['background']
    game_active = True
    last_time = pygame.time.get_ticks()
    
    while game_active:
        current_time = pygame.time.get_ticks()
        last_time = current_time

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                player.jump(assets.sounds.get('jump'))
            if event.type == pygame.MOUSEBUTTONDOWN:
                player.jump(assets.sounds.get('jump'))

        player.update()
        pipes.update(current_time, player.rect)

        if pipes.check_collision(player.rect) or player.check_out_of_bounds():
            if assets.sounds.get('game_over'):
                assets.sounds['game_over'].play()
            await game_over_screen(pipes.score)
            return True
        
        screen.blit(background, (0, 0))
        pipes.draw(screen)
        player.draw(screen)

        font = pygame.font.SysFont("Arial", 36, bold=True)
        score_text = font.render(str(pipes.score), True, (255, 255, 255))
        screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, 50))
        
        draw_watermark()
        pygame.display.flip()
        await asyncio.sleep(0)
        clock.tick(FPS)
    
    return True

async def show_menu():
    background = assets.images['background']
    title_font = pygame.font.SysFont("Arial", 48, bold=True)
    start_font = pygame.font.SysFont("Arial", 24)
    
    while True:
        screen.blit(background, (0, 0))
        
        # Título
        title = title_font.render("STEVE BIRD", True, (255, 215, 0))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))
        
        # Primeira linha do texto de instrução
        line1 = start_font.render("Pressione ESPAÇO ou", True, (255, 255, 255))
        screen.blit(line1, (WIDTH // 2 - line1.get_width() // 2, 300))
        
        # Segunda linha do texto de instrução
        line2 = start_font.render("toque na tela para começar", True, (255, 255, 255))
        screen.blit(line2, (WIDTH // 2 - line2.get_width() // 2, 330))

        draw_watermark()
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                return True
            if event.type == pygame.MOUSEBUTTONDOWN:
                return True
        
        await asyncio.sleep(0)


async def game_over_screen(score):
    position, top3 = get_rankings(score)
    font_big = pygame.font.SysFont("Arial", 48, bold=True)
    font = pygame.font.SysFont("Arial", 28)
    small = pygame.font.SysFont("Arial", 20)
    background = assets.images['background']
    
    while True:
        screen.blit(background, (0, 0))
        screen.blit(font_big.render("Game Over", True, (255, 0, 0)), (WIDTH//2 - 120, 100))
        screen.blit(font.render(f"Seu Score: {score}", True, (255, 255, 255)), (WIDTH//2 - 100, 200))

        for i, score_val in enumerate(top3):
            screen.blit(small.render(f"Top {i + 1}: {score_val}", True, (255, 255, 255)), (WIDTH//2 - 80, 250 + 30*i))
        
        screen.blit(small.render(f"Sua posição: {position}", True, (255, 255, 255)), (WIDTH//2 - 80, 350))

        draw_watermark()
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                return
        
        await asyncio.sleep(0)

def draw_watermark():
    watermark_text = "Feito por Rodrigo D. Barbaceli e Alana O. Barbaceli"
    watermark_font = pygame.font.SysFont("Arial", 14)
    watermark_surface = watermark_font.render(watermark_text, True, (255, 255, 255))
    screen.blit(watermark_surface, (WIDTH // 2 - watermark_surface.get_width() // 2, HEIGHT - 30))

async def main():
    global assets
    assets = GameAssets()
    await assets.load()
    
    menu_result = await show_menu()
    if menu_result:
        game_loop()

    while True:
        start = await show_menu()
        if not start:
            break
        again = await game_loop()
        if not again:
            break

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except:
        pygame.quit()
        sys.exit()
