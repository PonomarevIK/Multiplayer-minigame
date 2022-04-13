import pygame as game
from math import dist
import numpy as np


# Constants
WND_WIDTH = 900
WND_HEIGHT = 700
WND_CENTER = (WND_WIDTH/2, WND_HEIGHT/2)
GAME_NAME = "Drawl Stars"
PLAYER_SPEED = 5
BULLET_SPEED = 0.4
BULLET_SIZE = 50
WALL_MAX_LENGTH = 120
WALL_COLOR_INACTIVE = (150, 150, 150)
WALL_COLOR_ACTIVE = (165, 42, 42)


# Classes
class Player(game.sprite.Sprite):
    def __init__(self, start_pos):
        game.sprite.Sprite.__init__(self)
        self.movement = {'x': 0, 'y': 0}
        self.image = game.image.load('graphics/player1.png')
        self.rect = self.image.get_rect(center=start_pos)

    def update(self):
        self.rect.x += self.movement['x']
        self.rect.y += self.movement['y']

        if self.rect.bottom > WND_HEIGHT:
            self.rect.bottom = WND_HEIGHT
        if self.rect.top < 0:
            self.rect.top = 0
        if self.rect.right > WND_WIDTH:
            self.rect.right = WND_WIDTH
        if self.rect.left < 0:
            self.rect.left = 0

        for entity in entities:
            if type(entity) == Wall:
                if entity.check_collision_rect(self.rect):
                    self.rect.x -= self.movement['x']
                    self.rect.y -= self.movement['y']

    def shoot(self, pos):
        entities.add(Bullet(self.rect.center, pos))

    def check_collision(self):
        pass


class Bullet(game.sprite.Sprite):
    def __init__(self, a, b):
        game.sprite.Sprite.__init__(self)
        self.origin = np.array(a, dtype=float)
        self.vector = np.array([b[0]-a[0], b[1]-a[1]], dtype=float)
        self.vector = self.vector * BULLET_SIZE / np.linalg.norm(self.vector)
        sound_pew.play()

    def update(self):
        game.draw.line(screen, color='red', start_pos=self.origin, end_pos=self.origin+self.vector, width=7)
        self.origin += BULLET_SPEED*self.vector
        if not screen.get_rect().collidepoint(tuple(self.origin)):
            self.kill()
        if wall.check_collision_line(tuple(self.origin), tuple(self.origin+self.vector)):
            sound_break.play()
            self.kill()
            wall.clear()

    def check_collision(self, rect):
        pass


class Wall(game.sprite.Sprite):
    def __init__(self):
        game.sprite.Sprite.__init__(self)
        self.head = None
        self.tail = None
        self.n = 0
        self.length = 0.0
        self.active = False
        self.rect = game.rect.Rect(0, 0, 0, 0)

    def append(self, pos):
        new_node = WallNode(pos)
        if self.tail:
            self.tail.dist_to_next = dist(pos, self.tail.pos)
            self.length += self.tail.dist_to_next
            self.tail.next = new_node
            new_node.prev = self.tail
            self.tail = new_node
        else:
            self.head = new_node
            self.tail = new_node
        self.n += 1
        while self.length > WALL_MAX_LENGTH:
            self.pop()

    def pop(self):
        if self.head:
            if self.head is self.tail:
                self.head = None
                self.tail = None
                self.length = 0
            else:
                self.length -= self.head.dist_to_next
                self.head = self.head.next
                self.head.prev = None
            self.n -= 1

    def clear(self):
        self.active = False
        self.rect = game.rect.Rect(0, 0, 0, 0)
        while self.head:
            self.pop()

    def update(self):
        color = WALL_COLOR_ACTIVE if self.active else WALL_COLOR_INACTIVE
        if self.head:
            if self.n == 1:
                game.draw.circle(screen, color=color, center=self.head.pos, radius=3)
            else:
                pt = self.head
                while pt.next:
                    game.draw.line(screen, color=color, start_pos=pt.pos, end_pos=pt.next.pos, width=7)
                    pt = pt.next

    def get_rect(self):
        if self.n < 2:
            return game.rect.Rect(0, 0, 0, 0)
        min_x, min_y = WND_WIDTH, WND_HEIGHT
        max_x, max_y = 0, 0
        pt = self.head
        while pt:
            min_x = min(min_x, pt.pos[0])
            min_y = min(min_y, pt.pos[1])
            max_x = max(max_x, pt.pos[0])
            max_y = max(max_y, pt.pos[1])
            pt = pt.next
        return game.rect.Rect(min_x, min_y, max_x-min_x, max_y-min_y)

    def check_collision_rect(self, rect):
        if not self.active:
            return False
        if not self.rect.colliderect(rect):
            return False
        pt = self.head
        while pt.next:
            if rect.clipline(pt.pos, pt.next.pos):
                return True
            pt = pt.next
        return False

    def check_collision_line(self, a, b):
        if not self.active:
            return False
        if not self.rect.clipline(a, b):
            return False
        pt = self.head
        while pt.next:
            if intersect(a, b, pt.pos, pt.next.pos):
                return True
            pt = pt.next
        return False


class WallNode:
    def __init__(self, pos, next=None, prev=None):
        self.pos = pos
        self.next = next
        self.prev = prev
        self.dist_to_next = 0


def ccw(a, b, c):
    return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])


# Return true if line segments AB and CD intersect
def intersect(a, b, c, d):
    return ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d)


# Initialisation
game.init()
clock = game.time.Clock()
font = game.font.Font('Fonts/Pixeltype.ttf', 40)
sound_pew = game.mixer.Sound('Sounds/pew.wav')
sound_break = game.mixer.Sound('Sounds/break.wav')
screen = game.display.set_mode(size=(WND_WIDTH, WND_HEIGHT))
game.display.set_caption(GAME_NAME)

running = True
drawing = False
wall = Wall()
player = Player(WND_CENTER)
entities = game.sprite.Group()
entities.add(player, wall)

# Game Loop
while True:
    screen.fill('white')

    for event in game.event.get():
        if event.type == game.QUIT:
            running = False
            game.quit()
            break

        elif event.type == game.KEYDOWN:
            if event.key == game.K_w:
                player.movement['y'] -= PLAYER_SPEED
            elif event.key == game.K_a:
                player.movement['x'] -= PLAYER_SPEED
            elif event.key == game.K_s:
                player.movement['y'] += PLAYER_SPEED
            elif event.key == game.K_d:
                player.movement['x'] += PLAYER_SPEED
            elif event.key == game.K_ESCAPE:
                game.event.post(game.event.Event(game.QUIT))

        elif event.type == game.KEYUP:
            if event.key == game.K_w:
                player.movement['y'] += PLAYER_SPEED
            elif event.key == game.K_a:
                player.movement['x'] += PLAYER_SPEED
            elif event.key == game.K_s:
                player.movement['y'] -= PLAYER_SPEED
            elif event.key == game.K_d:
                player.movement['x'] -= PLAYER_SPEED

        elif event.type == game.MOUSEBUTTONDOWN:
            if event.button == 1:
                drawing = True
                wall.clear()
                wall.append(event.pos)
            elif event.button == 3:
                player.shoot(event.pos)

        elif event.type == game.MOUSEMOTION and drawing:
            wall.append(event.pos)

        elif event.type == game.MOUSEBUTTONUP:
            if event.button == 1 and drawing:
                drawing = False
                wall.active = True
                wall.rect = wall.get_rect()
                if wall.n == 1 or wall.check_collision_rect(player.rect):
                    wall.clear()

        elif event.type == game.WINDOWLEAVE and drawing:
            drawing = False
            wall.clear()

    if not running:
        break

    fps_surf = font.render(f'{int(clock.get_fps())}', False, 'black')
    fps_rect = fps_surf.get_rect(topleft=(0, 0))
    screen.blit(fps_surf, fps_rect)

    screen.blit(player.image, player.rect)

    entities.update()
    game.display.update()
    clock.tick(60)


# TODO: fix bug where a straight wall ignores collision
