import pygame as game
from sys import exit
import math
import numpy as np
from collections import deque
from itertools import pairwise, cycle
from constants import *


# Classes
class Player(game.sprite.Sprite):
    def __init__(self, spawn_pos: tuple[int, int]):
        super().__init__()
        self.image = game.image.load('graphics/player1.png')
        self.rect = self.image.get_rect(center=spawn_pos)
        self.movement_vector = np.array((0, 0))
        self.health = 3
        self.bullet_cooldown = 0

    @property
    def is_alive(self) -> bool:
        return self.health > 0

    def update(self):
        # reduce bullet cooldown
        if self.bullet_cooldown:
            self.bullet_cooldown -= 1

        # process keyboard input
        keys_state = game.key.get_pressed()
        self.movement_vector[0] = PLAYER_SPEED * (keys_state[game.K_d] - keys_state[game.K_a])
        self.movement_vector[1] = PLAYER_SPEED * (keys_state[game.K_s] - keys_state[game.K_w])

        if self.movement_vector.any():
            self.rect.move_ip(self.movement_vector)

            # check if player is trying to move outside the window bounds
            if self.rect.bottom > WND_HEIGHT:
                self.rect.bottom = WND_HEIGHT
            if self.rect.top < 0:
                self.rect.top = 0
            if self.rect.right > WND_WIDTH:
                self.rect.right = WND_WIDTH
            if self.rect.left < 0:
                self.rect.left = 0

            # check collision with walls and other players
            for wall_iter in walls:
                if wall_iter.check_collision_rect(self.rect):
                    self.rect.move_ip(-self.movement_vector)

    def take_damage(self):
        self.health -= 1
        if not self.is_alive:
            self.kill()

    def shoot(self, target: tuple[int, int]):
        if self.bullet_cooldown == 0:
            self.bullet_cooldown = BULLET_COOLDOWN
            bullets.add(Bullet(self.rect.center, target))


class Bullet(game.sprite.Sprite):
    def __init__(self, origin: tuple[int, int], target: tuple[int, int]):
        super().__init__()
        self.origin = np.array(origin, dtype=float)
        self.vector = np.array([target[0]-origin[0], target[1]-origin[1]], dtype=float)
        self.vector = self.vector * BULLET_LENGTH / np.linalg.norm(self.vector)
        self.hostile = False
        sounds["pew"].play()

    def update(self):
        game.draw.line(screen, color='red', start_pos=self.origin, end_pos=self.origin+self.vector, width=7)
        self.origin += BULLET_SPEED * self.vector
        if not screen.get_rect().collidepoint(tuple(self.origin)):
            self.kill()
        for wall_iter in walls:
            if wall_iter.check_collision_line(tuple(self.origin), tuple(self.origin+self.vector)):
                wall_iter.take_damage()
                self.vector = -self.vector
                self.hostile = True
        for player_iter in players:
            if self. hostile and player_iter.rect.clipline(self.origin, self.origin+self.vector):
                self.kill()
                player_iter.take_damage()


class WallNode:
    """A 2D point that will be connected to other wall nodes with lines to form a dynamically drawable wall. Distance
    to next node will be stored to avoid having to calculate it twice when adding and later deleting this node"""
    def __init__(self, pos: tuple[int, int]):
        self.pos = pos
        self.dist_to_next = 0.

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
    def __init__(self, first_node: tuple[int, int]):
        super().__init__()
        self.nodes = deque((WallNode(first_node),))
        self.total_length = 0.
        self.health = 3
        self.is_active = False
        self.drawing_mode = True
        self.color = WALL_COLOR_INACTIVE

    def append(self, new_node: WallNode):
        self.nodes[-1].dist_to_next = math.dist(self.nodes[-1].pos, new_node.pos)
        self.total_length += self.nodes[-1].dist_to_next
        self.nodes.append(new_node)
        while self.total_length > WALL_MAX_LENGTH:
            self.total_length -= self.nodes[0].dist_to_next
            self.nodes.popleft()

    def kill(self):
        sounds["wall_break"].play()
        super().kill()

    def take_damage(self):
        self.health -= 1
        if self.health > 0:
            sounds["wall_hit"].play()
        else:
            self.kill()

    def activate(self):
        self.drawing_mode = False
        self.is_active = True
        self.color = WALL_COLOR_ACTIVE
        self.rect = self.get_rect()
        if (len(self.nodes) < 2) or self.check_collision_rect(player.rect):
            self.kill()

    def update(self):
        if len(self.nodes) == 1:
            game.draw.circle(screen, color=self.color, center=self.nodes[0].pos, radius=3)
        else:
            for node1, node2 in pairwise(self.nodes):
                game.draw.line(screen, color=self.color, start_pos=node1.pos, end_pos=node2.pos, width=7)

    def get_rect(self):
        min_x = min(node.x for node in self.nodes)
        min_y = min(node.y for node in self.nodes)
        max_x = max(node.x for node in self.nodes)
        max_y = max(node.y for node in self.nodes)
        return game.rect.Rect(min_x-1, min_y-1, max_x - min_x + 1, max_y - min_y + 1)

    def check_collision_rect(self, rect):
        if (not self.is_active) or (not self.rect.colliderect(rect)):
            return False
        for node1, node2 in pairwise(self.nodes):
            if rect.clipline(node1.pos, node2.pos):
                return True
        return False

    def check_collision_line(self, a, b):
        if (not self.is_active) or (not self.rect.clipline(a, b)):
            return False
        for node1, node2 in pairwise(self.nodes):
            if intersect(a, b, node1.pos, node2.pos):
                return True
        return False


def check_collision(sprite1, sprite2) -> bool:
    pass  # TODO


# Return true if line segments AB and CD intersect
def intersect(a, b, c, d) -> bool:
    def ccw(m, n, k):
        return (k[1] - m[1]) * (n[0] - m[0]) > (n[1] - m[1]) * (k[0] - m[0])
    return ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d)


# Initialisation
game.init()
clock = game.time.Clock()
font = game.font.Font("Fonts/Pixeltype.ttf", 40)
sounds = {"pew": game.mixer.Sound("Sounds/pew.wav"),
          "wall_hit": game.mixer.Sound("Sounds/wall_hit.wav"),
          "wall_break": game.mixer.Sound("Sounds/wall_break.wav")
          }
screen = game.display.set_mode(size=(WND_WIDTH, WND_HEIGHT))
game.display.set_caption(GAME_TITLE)

wall = None
player = Player(WND_CENTER)

players = game.sprite.Group(player)
bullets = game.sprite.Group()
walls = game.sprite.Group()


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
                if wall in walls:
                    wall.kill()
                wall = Wall(event.pos)
                walls.add(wall)
            elif event.button == 3:
                player.shoot(event.pos)

        elif event.type == game.MOUSEMOTION:
            if wall and wall.drawing_mode:
                wall.append(WallNode(event.pos))

        elif event.type == game.MOUSEBUTTONUP:
            if event.button == 1 and wall and wall.drawing_mode:
                wall.activate()

        elif event.type == game.WINDOWLEAVE:
            if wall and wall.drawing_mode:
                wall.kill()

    fps_surf = font.render(f'{int(clock.get_fps())}', False, 'black')
    fps_rect = fps_surf.get_rect(topleft=(0, 0))
    screen.blit(fps_surf, fps_rect)

    players.update()
    players.draw(screen)
    bullets.update()
    walls.update()

    game.display.update()
    clock.tick(60)
