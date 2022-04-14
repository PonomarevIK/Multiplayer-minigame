import pygame as game
from math import dist
import numpy as np
from collections import deque
from itertools import pairwise
from sympy.geometry.point import Point2D

# Constants
WND_WIDTH = 900
WND_HEIGHT = 700
WND_CENTER = (WND_WIDTH/2, WND_HEIGHT/2)
GAME_NAME = "Drawl Stars"
PLAYER_SPEED = 5
BULLET_SPEED = 0.4
BULLET_LENGTH = 50
WALL_MAX_LENGTH = 120
WALL_COLOR_INACTIVE = (150, 150, 150)
WALL_COLOR_ACTIVE = (165, 42, 42)


# Classes
class Player(game.sprite.Sprite):
    def __init__(self, start_pos):
        super().__init__()
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
    def __init__(self, origin: tuple[int, int], target: tuple[int, int]):
        super().__init__()
        self.origin = np.array(origin, dtype=float)
        self.vector = np.array([origin[0]-target[0], origin[1]-target[1]], dtype=float)
        self.vector = self.vector * BULLET_LENGTH / np.linalg.norm(self.vector)
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


class WallNode:
    """A 2d point that will be connected to other wall nodes with lines to form a dynamically drawable wall.
    Distance to next wall node is stored to avoid having to calculate it twice when 1.adding and 2.deleting this node"""
    def __init__(self, pos: tuple[int, int]):
        self.pos = pos
        self.dist_to_next = 0.0

    @property
    def x(self):
        return self.pos[0]

    @property
    def y(self):
        return self.pos[1]


# TODO: fix bug where a straight wall ignores collision
class Wall(game.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.nodes = deque()
        self.total_length = 0.0
        self.active = False
        self.rect = game.rect.Rect(0, 0, 0, 0)

    def append(self, new_node: WallNode):
        if len(self.nodes):
            self.nodes[-1].dist_to_next = dist(self.nodes[-1].pos, new_node.pos)
            self.total_length += self.nodes[-1].dist_to_next
        self.nodes.append(new_node)

        while self.total_length > WALL_MAX_LENGTH:
            self.total_length -= self.nodes[0].dist_to_next
            self.nodes.popleft()

    def clear(self):
        self.nodes.clear()
        self.active = False
        self.total_length = 0.0
        self.rect.update(0, 0, 0, 0)

    # TODO: check for redundancy in event loop
    def update(self):
        if len(self.nodes) == 0:
            return
        color = WALL_COLOR_ACTIVE if self.active else WALL_COLOR_INACTIVE
        if len(self.nodes) == 1:
            game.draw.circle(screen, color=color, center=self.nodes[0].pos, radius=3)
        else:
            for node1, node2 in pairwise(self.nodes):
                game.draw.line(screen, color=color, start_pos=node1.pos, end_pos=node2.pos, width=7)

    # TODO: check this for bugs and event loop for redundancy
    def get_rect(self):
        if len(self.nodes) < 2:
            return game.rect.Rect(0, 0, 0, 0)

        min_x = min(node.x for node in self.nodes)
        min_y = min(node.y for node in self.nodes)
        max_x = max(node.x for node in self.nodes)
        max_y = max(node.y for node in self.nodes)
        return game.rect.Rect(min_x, min_y, max_x - min_x, max_y - min_y)

    def check_collision_rect(self, rect):
        if not self.active:
            return False
        if not self.rect.colliderect(rect):
            return False
        for node1, node2 in pairwise(self.nodes):
            if rect.clipline(node1.pos, node2.pos):
                return True
        return False

    # TODO: check intersection using sympy
    def check_collision_line(self, a, b):
        if not self.active:
            return False
        if not self.rect.clipline(a, b):
            return False
        for node1, node2 in pairwise(self.nodes):
            if intersect(a, b, node1.pos, node2.pos):
                return True
        return False


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
                wall.clear()
                drawing = True
                wall.append(WallNode(event.pos))
            elif event.button == 3:
                player.shoot(event.pos)

        elif event.type == game.MOUSEMOTION and drawing:
            wall.append(WallNode(event.pos))

        elif event.type == game.MOUSEBUTTONUP:
            if event.button == 1 and drawing:
                drawing = False
                wall.active = True
                wall.rect.update(wall.get_rect())
                if len(wall.nodes) == 1 or wall.check_collision_rect(player.rect):
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
