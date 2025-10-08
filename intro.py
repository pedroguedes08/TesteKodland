# Teste kodland
from pygame import Rect
import random
import math

TITLE = "Roguelike Submarino"
WIDTH, HEIGHT = 800, 480

def clamp(v, lo, hi): return max(lo, min(hi, v))
MAX_BUBBLES = 120

# ---------------- helpers de áudio ----------------
def safe_play_ambient():
    try:
        if G.sound_on:
            sounds.ocean.play(-1)
    except Exception:
        pass

def safe_stop_ambient():
    try:
        sounds.ocean.stop()
    except Exception:
        pass

def safe_play_sfx(name):
    try:
        if G.sound_on:
            getattr(sounds, name).play()
    except Exception:
        pass

# ---------------- terreno ----------------
class Terrain:
    def __init__(self, name="terrain_sand_top_h"):
        tmp = Actor(name)
        self.tile_w, self.tile_h = tmp.width, tmp.height
        self.name = name
        self.tiles = []
        self.build()
    @property
    def sand_top_y(self): return HEIGHT - self.tile_h + 2
    def build(self):
        self.tiles.clear()
        n = int(math.ceil(WIDTH / float(self.tile_w))) + 1
        for i in range(n):
            a = Actor(self.name); a.anchor=("left","bottom"); a.pos=(i*self.tile_w, HEIGHT)
            self.tiles.append(a)
    def draw(self): [t.draw() for t in self.tiles]

# ---------------- parallax ----------------
class ParallaxRow:
    def __init__(self, names, base_y, speed=20, spacing=140, scale=1.0):
        self.speed, self.spacing, self.scale = speed, spacing, scale
        self.actors = []; self.build(names, base_y)
    def build(self, names, base_y):
        self.actors.clear(); x=-self.spacing; i=0
        while x < WIDTH + self.spacing:
            a = Actor(names[i % len(names)]); a.anchor=("center","bottom"); a.pos=(x, base_y)
            try: a.scale=self.scale
            except Exception: pass
            self.actors.append(a); x += self.spacing; i += 1
    def update(self, dt):
        mx = max(a.x for a in self.actors) if self.actors else WIDTH
        for a in self.actors:
            a.x -= self.speed * dt
            if a.right < -10:
                a.x = mx + self.spacing; mx = a.x
    def draw(self): [a.draw() for a in self.actors]

# ---------------- bolhas ----------------
class Bubble:
    def __init__(self, x, y, speed_range=(1.0, 2.0)):
        self.actor = Actor("bubble_a", (x, y))
        self.speed = random.uniform(*speed_range)
        self.phase = random.uniform(0, math.tau)
    def update(self, dt):
        a=self.actor; a.y -= self.speed; a.x += math.sin((a.y + self.phase*30.0)/16.0)*0.6
    def offscreen(self): return self.actor.y < -30
    def draw(self): self.actor.draw()

# ---------------- tiro ----------------
class Shot:
    def __init__(self, x, y, speed=300):
        self.actor = Actor("bubble_b", (x, y)); self.speed = speed
    def update(self, dt): self.actor.x += self.speed * dt
    def offscreen(self): return self.actor.x > WIDTH + 30
    def draw(self): self.actor.draw()

# ---------------- peixes de cenário ----------------
class BgFish:
    def __init__(self, x, y):
        self.actor = Actor(random.choice(["fish_grey","fish_pink"]), (x,y))
        try: self.actor.flip_x = True
        except Exception: pass
        try: self.actor.scale = random.uniform(0.6, 0.8)
        except Exception: pass
        self.speed = random.uniform(0.6, 1.2)
        self.wag_phase = random.uniform(0, math.tau)
        self.wag_speed = random.uniform(5.0, 8.0)
        self.wag_amp   = random.uniform(2.0, 4.0)
        self.next_breath = random.uniform(0.8, 1.6)
    def update(self, dt, bubble_cb):
        self.actor.x -= self.speed
        self.wag_phase += self.wag_speed * dt
        self.actor.angle = self.wag_amp * math.sin(self.wag_phase)
        self.next_breath -= dt
        if self.next_breath <= 0:
            self.next_breath = random.uniform(0.9, 1.7)
            bubble_cb(self.actor.x-6, self.actor.y-8, (0.8,1.6))
    def offscreen(self): return self.actor.x < -60
    def draw(self): self.actor.draw()

# ---------------- inimigos ----------------
class EnemyBase:
    def __init__(self, img, x, y, speed_px_s, dmg_to_hero):
        self.actor = Actor(img, (x,y))
        try: self.actor.flip_x = True
        except Exception: pass
        self.speed = speed_px_s
        self.alive, self.dying = True, False
        self.die_timer, self.die_duration = 0.0, 0.35
        self.dmg_to_hero = dmg_to_hero
        self.wag_phase = random.uniform(0, math.tau)
        self.wag_speed = random.uniform(6.0, 9.5)
        self.wag_amp   = random.uniform(3.0, 6.0)
        self.next_breath = random.uniform(0.6, 1.2)
    def breathe(self, dt, bubble_cb):
        self.next_breath -= dt
        if self.next_breath <= 0:
            self.next_breath = random.uniform(0.6, 1.2)
            bubble_cb(self.actor.x-8, self.actor.y-10, (1.2,2.4))
    def hit_by_shot(self):
        if not self.alive: return
        self.alive, self.dying = False, True
        self.actor.image = "fish_green_skeleton"
        self.actor.angle = 0
        safe_play_sfx("eep")
    def update_common(self, dt):
        if self.alive:
            self.wag_phase += self.wag_speed * dt
            self.actor.angle = self.wag_amp * math.sin(self.wag_phase)
    def update_dying(self, dt):
        if self.dying: self.die_timer += dt
        return self.dying and self.die_timer >= self.die_duration
    def draw(self): self.actor.draw()

class FishBrown(EnemyBase):
    def __init__(self, x, y): super().__init__("fish_brown", x, y, random.uniform(60,100), 10)
    def update(self, dt, bubble_cb):
        if self.alive:
            self.actor.x -= self.speed * dt
            self.breathe(dt, bubble_cb)
        self.update_common(dt)

class FishGreen(EnemyBase):
    def __init__(self, x, y):
        super().__init__("fish_green", x, y, random.uniform(80,120), 20)
        self.base_y, self.phase = y, random.uniform(0, math.tau)
        self.amp = random.uniform(10, 40)
        self.freq = random.uniform(2.0, 3.0)
    def update(self, dt, bubble_cb):
        if self.alive:
            self.actor.x -= self.speed * dt
            self.phase += dt * self.freq * 2*math.pi
            self.actor.y = self.base_y + self.amp * math.sin(self.phase)
            self.breathe(dt, bubble_cb)
        self.update_common(dt)

# ---------------- herói ----------------
class Hero:
    def __init__(self):
        self.actor = Actor("hero"); self.actor.pos = (60, HEIGHT//2)
        self.breath_t, self.breath_dt = 0.0, 0.8
        self.speed = 180
        self.wag_phase = 0.0
        self.wag_speed_idle, self.wag_speed_move = 5.0, 8.5
        self.wag_amp_idle,   self.wag_amp_move   = 2.0, 4.5
    def update(self, dt, bubble_cb, bounds):
        self.breath_t += dt
        if self.breath_t >= self.breath_dt:
            self.breath_t = 0.0
            bubble_cb(self.actor.x + self.actor.width*0.45, self.actor.y - self.actor.height*0.1, (1.0,1.8))
        dx=dy=0
        if keyboard.left:  dx -= self.speed*dt
        if keyboard.right: dx += self.speed*dt
        if keyboard.up:    dy -= self.speed*dt
        if keyboard.down:  dy += self.speed*dt
        self.actor.x += dx; self.actor.y += dy
        xmin,xmax,ymin,ymax = bounds
        self.actor.x = clamp(self.actor.x, xmin, xmax)
        self.actor.y = clamp(self.actor.y, ymin, ymax)
        moving = (abs(dx)+abs(dy)) > 0.1
        ws = self.wag_speed_move if moving else self.wag_speed_idle
        wa = self.wag_amp_move   if moving else self.wag_amp_idle
        self.wag_phase += ws*dt; self.actor.angle = wa * math.sin(self.wag_phase)
    def draw(self): self.actor.draw()

# ---------------- HUD ----------------
class HUD:
    def __init__(self):
        w,h,g=86,28,8; bx,by=16,12
        self.pause_rect=Rect(bx,by,w,h); self.cont_rect=Rect(bx+w+g,by,w,h); self.exit_rect=Rect(bx+(w+g)*2,by,w,h)
        self.panel_x, self.bar_w, self.bar_h = WIDTH-220, 100, 18
    def draw(self, life, kills, paused):
        self._btn(self.pause_rect,"Pausar",paused); self._btn(self.cont_rect,"Continuar",not paused); self._btn(self.exit_rect,"Sair",False)
        x,y=self.panel_x,16
        screen.draw.text("Vida:",(x,y),color="white",fontsize=22)
        screen.draw.filled_rect(Rect((x+50,y+5),(self.bar_w,self.bar_h)),(80,0,0))
        w = clamp(int(life),0,100) * self.bar_w // 100
        screen.draw.filled_rect(Rect((x+50,y+5),(w,self.bar_h)),(0,200,0))
        screen.draw.text(f"Inimigos: {kills}",(x,y+28),color="white",fontsize=22)
    def _btn(self, r, label, hi):
        c=(60,80,140) if not hi else (90,120,190)
        screen.draw.filled_rect(r,c); screen.draw.rect(r,(20,30,60)); screen.draw.text(label,center=r.center,color="white",fontsize=18)
    def click(self,pos):
        if self.pause_rect.collidepoint(pos): return "pause"
        if self.cont_rect.collidepoint(pos):  return "continue"
        if self.exit_rect.collidepoint(pos):  return "exit"

# ---------------- pós-morte ----------------
class DeathUI:
    def __init__(self):
        w,h = 180,40; cx,cy = WIDTH//2, HEIGHT//2 + 70
        self.r_restart = Rect(cx-(w+12), cy, w, h)
        self.r_menu    = Rect(cx+12,     cy, w, h)
    def draw(self, kills, time_s, best_k, best_t):
        screen.draw.filled_rect(Rect(0,0,WIDTH,HEIGHT), (0,0,0))
        screen.draw.text("Morreu!", center=(WIDTH//2, HEIGHT//2-60), fontsize=52, color="white")
        screen.draw.text(f"Inimigos abatidos: {kills}", center=(WIDTH//2, HEIGHT//2-10), fontsize=32, color="white")
        screen.draw.text(f"Tempo: {time_s:.1f}s", center=(WIDTH//2, HEIGHT//2+20), fontsize=28, color="white")
        screen.draw.text(f"Recorde: {best_k} | Tempo: {best_t:.1f}s", center=(WIDTH//2, HEIGHT//2+46), fontsize=22, color="white")
        self._btn(self.r_restart, "Reiniciar"); self._btn(self.r_menu, "Menu principal")
    def _btn(self, r, label):
        screen.draw.filled_rect(r,(80,120,180)); screen.draw.rect(r,(20,30,60)); screen.draw.text(label, center=r.center, color="white", fontsize=22)
    def click(self,pos):
        if self.r_restart.collidepoint(pos): return "restart"
        if self.r_menu.collidepoint(pos):    return "menu"

# ---------------- menu ----------------
class Menu:
    def __init__(self):
        self.buttons=[{"text":"Iniciar o jogo","rect":Rect(300,180,200,50)},
                      {"text":"Som: Ligado","rect":Rect(300,250,200,50)},
                      {"text":"Sair","rect":Rect(300,320,200,50)}]
    def draw(self):
        screen.fill((30,30,50))
        screen.draw.text("Projeto - Roguelike Submarino",center=(WIDTH//2,100),fontsize=40,color="white")
        for b in self.buttons:
            screen.draw.filled_rect(b["rect"],(70,90,150))
            screen.draw.text(b["text"],center=b["rect"].center,fontsize=30,color="white")
    def click(self,pos):
        for b in self.buttons:
            if b["rect"].collidepoint(pos): return b["text"]
    def set_sound_label(self,on): self.buttons[1]["text"]="Som: Ligado" if on else "Som: Desligado"

# ---------------- jogo ----------------
class Game:
    def __init__(self):
        self.state, self.sound_on, self.paused = "menu", True, False
        self.terrain = Terrain(); base_y = self.terrain.sand_top_y
        self.parallax_back  = ParallaxRow(["background_rock_a","background_seaweed_c"], base_y, speed=12, spacing=160, scale=0.9)
        self.parallax_front = ParallaxRow(["background_rock_b","background_seaweed_a","background_seaweed_b","background_seaweed_d"], base_y, speed=22, spacing=140, scale=1.0)
        self.hero = Hero()
        self.enemies, self.bg_fishes, self.bubbles, self.shots = [], [], [], []
        self.hud, self.menu, self.death_ui = HUD(), Menu(), DeathUI()
        self.life, self.kills = 100, 0

        
        self.run_time, self.best_kills, self.best_time = 0.0, 0, 0.0

        # estado de morte
        self.dead = False
        self.death_t = 0.0
        self.freeze_duration = 1.5

        
        safe_play_ambient()

        # timers de spawn
        self.enemy_cd = self.bgfish_cd = 0.0
        self.enemy_interval = (0.8, 1.5)
        self.bgfish_interval = (1.5, 3.0)

    # ---- morte / reset ----
    def hero_die(self):
        if self.dead: return
        self.dead = True
        self.death_t = 0.0
        self.hero.actor.image = "fish_blue_skeleton"
        # burst sutil de bolhas
        for _ in range(28):
            self.spawn_bubble(self.hero.actor.x + random.uniform(-8,8),
                              self.hero.actor.y + random.uniform(-8,8),
                              (1.8,3.0))
        # atualiza recorde
        if self.kills > self.best_kills: self.best_kills = self.kills
        if self.run_time > self.best_time: self.best_time = self.run_time

    def reset_run(self):
        self.dead = False
        self.death_t = 0.0
        self.paused = False
        self.life = 100
        self.kills = 0
        self.run_time = 0.0
        self.hero.actor.image = "hero"
        self.hero.actor.pos = (60, HEIGHT//2)
        self.enemies.clear(); self.bg_fishes.clear(); self.bubbles.clear(); self.shots.clear()
        self.enemy_cd = self.bgfish_cd = 0.0

    # spawns
    def spawn_enemy(self):
        y=random.randint(80, max(81,self.terrain.sand_top_y-40))
        x=WIDTH+random.randint(40,160)
        self.enemies.append(random.choice([FishBrown,FishGreen])(x,y))
    def spawn_bgfish(self):
        y=random.randint(80, max(81,self.terrain.sand_top_y-20))
        x=WIDTH+random.randint(10,100)
        self.bg_fishes.append(BgFish(x,y))
    def spawn_bubble(self,x,y,spd=(1.0,2.0)):
        if len(self.bubbles) < MAX_BUBBLES:
            self.bubbles.append(Bubble(x,y,spd))
    def spawn_burst(self,x,y,n=7):
        for _ in range(n):
            self.spawn_bubble(x+random.uniform(-6,6), y+random.uniform(-6,6), (1.8,3.2))
    def shoot(self):
        a=self.hero.actor; self.shots.append(Shot(a.x+a.width*0.5, a.y, 300))

    
    def on_click(self,pos):
        if self.state=="menu":
            ch=self.menu.click(pos)
            if not ch: return
            if ch.startswith("Iniciar"):
                self.state="game"
                self.reset_run()
            elif ch.startswith("Som"):
                self.sound_on = not self.sound_on
                self.menu.set_sound_label(self.sound_on)
                if self.sound_on: safe_play_ambient()
                else: safe_stop_ambient()
            elif ch.startswith("Sair"): raise SystemExit
        else:
            
            if self.dead and self.death_t >= self.freeze_duration:
                act = self.death_ui.click(pos)
                if act == "restart":
                    self.reset_run()
                elif act == "menu":
                    self.state = "menu"; self.paused = False
                return

            a=self.hud.click(pos)
            if   a=="pause":    self.paused=True
            elif a=="continue": self.paused=False
            elif a=="exit":     raise SystemExit

    def on_key_down(self,key):
        if self.state=="game" and not self.paused and not self.dead and key==keys.SPACE:
            self.shoot()
        if key==keys.ESCAPE and self.state=="game":
            self.state="menu"; self.paused=False
            if self.sound_on: safe_play_ambient()
            else: safe_stop_ambient()

    
    def update(self,dt):
        if self.state!="game": return

        
        if self.dead:
            self.death_t += dt
            
            target = self.terrain.sand_top_y - self.hero.actor.height*0.5
            self.hero.actor.y = min(self.hero.actor.y + 40*dt, target)
            return

        if self.paused: return

        # tempo vivo
        self.run_time += dt

        # herói
        a=self.hero.actor
        xmin=a.width*0.5; xmax=WIDTH-a.width*0.5
        ymin=a.height*0.5; ymax=self.terrain.sand_top_y-1-a.height*0.5
        self.hero.update(dt,self.spawn_bubble,(xmin,xmax,ymin,ymax))

        # parallax
        self.parallax_back.update(dt); self.parallax_front.update(dt)

        # spawns
        self.enemy_cd -= dt; self.bgfish_cd -= dt
        if self.enemy_cd<=0: self.spawn_enemy();  self.enemy_cd = random.uniform(*self.enemy_interval)
        if self.bgfish_cd<=0: self.spawn_bgfish(); self.bgfish_cd = random.uniform(*self.bgfish_interval)

        # inimigos
        for e in list(self.enemies):
            e.update(dt,self.spawn_bubble)
            if e.actor.y>self.terrain.sand_top_y-10: e.actor.y=self.terrain.sand_top_y-10
            if e.alive and e.actor.colliderect(self.hero.actor):
                self.life = clamp(self.life - e.dmg_to_hero, 0, 100)
                self.enemies.remove(e)
                if self.life == 0: self.hero_die()
                continue
            if e.update_dying(dt) or e.actor.x < -60: self.enemies.remove(e)

        # peixes de cenário
        for bf in list(self.bg_fishes):
            bf.update(dt,self.spawn_bubble)
            if bf.actor.y>self.terrain.sand_top_y-10: bf.actor.y=self.terrain.sand_top_y-10
            if bf.offscreen(): self.bg_fishes.remove(bf)

        # tiros
        for s in list(self.shots):
            s.update(dt); hit=False
            for e in self.enemies:
                if e.alive and e.actor.colliderect(s.actor):
                    e.hit_by_shot(); self.kills += 1; self.spawn_burst(e.actor.x,e.actor.y,7); hit=True; break
            if hit or s.offscreen(): self.shots.remove(s)

        # bolhas
        for b in list(self.bubbles):
            b.update(dt)
            if b.offscreen(): self.bubbles.remove(b)

    def draw(self):
        if self.state=="menu": self.menu.draw(); return
        screen.fill((0,0,40))
        self.terrain.draw()
        self.parallax_back.draw(); self.parallax_front.draw()
        for bf in self.bg_fishes: bf.draw()
        for e in self.enemies: e.draw()
        for s in self.shots: s.draw()
        for b in self.bubbles: b.draw()
        self.hero.draw()

        
        if self.dead and self.death_t >= self.freeze_duration:
            self.death_ui.draw(self.kills, self.run_time, self.best_kills, self.best_time)

       
        self.hud.draw(self.life, self.kills, self.paused)

# ---------------- PgZero callbacks ----------------
G=Game()
def draw(): screen.clear(); G.draw()
def update(dt): G.update(dt)
def on_mouse_down(pos): G.on_click(pos)
def on_key_down(key): G.on_key_down(key)

safe_stop_ambient()
safe_play_ambient()
def on_start():
    safe_stop_ambient()
    safe_play_ambient()
