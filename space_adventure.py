"""
space_adventure.py
A self-contained 2D arcade-style space shooter using pygame.

Features:
- Player ship (rotation + thrust + inertia)
- Enemies with simple AI (seek, wander)
- Bullets, collisions, score, levels
- Power-ups: rapid-fire and shield
- Particle explosions, HUD, pause, restart

Run:
    pip install pygame
    python space_adventure.py
"""

import math
import random
import sys
import time
from collections import deque

import pygame

# ---------- Configuration ----------
SCREEN_WIDTH = 900
SCREEN_HEIGHT = 600
FPS = 60

PLAYER_MAX_SPEED = 6.0
PLAYER_ACCEL = 0.25
PLAYER_ROT_SPEED = 4  # degrees per frame
BULLET_SPEED = 12
BULLET_LIFETIME = 1.8  # seconds
ENEMY_SPAWN_INTERVAL = 2.0  # seconds (will scale)
PARTICLE_LIFETIME = 0.8

FONT_NAME = None  # default pygame font

# ---------- Utility functions ----------
def vec_from_angle(angle_degrees):
    rad = math.radians(angle_degrees)
    return pygame.math.Vector2(math.cos(rad), math.sin(rad))

def clamp(x, a, b):
    return max(a, min(b, x))

# ---------- Particle ----------
class Particle:
    def __init__(self, pos, vel, size, lifetime, surface):
        self.pos = pygame.math.Vector2(pos)
        self.vel = pygame.math.Vector2(vel)
        self.size = size
        self.lifetime = lifetime
        self.age = 0.0
        self.surface = surface

    def update(self, dt):
        self.age += dt
        self.pos += self.vel * dt
        # gravity-like fade
        self.vel *= 0.98

    def draw(self, screen):
        alpha = clamp(int(255 * (1 - self.age / self.lifetime)), 0, 255)
        if alpha == 0:
            return
        surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (255, 160, 0, alpha), (self.size, self.size), int(self.size))
        screen.blit(surf, (self.pos.x - self.size, self.pos.y - self.size))

    def alive(self):
        return self.age < self.lifetime

# ---------- Bullet ----------
class Bullet:
    def __init__(self, pos, vel, owner, created_time):
        self.pos = pygame.math.Vector2(pos)
        self.vel = pygame.math.Vector2(vel)
        self.radius = 3 if owner == "player" else 6
        self.owner = owner
        self.created_time = created_time

    def update(self, dt):
        self.pos += self.vel * dt

    def draw(self, screen):
        color = (50, 255, 50) if self.owner == "player" else (255, 60, 60)
        pygame.draw.circle(screen, color, (int(self.pos.x), int(self.pos.y)), self.radius)

    def alive(self, now):
        return (now - self.created_time) < BULLET_LIFETIME and 0 <= self.pos.x <= SCREEN_WIDTH and 0 <= self.pos.y <= SCREEN_HEIGHT

# ---------- Player ----------
class Player:
    def __init__(self, pos):
        self.pos = pygame.math.Vector2(pos)
        self.vel = pygame.math.Vector2(0, 0)
        self.angle = -90  # facing up
        self.radius = 18
        self.health = 100
        self.max_health = 100
        self.lives = 3
        self.last_shot = 0.0
        self.fire_delay = 0.22
        self.rapid_fire_time = 0.0
        self.shield_time = 0.0

    def update(self, dt, keys):
        # Rotation
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.angle -= PLAYER_ROT_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.angle += PLAYER_ROT_SPEED

        # Thrust
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            thrust = vec_from_angle(self.angle) * PLAYER_ACCEL
            self.vel += thrust

        # Braking
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.vel *= 0.96

        # Clamp speed
        if self.vel.length() > PLAYER_MAX_SPEED:
            self.vel.scale_to_length(PLAYER_MAX_SPEED)

        # Position update
        self.pos += self.vel

        # Wrap around edges
        if self.pos.x < -self.radius:
            self.pos.x = SCREEN_WIDTH + self.radius
        elif self.pos.x > SCREEN_WIDTH + self.radius:
            self.pos.x = -self.radius
        if self.pos.y < -self.radius:
            self.pos.y = SCREEN_HEIGHT + self.radius
        elif self.pos.y > SCREEN_HEIGHT + self.radius:
            self.pos.y = -self.radius

        # timers
        if self.rapid_fire_time > 0:
            self.rapid_fire_time = max(0, self.rapid_fire_time - dt)
            self.fire_delay = 0.08
        else:
            self.fire_delay = 0.22

        if self.shield_time > 0:
            self.shield_time = max(0, self.shield_time - dt)

    def draw(self, screen):
        # Ship body (triangle)
        dir_vec = vec_from_angle(self.angle)
        left = vec_from_angle(self.angle - 140) * 14
        right = vec_from_angle(self.angle + 140) * 14
        p1 = (int(self.pos.x + dir_vec.x * 20), int(self.pos.y + dir_vec.y * 20))
        p2 = (int(self.pos.x + left.x), int(self.pos.y + left.y))
        p3 = (int(self.pos.x + right.x), int(self.pos.y + right.y))
        pygame.draw.polygon(screen, (160, 220, 255), [p1, p2, p3])
        pygame.draw.polygon(screen, (20, 20, 60), [p1, p2, p3], 2)

        # Shield visual
        if self.shield_time > 0:
            r = int(self.radius + 6 * math.sin(time.time() * 8))
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (100, 150, 255, 120), (r, r), r)
            screen.blit(surf, (self.pos.x - r, self.pos.y - r))

# ---------- Enemy ----------
class Enemy:
    def __init__(self, pos, etype="basic"):
        self.pos = pygame.math.Vector2(pos)
        self.vel = pygame.math.Vector2(0, 0)
        self.radius = 14 if etype == "basic" else 22
        self.etype = etype
        self.health = 20 if etype == "basic" else 45
        self.angle = 0
        self.wander_timer = random.uniform(0.3, 1.5)

    def update(self, dt, player_pos):
        # Simple AI: either seek player or wander
        self.wander_timer -= dt
        if self.etype == "basic":
            # Seek player slowly
            dir_to_player = (player_pos - self.pos)
            if dir_to_player.length() > 0.1:
                dir_to_player.scale_to_length(0.9)
                self.vel += dir_to_player * dt
            # slight drag
            self.vel *= 0.98
        else:
            # Larger enemy: wander and occasionally dash
            if self.wander_timer <= 0:
                self.wander_timer = random.uniform(0.5, 2.0)
                angle = random.uniform(0, 360)
                self.vel = vec_from_angle(angle) * random.uniform(0.6, 2.0)
            # occasionally dash toward player
            if random.random() < 0.002:
                dir_to_player = (player_pos - self.pos)
                if dir_to_player.length() > 0:
                    dir_to_player.scale_to_length(3.5)
                    self.vel += dir_to_player

        self.pos += self.vel

        # keep within bounds
        self.pos.x = clamp(self.pos.x, -50, SCREEN_WIDTH + 50)
        self.pos.y = clamp(self.pos.y, -50, SCREEN_HEIGHT + 50)

    def draw(self, screen):
        if self.etype == "basic":
            pygame.draw.circle(screen, (255, 100, 100), (int(self.pos.x), int(self.pos.y)), self.radius)
            pygame.draw.circle(screen, (120, 40, 40), (int(self.pos.x), int(self.pos.y)), self.radius, 2)
        else:
            # draw a spiky larger enemy
            points = []
            spikes = 8
            for i in range(spikes * 2):
                r = self.radius if i % 2 == 0 else self.radius - 6
                ang = i * (360 / (spikes * 2))
                v = vec_from_angle(ang) * r
                points.append((int(self.pos.x + v.x), int(self.pos.y + v.y)))
            pygame.draw.polygon(screen, (255, 160, 80), points)
            pygame.draw.polygon(screen, (120, 60, 20), points, 2)

# ---------- PowerUp ----------
class PowerUp:
    def __init__(self, pos, ptype):
        self.pos = pygame.math.Vector2(pos)
        self.ptype = ptype
        self.radius = 10
        self.duration = 6.0 if ptype == "rapid" else 5.0
        self.collected = False

    def update(self, dt):
        pass

    def draw(self, screen):
        if self.ptype == "rapid":
            color = (100, 255, 180)
        else:
            color = (120, 180, 255)
        pygame.draw.circle(screen, color, (int(self.pos.x), int(self.pos.y)), self.radius)
        pygame.draw.circle(screen, (20, 20, 40), (int(self.pos.x), int(self.pos.y)), self.radius, 2)

# ---------- HUD ----------
class HUD:
    def __init__(self, game):
        self.game = game
        self.font = pygame.font.Font(FONT_NAME, 20)
        self.large = pygame.font.Font(FONT_NAME, 36)

    def draw(self, screen):
        g = self.game
        # Score and level
        score_surf = self.font.render(f"Score: {g.score}", True, (235, 235, 240))
        level_surf = self.font.render(f"Level: {g.level}", True, (235, 235, 240))
        screen.blit(score_surf, (10, 8))
        screen.blit(level_surf, (10, 32))

        # Lives
        lives_surf = self.font.render(f"Lives: {g.player.lives}", True, (235, 235, 240))
        screen.blit(lives_surf, (SCREEN_WIDTH - 110, 8))

        # Health bar
        bar_w = 200
        x = (SCREEN_WIDTH - bar_w) // 2
        y = 8
        ratio = clamp(g.player.health / g.player.max_health, 0, 1)
        pygame.draw.rect(screen, (60, 60, 60), (x, y, bar_w, 18))
        pygame.draw.rect(screen, (60, 220, 100), (x + 2, y + 2, int((bar_w - 4) * ratio), 14))
        hp_text = self.font.render(f"HP: {int(g.player.health)}", True, (20, 20, 20))
        screen.blit(hp_text, (x + bar_w // 2 - hp_text.get_width() // 2, y))

        # powerups
        if g.player.rapid_fire_time > 0:
            rf = self.font.render(f"Rapid Fire: {int(g.player.rapid_fire_time)}s", True, (200, 255, 200))
            screen.blit(rf, (10, SCREEN_HEIGHT - 28))
        if g.player.shield_time > 0:
            sh = self.font.render(f"Shield: {int(g.player.shield_time)}s", True, (200, 220, 255))
            screen.blit(sh, (10, SCREEN_HEIGHT - 52))

        # paused or game over text
        if g.paused:
            text = self.large.render("PAUSED", True, (240, 240, 240))
            screen.blit(text, ((SCREEN_WIDTH - text.get_width()) // 2, (SCREEN_HEIGHT - text.get_height()) // 2))
        if g.game_over:
            text = self.large.render("GAME OVER - Press R to Restart", True, (255, 180, 180))
            screen.blit(text, ((SCREEN_WIDTH - text.get_width()) // 2, SCREEN_HEIGHT // 2 - 30))

# ---------- Game ----------
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Space Adventure")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(FONT_NAME, 18)

        self.reset()

    def reset(self):
        self.player = Player((SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
        self.bullets = []
        self.enemies = []
        self.particles = []
        self.powerups = []
        self.spawn_timer = 0.0
        self.level = 1
        self.score = 0
        self.last_time = time.time()
        self.paused = False
        self.game_over = False
        self.hud = HUD(self)
        self.enemy_spawn_interval = ENEMY_SPAWN_INTERVAL
        self.enemy_count_for_level = 6
        self.enemies_killed = 0

    def spawn_enemy(self):
        # spawn at random edge
        edge = random.choice(["top", "left", "right", "bottom"])
        margin = 30
        if edge == "top":
            pos = (random.uniform(0, SCREEN_WIDTH), -margin)
        elif edge == "bottom":
            pos = (random.uniform(0, SCREEN_WIDTH), SCREEN_HEIGHT + margin)
        elif edge == "left":
            pos = (-margin, random.uniform(0, SCREEN_HEIGHT))
        else:
            pos = (SCREEN_WIDTH + margin, random.uniform(0, SCREEN_HEIGHT))
        etype = "basic" if random.random() < 0.75 else "big"
        e = Enemy(pos, etype)
        self.enemies.append(e)

    def spawn_powerup(self, pos=None):
        types = ["rapid", "shield"]
        ptype = random.choice(types)
        if pos is None:
            pos = (random.uniform(60, SCREEN_WIDTH - 60), random.uniform(60, SCREEN_HEIGHT - 60))
        self.powerups.append(PowerUp(pos, ptype))

    def create_explosion(self, pos, count=18):
        for _ in range(count):
            ang = random.uniform(0, 360)
            speed = random.uniform(30, 160)
            vel = vec_from_angle(ang) * speed
            p = Particle(pos, vel, random.uniform(2, 5), PARTICLE_LIFETIME, self.screen)
            self.particles.append(p)

    def handle_input(self, dt):
        keys = pygame.key.get_pressed()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit(0)
                if event.key == pygame.K_p:
                    self.paused = not self.paused
                if event.key == pygame.K_r and self.game_over:
                    self.reset()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and not self.paused and not self.game_over:
                    self.player_shoot()

        if not self.paused and not self.game_over:
            # shooting with space
            if keys[pygame.K_SPACE]:
                self.player_shoot()

        return keys

    def player_shoot(self):
        now = time.time()
        if (now - self.player.last_shot) >= self.player.fire_delay:
            dirv = vec_from_angle(self.player.angle)
            pos = self.player.pos + dirv * 24
            vel = dirv * BULLET_SPEED + self.player.vel
            b = Bullet(pos, vel, "player", now)
            self.bullets.append(b)
            self.player.last_shot = now

    def spawn_wave_if_needed(self, dt):
        # spawn based on enemies_killed and time
        if len(self.enemies) == 0 and self.enemies_killed >= self.enemy_count_for_level:
            self.level += 1
            self.enemies_killed = 0
            self.enemy_count_for_level = 6 + self.level * 2
            # faster spawns next level
            self.enemy_spawn_interval = max(0.6, ENEMY_SPAWN_INTERVAL - 0.12 * (self.level - 1))
        self.spawn_timer -= dt
        if self.spawn_timer <= 0 and len(self.enemies) < 10:
            self.spawn_enemy()
            self.spawn_timer = self.enemy_spawn_interval

    def update(self, dt):
        now = time.time()
        keys = self.handle_input(dt)
        if self.paused or self.game_over:
            # allow some HUD updates but skip gameplay
            return

        self.player.update(dt, keys)

        # Enemies
        for e in self.enemies:
            e.update(dt, self.player.pos)

        # Bullets update & pruning
        for b in list(self.bullets):
            b.update(dt)
            if not b.alive(now):
                self.bullets.remove(b)

        # Particles
        for p in list(self.particles):
            p.update(dt)
            if not p.alive():
                self.particles.remove(p)

        # Powerups (static)
        for pu in list(self.powerups):
            # collision with player?
            if pu.pos.distance_to(self.player.pos) < (pu.radius + self.player.radius):
                self.apply_powerup(pu)
                pu.collected = True
                if pu in self.powerups:
                    self.powerups.remove(pu)

        # Collisions: bullets vs enemies
        for b in list(self.bullets):
            if b.owner == "player":
                for e in list(self.enemies):
                    if b.pos.distance_to(e.pos) < (b.radius + e.radius):
                        e.health -= 20
                        try:
                            self.bullets.remove(b)
                        except ValueError:
                            pass
                        self.create_explosion(b.pos, count=6)
                        if e.health <= 0:
                            self.score += 100 if e.etype == "basic" else 250
                            self.enemies.remove(e)
                            self.enemies_killed += 1
                            # chance to drop powerup
                            if random.random() < 0.12:
                                self.spawn_powerup(e.pos)
                            self.create_explosion(e.pos, count=20 if e.etype == "big" else 12)
                        break

        # Enemy collisions with player or player bullets from enemy
        for e in list(self.enemies):
            # enemy vs player
            if e.pos.distance_to(self.player.pos) < (e.radius + self.player.radius):
                if self.player.shield_time > 0:
                    # shield absorbs
                    self.player.shield_time = max(0, self.player.shield_time - 1.2)
                else:
                    self.player.health -= 18 if e.etype == "basic" else 36
                # knockback
                direction = (self.player.pos - e.pos)
                if direction.length() > 0:
                    direction.scale_to_length(8)
                    self.player.pos += direction
                self.create_explosion(e.pos, count=8)
                # small chance enemy dies
                if random.random() < 0.2:
                    self.enemies.remove(e)
                    self.score += 60
                    self.create_explosion(e.pos, 18)

        # enemies shooting occasionally (big enemies)
        if random.random() < 0.014 and len(self.enemies) > 0:
            shooter = random.choice(self.enemies)
            if shooter.etype == "big":
                # shoot a slow heavy bullet toward player
                dirv = (self.player.pos - shooter.pos)
                if dirv.length() > 0:
                    dirv.scale_to_length(6)
                    b = Bullet(shooter.pos + dirv.normalize() * (shooter.radius + 6), dirv, "enemy", now)
                    self.bullets.append(b)

        # bullets vs player
        for b in list(self.bullets):
            if b.owner == "enemy" and b.pos.distance_to(self.player.pos) < (b.radius + self.player.radius):
                if self.player.shield_time > 0:
                    self.player.shield_time = max(0, self.player.shield_time - 0.8)
                else:
                    self.player.health -= 12
                try:
                    self.bullets.remove(b)
                except ValueError:
                    pass
                self.create_explosion(b.pos, 8)

        # die / respawn
        if self.player.health <= 0:
            self.player.lives -= 1
            self.create_explosion(self.player.pos, 36)
            if self.player.lives <= 0:
                self.game_over = True
            else:
                # respawn with health and shield
                self.player.health = self.player.max_health
                self.player.pos = pygame.math.Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
                self.player.vel = pygame.math.Vector2(0, 0)
                self.player.shield_time = 2.0

        # spawn wave & powerups
        self.spawn_wave_if_needed(dt)

        # randomly spawn free powerups occasionally
        if random.random() < 0.002:
            self.spawn_powerup()

    def apply_powerup(self, pu):
        if pu.ptype == "rapid":
            self.player.rapid_fire_time = pu.duration
        elif pu.ptype == "shield":
            self.player.shield_time = max(self.player.shield_time, pu.duration)

    def draw(self):
        screen = self.screen
        screen.fill((10, 10, 18))

        # starfield background (procedural)
        for i in range(60):
            x = (i * 37 + (pygame.time.get_ticks() // 10) % SCREEN_WIDTH) % SCREEN_WIDTH
            y = (i * 53) % SCREEN_HEIGHT
            screen.set_at((x, y), (18, 18, 30))

        for p in self.particles:
            p.draw(screen)

        for pu in self.powerups:
            pu.draw(screen)

        for e in self.enemies:
            e.draw(screen)

        for b in self.bullets:
            b.draw(screen)

        self.player.draw(screen)

        self.hud.draw(screen)

        # small tip
        tip = self.font.render("WASD/Arrows to move, SPACE or click to shoot, P to pause", True, (180, 180, 200))
        screen.blit(tip, (10, SCREEN_HEIGHT - 20))

        pygame.display.flip()

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.update(dt)
            self.draw()

# ---------- Main ----------
if __name__ == "__main__":
    game = Game()
    game.run()
