import pygame
import random
import time
import pickle
import os

# Basic parameters
WIDTH, HEIGHT = 480, 640
PLAYER_Y = HEIGHT - 90
PLAYER_SPEED = 6
BULLET_SPEED = 9

# Q-learning parameters
ACTIONS = ["LEFT", "STAY", "RIGHT", "SHOOT"]
ALPHA = 0.1
GAMMA = 0.9
EPSILON = 1.0
MIN_EPSILON = 0.05
EPSILON_DECAY = 0.995
Q = {}

def get_q(s, a):
    return Q.get((s, a), 0.0)

def save_q_table(q_table, filename="q_table.pkl"):
    with open(filename, 'wb') as f:
        pickle.dump(q_table, f)
    print(f"[INFO] The Q table has been successfully saved to {filename}")

def load_q_table(filename="q_table.pkl"):
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            q_table = pickle.load(f)
        print(f"[INFO] The trained Q-table has been loaded from {filename}")
        return q_table
    else:
        print(f"[INFO] {filename} not found. Starting training with an empty Q-table.")
        return {}

Q = load_q_table("q_table.pkl")

def choose_action(state):
    if random.random() < EPSILON:
        return random.choice(ACTIONS)
    return max(ACTIONS, key=lambda a: get_q(state, a))

def update_q(s, a, r, s2):
    Q[(s, a)] = get_q(s, a) + ALPHA * (
        r + GAMMA * max(get_q(s2, na) for na in ACTIONS) - get_q(s, a)
    )

# State space
def get_state(px, ex, ey, etype):
    dx = ex - px
    x_state = "left" if dx < -40 else "right" if dx > 40 else "center"
    y_state = "near" if ey > HEIGHT * 0.55 else "far"
    return (x_state, y_state, etype)

# Enemy aircraft
def spawn_enemy():
    etype = random.choice(["small", "large"])
    if etype == "small":
        return etype, 32, 6, 10, -20
    else:
        return etype, 64, 3, 30, -20

# Pygame initialization
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("PLANE WAR")
clock = pygame.time.Clock()

font = pygame.font.Font(None, 28)
big_font = pygame.font.Font(None, 48)

# Load pictures
player_img = pygame.transform.scale(
    pygame.image.load("player.png").convert_alpha(), (50, 50)
)
enemy_imgs = {
    "small": pygame.transform.scale(
        pygame.image.load("enemy_small.png").convert_alpha(), (32, 32)),
    "large": pygame.transform.scale(
        pygame.image.load("enemy_large.png").convert_alpha(), (64, 64))
}
life_icon = pygame.transform.scale(player_img, (25, 25))

# Start menu
def start_menu():
    while True:
        screen.fill((0, 0, 0))
        title = big_font.render("PLANE WAR", True, (255, 255, 255))
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 200))

        tips = [
            "Press A - AI Mode",
            "Press H - Human Mode",
            "Press the left and right keys to move the plane",
            "Press space to shoot",
            "Press ESC - Quit"
        ]

        for i, t in enumerate(tips):
            txt = font.render(t, True, (200, 200, 200))
            screen.blit(txt, (WIDTH//2 - txt.get_width()//2, 300 + i*40))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_a:
                    return "AI"
                if event.key == pygame.K_h:
                    return "HUMAN"
                if event.key == pygame.K_ESCAPE:
                    return None

# Game starts
mode = start_menu()
if mode is None:
    pygame.quit()
    exit()

player_x = WIDTH // 2
bullets = []
lives = 3
score = 0
last_reward = 0

etype, esize, espeed, ereward, epenalty = spawn_enemy()
enemy_x = random.randint(0, WIDTH - esize)
enemy_y = -esize

running = True

# Main loop
while running:
    clock.tick(60)
    reward = 0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    state = get_state(player_x, enemy_x, enemy_y, etype)

    if mode == "AI":
        action = choose_action(state)
    else:
        action = "STAY"
        if keys[pygame.K_LEFT]:
            action = "LEFT"
        if keys[pygame.K_RIGHT]:
            action = "RIGHT"
        if keys[pygame.K_SPACE]:
            action = "SHOOT"

    # Perform actions
    if action == "LEFT":
        player_x -= PLAYER_SPEED
    if action == "RIGHT":
        player_x += PLAYER_SPEED
    if action == "SHOOT":
        bullets.append(pygame.Rect(player_x + 23, PLAYER_Y, 4, 12))

    player_x = max(0, min(WIDTH - 50, player_x))

    # Behavior shaping
    if action == "STAY":
        reward -= 0.1

    if abs(player_x - enemy_x) < 20:
        reward += 0.2

    if action == "SHOOT" and abs(player_x - enemy_x) > 30:
        reward -= 0.2

    # Boundary penalty
    if player_x <= 5 or player_x >= WIDTH - 55:
        reward -= 0.3

    if action == "STAY" and (player_x <= 5 or player_x >= WIDTH - 55):
        reward -= 0.3

    # Bullet
    for b in bullets[:]:
        b.y -= BULLET_SPEED
        if b.y < 0:
            bullets.remove(b)

    # Enemy aircraft
    enemy_y += espeed
    enemy_rect = pygame.Rect(enemy_x, enemy_y, esize, esize)
    player_rect = pygame.Rect(player_x, PLAYER_Y, 50, 50)

    if enemy_y > HEIGHT:
        etype, esize, espeed, ereward, epenalty = spawn_enemy()
        enemy_x = random.randint(0, WIDTH - esize)
        enemy_y = -esize

    # Hit
    for b in bullets[:]:
        if b.colliderect(enemy_rect):
            reward += ereward
            score += ereward
            bullets.remove(b)
            etype, esize, espeed, ereward, epenalty = spawn_enemy()
            enemy_x = random.randint(0, WIDTH - esize)
            enemy_y = -esize

    # Plane crash
    if player_rect.colliderect(enemy_rect):
        reward += epenalty
        score += epenalty
        lives -= 1

        if lives <= 0:
            screen.fill((0, 0, 0))
            text = big_font.render("GAME OVER", True, (255, 0, 0))
            screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2))
            pygame.display.flip()
            time.sleep(2)
            break

        etype, esize, espeed, ereward, epenalty = spawn_enemy()
        enemy_x = random.randint(0, WIDTH - esize)
        enemy_y = -esize

    next_state = get_state(player_x, enemy_x, enemy_y, etype)

    if mode == "AI":
        update_q(state, action, reward, next_state)
        EPSILON = max(MIN_EPSILON, EPSILON * EPSILON_DECAY)
        save_q_table(Q, "q_table.pkl")

    last_reward = reward

    # Draw
    screen.fill((0, 0, 0))
    screen.blit(player_img, (player_x, PLAYER_Y))
    screen.blit(enemy_imgs[etype], (enemy_x, enemy_y))

    for b in bullets:
        pygame.draw.rect(screen, (255, 255, 0), b)

    for i in range(lives):
        screen.blit(life_icon, (10 + i * 30, 10))

    info = [
        f"Mode: {mode}",
        f"Score: {score}",
        f"Last Reward: {last_reward:.1f}",
        f"Epsilon: {EPSILON:.2f}"
    ]

    for i, t in enumerate(info):
        screen.blit(font.render(t, True, (255, 255, 255)), (10, 50 + i * 24))

    pygame.display.flip()

pygame.quit()
