import pygame as game
from sys import exit
from math import dist
import numpy as np
from collections import deque
from itertools import pairwise
from constants import *


# Classes
class Player(game.sprite.Sprite):
    def __init__(self, spawn_pos: tuple[int, int]):
        super().__init__()
        self.movement_vector = np.array([0, 0])
        self.is_drawing = False
        self.image = game.image.load('graphics/player1.png')
        self.rect = self.image.get_rect(center=spawn_pos)

    def update(self):
        # process keyboard input
        keys_state = game.key.get_pressed()
        self.movement_vector[0] = PLAYER_SPEED * (keys_state[game.K_d] - keys_state[game.K_a])
        self.movement_vector[1] = PLAYER_SPEED * (keys_state[game.K_s] - keys_state[game.K_w])
        self.rect.move_ip(self.movement_vector)

        # check if player is out of bounds
        if self.rect.bottom > WND_HEIGHT:
            self.rect.bottom = WND_HEIGHT
        if self.rect.top < 0:
            self.rect.top = 0
        if self.rect.right > WND_WIDTH:
            self.rect.right = WND_WIDTH
        if self.rect.left < 0:
            self.rect.left = 0

        # check collision TODO
        if wall.check_collision_rect(self.rect):
            self.rect.move_ip(-self.movement_vector)

    def draw(self, surface):
        surface.blit(self.image, self.rect)

    def shoot(self, target: tuple[int, int]):
        entities.add(Bullet(self.rect.center, target))


class Bullet(game.sprite.Sprite):
    def __init__(self, origin: tuple[int, int], target: tuple[int, int]):
        super().__init__()
        self.origin = np.array(origin, dtype=float)
        self.vector = np.array([target[0]-origin[0], target[1]-origin[1]], dtype=float)
        self.vector = self.vector * BULLET_LENGTH / np.linalg.norm(self.vector)
        sounds["pew"].play()

    def update(self):
        game.draw.line(screen, color='red', start_pos=self.origin, end_pos=self.origin+self.vector, width=7)
        self.origin += BULLET_SPEED*self.vector
        if not screen.get_rect().collidepoint(tuple(self.origin)):
            self.kill()
        if wall.check_collision_line(tuple(self.origin), tuple(self.origin+self.vector)):
            sounds["wall_break"].play()
            self.kill()
            wall.clear()

    def check_collision(self, rect):
        pass


class WallNode:
    """A 2D point that will be connected to other wall nodes with lines to form a dynamically drawable wall.
    Distance to next node is stored to avoid having to calculate it twice when adding and later deleting this node"""
    def __init__(self, pos: tuple[int, int]):
        self.pos = pos
        self.dist_to_next = 0.0

    @property
    def x(self):
        return self.pos[0]

    @property
    def y(self):
        return self.pos[1]


class Wall(game.sprite.Sprite):
    """In-game object consisting of nodes connected by lines. As the player draws, nodes get added to one side
    and deleted from another forming a line of set max length that follows their cursor. Thus, nodes are stored in
    a deque for fast appends and pops"""
    def __init__(self):
        super().__init__()
        self.nodes = deque()
        self.total_length = 0.0
        self.is_active = False
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
        self.is_active = False
        self.total_length = 0.0
        self.rect.update(0, 0, 0, 0)

    # TODO: check for redundancy in event loop
    def update(self):
        if len(self.nodes) == 0:
            return
        color = WALL_COLOR_ACTIVE if self.is_active else WALL_COLOR_INACTIVE
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
        return game.rect.Rect(min_x-1, min_y-1, max_x - min_x + 1, max_y - min_y + 1)

    def check_collision_rect(self, rect):
        if not self.is_active:
            return False
        if not self.rect.colliderect(rect):
            return False
        for node1, node2 in pairwise(self.nodes):
            if rect.clipline(node1.pos, node2.pos):
                return True
        return False

    # TODO: check intersection using sympy
    def check_collision_line(self, a, b):
        if not self.is_active:
            return False
        if not self.rect.clipline(a, b):
            return False
        for node1, node2 in pairwise(self.nodes):
            if intersect(a, b, node1.pos, node2.pos):
                return True
        return False


# Return true if line segments AB and CD intersect
def intersect(a, b, c, d):
    def ccw(m, n, k):
        return (k[1] - m[1]) * (n[0] - m[0]) > (n[1] - m[1]) * (k[0] - m[0])
    return ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d)


# Initialisation
game.init()
clock = game.time.Clock()
font = game.font.Font("Fonts/Pixeltype.ttf", 40)
sounds = {"pew": game.mixer.Sound("Sounds/pew.wav"),
          "wall_hit": game.mixer.Sound("Sounds/wall_hit.wav"),
          "wall_break": game.mixer.Sound("Sounds/wall_break.wav")}
screen = game.display.set_mode(size=(WND_WIDTH, WND_HEIGHT))
game.display.set_caption(GAME_TITLE)

wall = Wall()
player = Player(WND_CENTER)
entities = game.sprite.Group()
entities.add(wall)


# Game Loop
while True:
    screen.fill('white')

    for event in game.event.get():
        if event.type == game.QUIT:
            game.quit()
            exit()

        elif event.type == game.KEYDOWN:
            if event.key == game.K_ESCAPE:
                game.event.post(game.event.Event(game.QUIT))

        elif event.type == game.MOUSEBUTTONDOWN:
            if event.button == 1:
                wall.clear()
                player.is_drawing = True
                wall.append(WallNode(event.pos))
            elif event.button == 3:
                player.shoot(event.pos)

        elif event.type == game.MOUSEMOTION and player.is_drawing:
            wall.append(WallNode(event.pos))

        elif event.type == game.MOUSEBUTTONUP:
            if event.button == 1 and player.is_drawing:
                player.is_drawing = False
                wall.is_active = True  # TODO handle activation and wall color inside wall class?
                wall.rect.update(wall.get_rect())
                if len(wall.nodes) == 1 or wall.check_collision_rect(player.rect):
                    wall.clear()

        elif event.type == game.WINDOWLEAVE and player.is_drawing:
            player.is_drawing = False
            wall.clear()

    fps_surf = font.render(f'{int(clock.get_fps())}', False, 'black')
    fps_rect = fps_surf.get_rect(topleft=(0, 0))
    screen.blit(fps_surf, fps_rect)

    player.update()
    player.draw(screen)
    entities.update()

    game.display.update()
    clock.tick(60)
