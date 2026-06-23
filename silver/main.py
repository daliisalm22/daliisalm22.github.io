# THE SILVER WAR 2.0

# Dieses Spiel wurde im Rahmen des Freien Forschens erstellt.
# Samar & Dalia, 2026

'''
Quellen:
- 
'''

#------------------------------------------

# Notizen:
# -> Entrance-Animationen programmieren, also vorm Rennen Countdown, lights out and away we go, fade in wie im Film
# -> Musik und Sounds einstellen und (Settings-Funktion im Start-Screen um die auszuschalten)
# -> go to car screen machen, mit sideshot vom Rennauto und mini-driver 

#------------------------------------------
import asyncio
from random import *
import pygame
import os
import math
import numpy as np

# Windows-only helpers (skip on web/pyodide)
IS_WINDOWS = False
try:
    from ctypes import windll  # type: ignore
    import pywinstyles  # type: ignore
    IS_WINDOWS = True
except Exception:
    windll = None
    pywinstyles = None

pygame.mixer.pre_init(frequency=44100, size=-16, channels=1, buffer=2048)
pygame.init()

#------------------------------------------
pygame.mixer.pre_init(frequency=44100, size=-16, channels=1, buffer=100000)
pygame.init()
pygame.mixer.init()
#------------------------------------------

WIDTH = 500
HEIGHT = 500
TITLE = "𐙚 the silver war 2.0 ˖.𖥔 ݁ ˖ ⊹ ࣪ ˖ 🏎"

os.environ['SDL_VIDEO_CENTERED'] = '1' # Fenster zentrieren
screen = pygame.display.set_mode((WIDTH, HEIGHT)) # Fenster erstellen
pygame.display.set_caption(TITLE) # Titel des Fensters festlegen
clock = pygame.time.Clock() # Clock-Objekt erstellen, um die Framerate zu kontrollieren

# Change window header/title color on Windows only (skip for web builds)
if IS_WINDOWS:
    try:
        hwnd = pygame.display.get_wm_info().get('window')
        if hwnd:
            pywinstyles.change_header_color(hwnd, color="#83769C") # Farbe der Titelleiste ändern
            pywinstyles.change_title_color(hwnd, color="#FFFFFF") # Farbe des Titels ändern
    except Exception:
        pass

icon = pygame.image.load('icon.png') # Icon des Fensters laden
pygame.display.set_icon(icon)        # Icon des Fensters festlegen 

#------------------------------------------

SEKUNDEN_EVENT = pygame.USEREVENT + 1
pygame.time.set_timer(SEKUNDEN_EVENT, 1000)

seconds_passed = 0

countdown_start_time = 0
countdown_lights = 0
countdown_done = False
last_beep_second = -1

#------------------------------------------

# Hintergrundmusik einstellen

countdown_buzzer = pygame.mixer.Sound("sounds/f1_countdown.ogg")
#------------------------------------------

class Actor:
    def __init__(self, image_path, pos=(0,0)):
        self.image = pygame.image.load(image_path).convert_alpha() # Bild laden und Transparenz unterstützen
        self.rect = self.image.get_rect(center=pos)
    
    @property
    def pos(self):
        return self.rect.center
    
    @pos.setter
    def pos(self, value):
        self.rect.center = value

    def draw(self):
        screen.blit(self.image, self.rect)

    def collidepoint(self, point):
        return self.rect.collidepoint(point)
    
    
#------------------------------------------
    
def draw_text(text, center, fontsize, color, fontname=None, owidth=0, ocolor='black', surface = None):
    if surface is None:
        surface = screen

    font = pygame.font.Font(fontname, fontsize)

    if owidth > 0:
        offset = round(fontsize * owidth/10)
        outline_surface = font.render(text, True, ocolor)
        for dx in (-offset, offset+1, offset):
            for dy in (-offset, offset+1, offset):
                if dx != 0 or dy != 0:
                    rect = outline_surface.get_rect(center=(center[0]+dx, center[1]+dy))
                    surface.blit(outline_surface, rect)

    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=center)
    surface.blit(text_surface, text_rect)


#------------------------------------------

drs_button_offset = pygame.math.Vector2(-40, -45)
brake_button_offset = pygame.math.Vector2(40, -45)
button_radius = 18

#------------------------------------------
steering_wheel_img = pygame.image.load('images/wheel.png').convert_alpha()

def draw_rotated_wheel(center, angle, speed_value, steering_wheel_img):
    w, h = steering_wheel_img.get_size()
    wheel_surface = pygame.Surface((w, h), pygame.SRCALPHA)
    
    wheel_surface.blit(steering_wheel_img, (0, 0))
    
    draw_text((f"{str(int(speed_value * 3.7))}0 km/h"), 
              center=(w // 2, h // 2 - 47), 
              fontsize=16, color="white", 
              fontname="fonts/monocraft.ttf", 
              surface=wheel_surface)

    rotated_surface = pygame.transform.rotate(wheel_surface, -angle)
    
    rotated_rect = rotated_surface.get_rect(center=center)
    
    screen.blit(rotated_surface, rotated_rect)
#------------------------------------------

def draw_hearts(current_hearts, top_left, spacing=32):
    for i in range(3):
        x = top_left[0] + i * spacing
        y = top_left[1]
        
        if i < current_hearts:
            screen.blit(heart_pink, (x, y))
        else:
            screen.blit(heart_bw, (x, y))

#------------------------------------------

def draw_glowing_circle(surface, color_rgb, center, radius, glow_radius=15):
    glow_surface = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
    
    for r in range(glow_radius, 0, -3):
        alpha = int(50 * (1 - r / glow_radius)) 
        pygame.draw.circle(glow_surface, (*color_rgb, alpha), (radius * 2, radius * 2), radius + r)
        
    surface.blit(glow_surface, (center[0] - radius * 2, center[1] - radius * 2))
    
    pygame.draw.circle(surface, color_rgb, center, radius)

#------------------------------------------

def get_rotated_button_pos(center, offset, angle):
    rotated_offset = offset.rotate(angle)
    return (center[0] + rotated_offset.x, center[1] + rotated_offset.y)

#------------------------------------------

def build_curve(length, peak_curve):
    segments = []
    for i in range(length):
        factor = math.sin((i / length) * math.pi)
        segments.append(peak_curve * factor)
    return segments

#------------------------------------------
def build_smooth_track(num_segments=5000):
    generated_track = [0] * 120 
    
    current_curve = 0
    target_curve = 0
    steps_until_change = 0
    
    for _ in range(num_segments):
        if steps_until_change <= 0:
            choice = randint(0, 5)
            if choice == 0 or choice == 1:
                target_curve = 0
            elif choice == 2:
                target_curve = 2.5
            elif choice == 3:
                target_curve = -2.5
            elif choice == 4:
                target_curve = 4.5
            elif choice == 5:
                target_curve = -4.5 
                
            steps_until_change = randint(60, 100)
            
        current_curve += (target_curve - current_curve) * 0.03
        generated_track.append(current_curve)
        
        steps_until_change -= 1
        
    return generated_track

track = build_smooth_track(5000)

SEGMENT_LENGTH = 200
ROAD_WIDTH = 1500
camera_depth = 0.72
DRAW_DISTANCE = 90

player_z = 0
player_x = 0

rival_z = 2000        
rival_x = 0            
rival_speed = 1.35

#-----------------------------------------
YAS_BLUE_DARK = (0, 101, 155)
YAS_BLUE_LIGHT = (0, 161, 155) 
DESERT_SAND = "#E3C193"       

SUNSET_SKY = (235, 120, 60)     
NIGHT_SKY = (15, 20, 45)        

#-----------------------------------------

CURVE_STRENGTH = 90
CURB_WIDTH = 0.3

def draw_road(z, x):
    global blend
    horizon_y = HEIGHT / 2

    if state == "race":
        current_time = pygame.time.get_ticks() - race_start_time
    else:
        current_time = 0

    blend = (math.sin((current_time / 60000.0) * 2 * math.pi) + 1) / 2

    # 1. DRAW REAL SKY GRADIENT
    for y in range(0, int(horizon_y)):
        line_pct = y / horizon_y 
        top_r = int(45 + (10 - 45) * blend)
        top_g = int(60 + (15 - 60) * blend)
        top_b = int(120 + (35 - 120) * blend)
        
        bot_r = int(245 + (35 - 245) * blend)
        bot_g = int(140 + (25 - 140) * blend)
        bot_b = int(60 + (45 - 60) * blend)
        
        r = int(top_r + (bot_r - top_r) * line_pct)
        g = int(top_g + (bot_g - top_g) * line_pct)
        b = int(top_b + (bot_b - top_b) * line_pct)
        
        pygame.draw.line(screen, (r, g, b), (0, y), (WIDTH, y))

    if blend > 0.3:
        star_alpha = int(255 * ((blend - 0.3) / 0.7))
        seed(42) 
        for _ in range(35):
            star_x = randint(0, WIDTH)
            star_y = randint(0, int(horizon_y - 10))
            twinkle = int(star_alpha * (0.6 + 0.4 * math.sin(current_time * 0.005 + star_x)))
            
            star_surface = pygame.Surface((4, 4), pygame.SRCALPHA)
            pygame.draw.circle(star_surface, (255, 255, 255, max(0, min(255, twinkle))), (2, 2), 1)
            screen.blit(star_surface, (star_x, star_y))

    if blend < 0.9:
        sun_y = int((horizon_y - 25) + (45 * blend))
        sun_alpha = int(255 * (1.0 - blend))
        
        sun_surface = pygame.Surface((120, 120), pygame.SRCALPHA)
        pygame.draw.circle(sun_surface, (255, 130, 50, int(sun_alpha * 0.2)), (60, 60), 55)
        pygame.draw.circle(sun_surface, (255, 180, 80, int(sun_alpha * 0.4)), (60, 60), 38)
        pygame.draw.circle(sun_surface, (255, 245, 200, sun_alpha), (60, 60), 20)
        
        screen.blit(sun_surface, (WIDTH // 2 - 60, sun_y - 60))

    for y in range(int(horizon_y), HEIGHT):
        ground_pct = (y - horizon_y) / (HEIGHT - horizon_y)
        
        r = int(130 + (227 - 130) * ground_pct)
        g = int(105 + (193 - 105) * ground_pct)
        b = int(75 + (147 - 75) * ground_pct)
        
        r = int(r * (1.0 - blend * 0.6))
        g = int(g * (1.0 - blend * 0.6))
        b = int(b * (1.0 - blend * 0.5))
        
        pygame.draw.line(screen, (r, g, b), (0, y), (WIDTH, y))

    if blend < 0.5 and raven_x > -30:
        flap = 3 if math.sin(pygame.time.get_ticks() * 0.01) > 0 else -3
        pygame.draw.line(screen, (20, 20, 20), (raven_x, raven_y), (raven_x - 8, raven_y - flap), 2)
        pygame.draw.line(screen, (20, 20, 20), (raven_x, raven_y), (raven_x + 8, raven_y - flap), 2)

    if blend >= 0.7 and shooting_star_timer > 0:
        pygame.draw.line(screen, (255, 255, 220), 
                         (int(shooting_star_x), int(shooting_star_y)), 
                         (int(shooting_star_x - shooting_star_dx * 2), int(shooting_star_y - shooting_star_dy * 2)), 2)

    current_segment = int(z / SEGMENT_LENGTH) % len(track)
    points = []
    curve_x = 0

    for n in range(0, DRAW_DISTANCE + 1):
        segment_index = (current_segment + n) % len(track)
        curve_x += track[segment_index] * CURVE_STRENGTH

        depth = n * SEGMENT_LENGTH
        scale = camera_depth / (depth / SEGMENT_LENGTH + camera_depth)

        screen_x = WIDTH / 2 + (curve_x - x) * scale
        screen_y = horizon_y + (HEIGHT - horizon_y) * scale
        half_width = ROAD_WIDTH * scale

        points.append((screen_x, screen_y, half_width))

    for i in range(len(points) - 1, 0, -1):
        x1, y1, w1 = points[i]
        x2, y2, w2 = points[i - 1]
        if w1 < 1:
            continue
            
        pygame.draw.polygon(screen, "#282A2E", [
            (x1 - w1, y1),
            (x1 + w1, y1),
            (x2 + w2, y2),
            (x2 - w2, y2),
        ])

        curb_w = w1 * 0.2
        is_even = (i + current_segment) % 2 == 0

        if is_even:
            curb_color = "#FFFFFF"
        else:
            r = int(200 + (0 - 200) * blend)
            g = int(15 + (101 - 15) * blend)
            b = int(30 + (155 - 30) * blend)
            curb_color = (r, g, b)

        pygame.draw.polygon(screen, curb_color, [
            (x1 - w1, y1),
            (x1 - w1 + curb_w, y1),
            (x2 - w2 + curb_w * (w2/w1), y2), 
            (x2 - w2, y2),
        ])

        pygame.draw.polygon(screen, curb_color, [
            (x1 + w1 - curb_w, y1), 
            (x1 + w1, y1),
            (x2 + w2, y2), 
            (x2 + w2 - curb_w * (w2/w1), y2)
        ])

#------------------------------------------

state = "start"  # Status des Spieles bei Start des Spiels festlegen -> entsprechende Variable erstellen

driver = "" # Variable für den Fahrer

hearts = 3 # Anzahl der Leben

crash_cooldown_until = 0

gotocar_start_time = 0

race_start_time = 0

blend = 0

#------------------------------------------

speed = 0 # Geschwindigkeit des Autos
heading = 0 # Richtung, in die das Auto zeigt
steering_angle = 0 # Winkel, um den das Auto lenkt
x = 0 # x-Koordinate des Autos
y = 0 # y-Koordinate des Autos
max_speed = 1.7 # maximale Geschwindigkeit des Autos
turn_rate = 2 # Wendegeschwindigkeit des Autos
acceleration_per_frame = 0.1 # Beschleunigung pro Frame
braking_per_frame = 0.2 # Bremsen pro Frame

#------------------------------------------

wheel_center = (WIDTH / 2, HEIGHT - 100)
wheel_radius = 80
dragging_wheel = False
drs_pressed = False
brake_pressed = False

#------------------------------------------

play_button = Actor("images/play_button.png", pos=(WIDTH/2, HEIGHT/2 + 75)) 
play_button2 = Actor("images/play_button.png", pos=(WIDTH/2, HEIGHT/2)) 
quit_button = Actor("images/quit_button.png", pos=(WIDTH/2, HEIGHT/2 + 185))

ant_choose = Actor("images/ant.png", pos=(WIDTH/2 + 125, HEIGHT/2 + 140))
rus_choose = Actor("images/rus.png", pos=(WIDTH/2 - 125,HEIGHT/2 + 140))
kimi_choose = Actor("images/kimi_choose.png", pos=(WIDTH/2 + 125, HEIGHT/2 - 40))
george_choose = Actor("images/george_choose.png", pos=(WIDTH/2 - 125, HEIGHT/2 - 40))

#kimi_gotocar = Actor("images/kimi_gotocar.png")
#george_gotocar = Actor("images/george_gotocar.png")

rival_car = pygame.image.load("images/rival_car.png").convert_alpha()

fade_alpha = 255
heart_pink = pygame.image.load("images/heart_pink.png").convert_alpha()
heart_bw = pygame.image.load("images/heart_bw.png").convert_alpha()

pause_button = pygame.transform.scale(pygame.image.load("images/pause_button.png").convert_alpha(), (40, 40))
pause_start_time = 0

retry_button_img = pygame.image.load("images/retry_btn.png").convert_alpha()
menu_button_img = pygame.image.load("images/menu_btn.png").convert_alpha()

retry_rect = retry_button_img.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
menu_rect = menu_button_img.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 120))

gotocar_car_img = pygame.image.load("images/gotocar.png").convert_alpha()

merc_logo = pygame.image.load("images/merc.png").convert_alpha()
#-----------------------------------------

raven_x = -20
raven_y = 100
raven_speed = 1.5

shooting_star_x = -50
shooting_star_y = -50
shooting_star_dx = 0
shooting_star_dy = 0
shooting_star_timer = 0
has_spawned_this_night = False

#------------------------------------------

def update():
    global state, driver, steering_angle, speed, heading, player_x, player_z, track, countdown_lights, countdown_done, countdown_start_time, hearts, crash_cooldown_until, race_start_time, rival_x, rival_z, blend, raven_x, raven_y, raven_speed, shooting_star_x, shooting_star_y, shooting_star_dx, shooting_star_dy, shooting_star_timer, fade_alpha, has_spawned_this_night
    # je nach Status des Spieles entsprechenden Bildschirm aktualisieren

    if state == "start":
        keys = pygame.key.get_pressed()

        if keys[pygame.K_SPACE]:
            state = "choose"

    elif state == "choose":
        keys = pygame.key.get_pressed()

        if keys[pygame.K_LEFT]:
            driver = "russell"
            state = "gotocar"
        elif keys[pygame.K_RIGHT]:
            driver = "antonelli"
            state = "gotocar"

    elif state == "gotocar":
        if pygame.time.get_ticks() - gotocar_start_time > 5000:
            state= "countdown"
            countdown_start_time = pygame.time.get_ticks()
            fade_alpha = 255
            player_z = 0
            player_x = 0

    elif state == "countdown":
        global countdown_lights, countdown_done, race_start_time
        elapsed = pygame.time.get_ticks() - countdown_start_time
        fade_alpha = max(0, fade_alpha - 4)

        if elapsed < 100:
            countdown_buzzer.play()

        if not countdown_done:
            countdown_lights = min(5, elapsed // 1000)
            if countdown_lights == 5 and elapsed > 6000 + randint(0, 2000):
                countdown_done = True
                race_start_time = pygame.time.get_ticks()
                state = "race"

    elif state == "race":
        #segments_traveled = int(player_z / SEGMENT_LENGTH)
        #if segments_traveled + DRAW_DISTANCE + 20 >= len(track):
        #    track += make_chunk()

        keys = pygame.key.get_pressed()

        target_steering = 0
        if not dragging_wheel:
            if keys[pygame.K_LEFT]:
                target_steering = -90
            elif keys[pygame.K_RIGHT]:
                target_steering = 90
            
            steering_angle += (target_steering - steering_angle) * 0.025

        if keys[pygame.K_UP] or drs_pressed:
            speed += acceleration_per_frame
        if keys[pygame.K_DOWN] or brake_pressed:
            speed -= braking_per_frame

        speed = max(0, min(max_speed, speed))
        steering_angle = max(-90, min(90, steering_angle))

        current_segment = int(player_z / SEGMENT_LENGTH) % len(track)
        current_curve = track[current_segment]

        if speed > 0.01:
            player_z += speed * 45
        else:
            speed = 0

        speed_ratio = speed / max_speed

        if speed > 0:
            heading += steering_angle * 0.05 * speed_ratio

        player_x += heading * speed_ratio
        
        if speed > 0:
            player_x -= current_curve * 8.0 * speed_ratio

        if target_steering == 0:
            heading *= 0.92
            
        if abs(player_x) > ROAD_WIDTH * 0.80:
            if speed > max_speed * 0.4:
                speed -= braking_per_frame * 0.1


        x = player_x

        if abs(player_x) > ROAD_WIDTH:
            now = pygame.time.get_ticks()
            if now > crash_cooldown_until:
                hearts -= 1
                speed = 0 
                player_x = 0
                steering_angle = 0
                crash_cooldown_until = now + 3000

                current_seg = int(player_z / SEGMENT_LENGTH)
                for idx in range(current_seg, current_seg + 40):
                    if idx < len(track):
                        track[idx] = 0

        player_x = max(-ROAD_WIDTH, min(ROAD_WIDTH, player_x))

        minutes_passed = int((pygame.time.get_ticks() - race_start_time) / 60000)

        dynamic_rival_speed = 1.35 + (minutes_passed * 0.12)
        rival_z += dynamic_rival_speed * 45
        rival_time = pygame.time.get_ticks() * 0.002
        rival_x = math.sin(rival_time) * (ROAD_WIDTH * 0.4)


        if shooting_star_timer > 0:
            shooting_star_x += shooting_star_dx
            shooting_star_y += shooting_star_dy
            shooting_star_timer -= 1
        elif blend >= 0.95:
            night_cycle_count = int((pygame.time.get_ticks() - race_start_time) / 60000)
            if night_cycle_count % 2 == 0 and not has_spawned_this_night and shooting_star_timer == 0:
                shooting_star_x = randint(100, WIDTH - 200)
                shooting_star_y = randint(20, int(HEIGHT / 2) - 80)
                shooting_star_dx = choice([4, 6, 8])
                shooting_star_dy = choice([2, 3, 4])
                shooting_star_timer = 30
                has_spawned_this_night = True
        
        if blend < 0.5:
            has_spawned_this_night = False


        if blend < 0.5:
            raven_x += raven_speed
            if raven_x > WIDTH + 50:
                raven_x = -30
                raven_y = randint(40, 120)
                raven_speed = uniform(1.0, 2.5)
        else:
            if raven_x > -20:
                raven_x = -40

        if hearts == 0:
            state = "gameover"

    elif state == "paused":
        return

#------------------------------------------

def draw():
    global steering_angle
    screen.fill(("#000000")) # Hintergrundfarbe des Fensters festlegen

    # je nach Status des Spieles entsprechenden Bildschirm zeichnen

    if state == "start":
        blend = 0.95 
        horizon_y = HEIGHT 
        
        for y in range(0, int(horizon_y)):
            line_pct = y / horizon_y 
            
            top_r = int(10 + (5 - 10) * blend)
            top_g = int(20 + (10 - 20) * blend)
            top_b = int(60 + (30 - 60) * blend)

            bot_r = int(80 + (20 - 80) * blend)
            bot_g = int(20 + (5 - 20) * blend)
            bot_b = int(100 + (40 - 100) * blend)
            
            r = int(top_r + (bot_r - top_r) * line_pct)
            g = int(top_g + (bot_g - top_g) * line_pct)
            b = int(top_b + (bot_b - top_b) * line_pct)
            
            pygame.draw.line(screen, (r, g, b), (0, y), (WIDTH, y))

        seed(42) 
        for _ in range(40):
            star_x = randint(0, WIDTH)
            star_y = randint(0, HEIGHT)
            twinkle = int(120 + 135 * math.sin(pygame.time.get_ticks() * 0.003 + star_x))
            
            star_surface = pygame.Surface((4, 4), pygame.SRCALPHA)
            pygame.draw.circle(star_surface, (255, 255, 255, max(0, min(255, twinkle))), (2, 2), 1)
            screen.blit(star_surface, (star_x, star_y))

        screen.blit(merc_logo, (WIDTH // 2 - merc_logo.get_width() // 2, HEIGHT // 2 - 200))
        draw_text("SILVER WAR 2.0", center=(WIDTH/2, HEIGHT/2 - 30), owidth=0.25, 
                  ocolor=("#83769C"), fontsize=45, color="white", fontname='fonts/monocraft.ttf')
        
        play_button.draw()
        quit_button.draw()

    elif state == "choose":
        draw_text("CHOOSE YOUR DRIVER!", center=(WIDTH/2, HEIGHT/2 - 205), fontsize=35, color="white", fontname='fonts/monocraft.ttf')
        draw_text("George Russell", center=(WIDTH/2 - 125, HEIGHT/2 + 200), fontsize=15, color="white", fontname='fonts/monocraft.ttf')
        draw_text("Kimi Antonelli", center=(WIDTH/2 + 125, HEIGHT/2 + 200), fontsize=15, color="white", fontname='fonts/monocraft.ttf')

        pygame.draw.rect(screen, "#9C768F", pygame.Rect(ant_choose.pos[0] - 66, ant_choose.pos[1] - 31, 132, 62))
        pygame.draw.rect(screen, "#9C768F", pygame.Rect(rus_choose.pos[0] - 66, rus_choose.pos[1] - 31, 132, 62))

        ant_choose.draw()
        rus_choose.draw()
        kimi_choose.draw()
        george_choose.draw()
    
    elif state == "gotocar":
        current_time = pygame.time.get_ticks() - gotocar_start_time
        blend = (math.sin((current_time / 60000.0) * 2 * math.pi) + 1) / 2

        sky_height = int(HEIGHT * 0.6)
        for y in range(0, sky_height):
            line_pct = y / sky_height
            top_r = int(45 + (10 - 45) * blend)
            top_g = int(60 + (15 - 60) * blend)
            top_b = int(120 + (35 - 120) * blend)
            
            bot_r = int(245 + (35 - 245) * blend)
            bot_g = int(140 + (25 - 140) * blend)
            bot_b = int(60 + (45 - 60) * blend)
            
            r = int(top_r + (bot_r - top_r) * line_pct)
            g = int(top_g + (bot_g - top_g) * line_pct)
            b = int(top_b + (bot_b - top_b) * line_pct)
            pygame.draw.line(screen, (r, g, b), (0, y), (WIDTH, y))

        if blend > 0.3:
            star_alpha = int(255 * ((blend - 0.3) / 0.7))
            seed(42)
            for _ in range(15):
                star_x = randint(0, WIDTH)
                star_y = randint(0, sky_height - 10)
                twinkle = int(star_alpha * (0.6 + 0.4 * math.sin(current_time * 0.005 + star_x)))
                star_surface = pygame.Surface((4, 4), pygame.SRCALPHA)
                pygame.draw.circle(star_surface, (255, 255, 255, max(0, min(255, twinkle))), (2, 2), 1)
                screen.blit(star_surface, (star_x, star_y))

        sand_y = sky_height
        sand_height = int(HEIGHT * 0.15)
        for y in range(sand_y, sand_y + sand_height):
            ground_pct = (y - sand_y) / sand_height
            r = int(130 + (227 - 130) * ground_pct)
            g = int(105 + (193 - 105) * ground_pct)
            b = int(75 + (147 - 75) * ground_pct)
            r = int(r * (1.0 - blend * 0.6))
            g = int(g * (1.0 - blend * 0.6))
            b = int(b * (1.0 - blend * 0.5))
            pygame.draw.line(screen, (r, g, b), (0, y), (WIDTH, y))

        track_y = sand_y + sand_height
        track_height = HEIGHT - track_y
        pygame.draw.rect(screen, (40, 42, 46), (0, track_y, WIDTH, track_height))

        curb_y = track_y
        curb_h = 12
        curb_w = 60
        for i in range((WIDTH // curb_w) + 1):
            if i % 2 == 0:
                curb_color = (255, 255, 255)
            else:
                cr = int(200 + (0 - 200) * blend)
                cg = int(15 + (101 - 15) * blend)
                cb = int(30 + (155 - 30) * blend)
                curb_color = (cr, cg, cb)
            pygame.draw.rect(screen, curb_color, (i * curb_w, curb_y, curb_w, curb_h))

        car_x = -150
        car_y = track_y - 50

        if current_time < 1000:
            car_x = WIDTH + 150 - (current_time / 1000) * (WIDTH // 2 + 150)
        elif current_time < 3000:
            car_x = WIDTH // 2
        else:
            car_x = WIDTH // 2 - ((current_time - 3000) / 1000) * (WIDTH // 2 + 150)
            
        screen.blit(gotocar_car_img, (car_x - (gotocar_car_img.get_width() // 2), car_y))
        
        if 1000 <= current_time < 3000:
            rival_name = "Kimi" if driver == "russell" else "George"
            message = f"Let's beat {rival_name}!!"
            
            bubble_w, bubble_h = 420, 120
            bubble_x = WIDTH // 2 - bubble_w // 2
            bubble_y = car_y - 150  
            
            pygame.draw.rect(screen, (255, 255, 255), (bubble_x, bubble_y, bubble_w, bubble_h))
            pygame.draw.rect(screen, (15, 15, 18), (bubble_x, bubble_y, 6, 6))
            pygame.draw.rect(screen, (15, 15, 18), (bubble_x + bubble_w - 6, bubble_y, 6, 6))
            pygame.draw.rect(screen, (15, 15, 18), (bubble_x, bubble_y + bubble_h - 6, 6, 6))
            pygame.draw.rect(screen, (15, 15, 18), (bubble_x + bubble_w - 6, bubble_y + bubble_h - 6, 6, 6))
            
            pygame.draw.rect(screen, (255, 255, 255), (bubble_x + 6, bubble_y, bubble_w - 12, 6))
            pygame.draw.rect(screen, (255, 255, 255), (bubble_x, bubble_y + 6, 6, bubble_h - 12))
            pygame.draw.rect(screen, (255, 255, 255), (bubble_x + bubble_w - 6, bubble_y + 6, 6, bubble_h - 12))
            pygame.draw.rect(screen, (255, 255, 255), (bubble_x + 6, bubble_y + bubble_h - 6, bubble_w - 12, 6))

            pygame.draw.rect(screen, (255, 255, 255), (WIDTH // 2 - 12, bubble_y + bubble_h, 24, 6))
            pygame.draw.rect(screen, (255, 255, 255), (WIDTH // 2 - 6, bubble_y + bubble_h + 6, 12, 6))
            
            draw_text(message, center=(WIDTH // 2, bubble_y + bubble_h // 2), color=(0, 0, 0), fontsize=30, fontname="fonts/monocraft.ttf")

    elif state == "countdown":
        draw_road(player_z, player_x)

        if fade_alpha > 0:
            fade_surface = pygame.Surface((WIDTH, HEIGHT))
            fade_surface.fill((0, 0, 0))
            fade_surface.set_alpha(fade_alpha)
            screen.blit(fade_surface, (0, 0))

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))

        light_spacing = 50
        start_x = WIDTH / 2 - (light_spacing * 2)
        
        for i in range(5):
            light_x = int(start_x + i * light_spacing)
            light_y = int(HEIGHT / 2 - 40)

            pygame.draw.circle(screen, "#222222", (light_x, light_y), 20)
            
            if i < countdown_lights:
                draw_glowing_circle(screen, (255, 0, 0), (light_x, light_y), 12, glow_radius=15)
            else:
                pygame.draw.circle(screen, "#440000", (light_x, light_y), 12)

        draw_rotated_wheel(wheel_center, steering_angle, speed, steering_wheel_img)

    elif state == "race":
        draw_road(player_z, player_x)

        relative_z = rival_z - player_z
        if 0 < relative_z < (DRAW_DISTANCE * SEGMENT_LENGTH):
            scale = camera_depth / (relative_z / SEGMENT_LENGTH + camera_depth)
            rival_seg = int(rival_z / SEGMENT_LENGTH) % len(track)
            curve_at_rival = track[rival_seg] * CURVE_STRENGTH
            
            rival_screen_x = WIDTH / 2 + (curve_at_rival + rival_x - player_x) * scale
            rival_screen_y = (HEIGHT / 2) + (HEIGHT / 2) * scale
            
            w = int(500 * scale) 
            h = int(500 * scale)
            
            scaled_rival = pygame.transform.scale(rival_car, (w, h))
            screen.blit(scaled_rival, (int(rival_screen_x - w / 2), int(rival_screen_y - h)))
            
            rival_name = "Kimi" if driver == "russell" else "George"
            draw_text(rival_name.upper(), center=(rival_screen_x, rival_screen_y - h - 15), fontsize=max(10, int(20 * scale)), color="white", fontname="fonts/monocraft.ttf")
        

        if relative_z > 0:
            current_rank = 2
        else:
            current_rank = 1

        draw_rotated_wheel(wheel_center, steering_angle, speed, steering_wheel_img)
        draw_text(f"{zeit_text}s", center=(WIDTH/2, 25), fontsize=22, color="white", fontname="fonts/monocraft.ttf", surface=screen)
        draw_hearts(hearts, top_left=(40, 10))
        screen.blit(pause_button, (WIDTH - 70, 10))

        rank_text = f"{current_rank}{'st' if current_rank == 1 else 'nd'}"
        draw_text(rank_text, center=(WIDTH - 120, 25), fontsize=22, color="white", fontname="fonts/monocraft.ttf")

        now = pygame.time.get_ticks()
        if now < crash_cooldown_until:
            if (now // 150) % 2 == 0:
                red_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                red_overlay.fill((255, 0, 0, 80))
                screen.blit(red_overlay, (0, 0))

    elif state in ["race", "countdown"]:
        pause_button.draw()

    elif state == "paused":
        pause_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pause_overlay.fill((0, 0, 0, 50))
        screen.blit(pause_overlay, (0, 0))

        draw_text("GAME PAUSED", center=(WIDTH/2, HEIGHT/2 - 150), owidth=0.25, ocolor=("#83769C"), fontsize=60, color="white", fontname='fonts/monocraft.ttf')

        play_button2.center = (WIDTH // 2, HEIGHT // 2)
        play_button2.draw()

        screen.blit(menu_button_img, menu_rect.topleft)



    elif state == "gameover":
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180)) 
        screen.blit(overlay, (0, 0))

        draw_text("GAME OVER", center=(WIDTH/2, HEIGHT/2 - 120), owidth=0.25, 
                  ocolor=("#83769C"), fontsize=60, color="white", fontname='fonts/monocraft.ttf')

        if player_z > rival_z:
            result_text = "YOU FINISHED 1ST!"
            result_color = "#FFD700" # golddd
        else:
            result_text = "YOU FINISHED 2ND!"
            result_color = "#C0C0C0" # silber
            
        draw_text(result_text, center=(WIDTH/2, HEIGHT/2 - 40), fontsize=40, 
                  color=result_color, fontname='fonts/monocraft.ttf')

        screen.blit(retry_button_img, retry_rect.topleft)
        screen.blit(menu_button_img, menu_rect.topleft)

    pygame.display.flip() # Bildschirm aktualisieren

#------------------------------------------

def on_mouse_down(pos):
    global state, driver, gotocar_start_time, dragging_wheel, drs_pressed, brake_pressed
    global previous_state, race_start_time, countdown_start_time, pause_start_time
    # je nach Status des Spieles bestimmte Dinge ausführen, wenn sich die Maus an einer bestimmten Stelle befindet

    if state == "start":
        if play_button.collidepoint(pos):
            state = "choose"
        elif quit_button.collidepoint(pos):
            exit()   

    elif state == "choose":
        if rus_choose.collidepoint(pos) or george_choose.collidepoint(pos):
            driver = "russell"
            state = "gotocar"
            gotocar_start_time = pygame.time.get_ticks()
        elif ant_choose.collidepoint(pos) or kimi_choose.collidepoint(pos):
            driver = "antonelli"
            state = "gotocar"
            gotocar_start_time = pygame.time.get_ticks()

    elif state == "race":
        if pygame.Rect(WIDTH - 60, 20, 40, 40).collidepoint(pos):
            previous_state = state
            state = "paused"
            pause_start_time = pygame.time.get_ticks() 
            return
            
        drs_screen_pos = get_rotated_button_pos(wheel_center, drs_button_offset, steering_angle)
        brake_screen_pos = get_rotated_button_pos(wheel_center, brake_button_offset, steering_angle)
        
        if math.hypot(pos[0] - drs_screen_pos[0], pos[1] - drs_screen_pos[1]) <= button_radius:
            drs_pressed = True
        elif math.hypot(pos[0] - brake_screen_pos[0], pos[1] - brake_screen_pos[1]) <= button_radius:
            brake_pressed = True
        else:
            dx = pos[0] - wheel_center[0]
            dy = pos[1] - wheel_center[1]
            distance = math.hypot(dx, dy)
            if distance <= wheel_radius:
                dragging_wheel = True

    elif state == "paused":
        play_rect = pygame.Rect(WIDTH // 2 - 60, HEIGHT // 2, 120, 40)
        back_rect = pygame.Rect(WIDTH // 2 - 60, HEIGHT // 2 + 60, 120, 40)
        
        if play_button.collidepoint(pos):
            pause_duration = pygame.time.get_ticks() - pause_start_time
            
            race_start_time += pause_duration
            countdown_start_time += pause_duration
            
            state = previous_state 
        elif back_rect.collidepoint(pos):
            state = "start"

    elif state == "gameover":
        global player_x, player_z, speed, hearts
        if retry_rect.collidepoint(pos):
            state = "race"
            player_z = 0
            player_x = 0
            speed = 0
            hearts = 3
            race_start_time = pygame.time.get_ticks()
            state = "race" 
            return
        
        elif menu_rect.collidepoint(pos):
            state = "start"
            return

#------------------------------------------

def on_mouse_up():
    global dragging_wheel, drs_pressed, brake_pressed
    dragging_wheel = False
    drs_pressed = False
    brake_pressed = False

#------------------------------------------

def on_mouse_motion(pos):
    global steering_angle
    if dragging_wheel:
        dx = pos[0] - wheel_center[0]
        dy = pos[1] - wheel_center[1]
        angle = math.degrees(math.atan2(dx, -dy))
        steering_angle = max(-90, min(90, angle))

async def main():
    global racing, seconds_passed, zeit_text
    
    racing = True
    clock = pygame.time.Clock()

    while racing:
        # 1. Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                racing = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                on_mouse_down(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                on_mouse_up()
            elif event.type == pygame.MOUSEMOTION:
                on_mouse_motion(event.pos)
            elif event.type == SEKUNDEN_EVENT:
                seconds_passed += 1

        # 2. Logic Updates
        if state == "race":
            race_duration = pygame.time.get_ticks() - race_start_time
        else:
            race_duration = 0

        minuten = int(race_duration / 60000)
        sekunden = int((race_duration % 60000) / 1000)
        hundertstel = int((race_duration % 1000) / 10)
        zeit_text = f"{minuten:02d}:{sekunden:02d}.{hundertstel:02d}"

        update()
        draw()
        
        # 3. Frame control for Web
        await asyncio.sleep(0)
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    asyncio.run(main())