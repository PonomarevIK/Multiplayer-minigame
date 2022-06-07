import pygame as game
from numpy import array as nparr
from numpy import linalg as nplinalg
import math
from collections import deque
from itertools import pairwise
from constants import *
from network import Network


class Collide:
    """Methods to check for collision between various game objects"""
    @staticmethod
    def rect_and_wall(rect, wall):
        if (not wall.is_active) or (not rect.colliderect(wall.rect)):
            return False
        for node1, node2 in pairwise(wall.nodes):
            if rect.clipline(node1.pos, node2.pos):
                return True
        return False

    @staticmethod
    def rect_and_line(rect, line_start: tuple, line_end: tuple):
        return rect.clipline(line_start, line_end)

    @staticmethod
    def wall_and_line(wall, line_start: tuple, line_end: tuple):
        if (not wall.is_active) or (not wall.rect.clipline(line_start, line_end)):
            return False
        for node1, node2 in pairwise(wall.nodes):
            if intersect(line_start, line_end, node1.pos, node2.pos):
                return True
        return False


class Player(game.sprite.Sprite):
    def __init__(self, id):
        game.sprite.Sprite.__init__(self)
        self.id = int(id)
        self.image = game.image.load('graphics/player.png')
        self.rect = self.image.get_rect(center=SPAWN_POSITIONS[self.id])
        self.health = 3
        self.bullet_cooldown = 0
        self.wall = game.sprite.GroupSingle()

    @property
    def is_alive(self) -> bool:
        return self.health > 0

    def update(self):
        # reduce bullet cooldown
        if self.bullet_cooldown > 0:
            self.bullet_cooldown -= 1

        # process keyboard input
        keys_state = game.key.get_pressed()
        x_velocity = PLAYER_SPEED * (keys_state[game.K_d] - keys_state[game.K_a])
        y_velocity = PLAYER_SPEED * (keys_state[game.K_s] - keys_state[game.K_w])

        if x_velocity or y_velocity:
            self.rect.move_ip(x_velocity, y_velocity)

            # check if player is trying to move outside the window bounds
            if self.rect.bottom > WND_HEIGHT:
                self.rect.bottom = WND_HEIGHT
            if self.rect.top < 0:
                self.rect.top = 0
            if self.rect.right > WND_WIDTH:
                self.rect.right = WND_WIDTH
            if self.rect.left < 0:
                self.rect.left = 0

            # check collision with other entities
            for entity in entities:
                if entity is self:
                    continue
                if isinstance(entity, Wall):
                    if Collide.rect_and_wall(self.rect, entity):
                        self.rect.move_ip(-x_velocity, -y_velocity)
                elif isinstance(entity, Player):
                    if self.rect.colliderect(entity.rect):
                        self.rect.move_ip(-x_velocity, -y_velocity)
            network.send(f"{self.id}:move:{self.rect.x},{self.rect.y}")

    def take_damage(self):
        self.health -= 1
        sounds["player_damage"].play()
        if not self.is_alive:
            self.kill()

    def shoot(self, target: tuple[int, int]):
        #   cooldown time is over           otherwise vector would be of length 0
        if (self.bullet_cooldown == 0) and (target != self.rect.center):
            self.bullet_cooldown = BULLET_COOLDOWN
            entities.add(Bullet(self.rect.center, target))
            network.send(f"{self.id}:shoot:{self.rect.center[0]},{self.rect.center[1]},{target[0]},{target[1]}")


class Bullet(game.sprite.Sprite):
    def __init__(self, origin: tuple[int, int], target: tuple[int, int], hostile=False):
        game.sprite.Sprite.__init__(self)
        self.origin = nparr(origin, dtype=float)
        self.vector = nparr([target[0]-origin[0], target[1]-origin[1]], dtype=float)
        self.vector = self.vector * BULLET_LENGTH / nplinalg.norm(self.vector)
        self.hostile = hostile
        self.color = "green"
        sounds["pew"].play()

    def update(self):
        game.draw.line(screen, color=self.color, start_pos=self.origin, end_pos=self.origin+self.vector, width=7)
        self.origin += BULLET_SPEED * self.vector
        if not screen.get_rect().collidepoint(tuple(self.origin)):
            self.kill()

        for entity in entities:
            if isinstance(entity, Wall):
                # upon hitting a wall bullet bounces and becomes hostile - now it can also damage the shoote
                if Collide.wall_and_line(entity, tuple(self.origin), tuple(self.origin+self.vector)):
                    entity.take_damage()
                    self.vector = -self.vector
                    self.hostile = True
                    self.color = "red"
            if isinstance(entity, Player):
                if self.hostile and Collide.rect_and_line(entity.rect, tuple(self.origin), tuple(self.origin+self.vector)):
                    self.kill()
                    entity.take_damage()


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
        game.sprite.Sprite.__init__(self)
        self.nodes = deque((WallNode(first_node),))
        self.total_length = 0.
        self.health = 2
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

    def kill(self, play_sound=True):
        if play_sound:
            sounds["wall_break"].play()
        game.sprite.Sprite.kill(self)

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
        if len(self.nodes) < 2:
            self.kill(False)
        elif Collide.rect_and_wall(player.rect, self):
            self.kill(True)

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


# Return true if line segments AB and CD intersect
def intersect(a, b, c, d) -> bool:
    def ccw(m, n, k):
        return (k[1] - m[1]) * (n[0] - m[0]) > (n[1] - m[1]) * (k[0] - m[0])
    return ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d)


# Initialisation
game.init()
running = True
screen = game.display.set_mode(size=(WND_WIDTH, WND_HEIGHT))
game.display.set_caption(GAME_TITLE)

# Game objects
network = Network("0", 9999)
clock = game.time.Clock()
player = Player(network.request_id())
entities = game.sprite.Group(player)

# Resources
heart = game.image.load("Graphics/heart.png")
font = game.font.Font("Fonts/Pixeltype.ttf", 40)
sounds = {"pew": game.mixer.Sound("Sounds/pew.wav"),
          "wall_hit": game.mixer.Sound("Sounds/wall_hit.wav"),
          "wall_break": game.mixer.Sound("Sounds/wall_break.wav"),
          "player_damage": game.mixer.Sound("Sounds/player_damage.wav")}

# Game Loop
while running:
    screen.fill('white')

    for event in game.event.get():
        if event.type == game.QUIT:
            running = False

        elif event.type == game.KEYDOWN:
            if event.key == game.K_ESCAPE:
                game.event.post(game.event.Event(game.QUIT))

        elif event.type == game.MOUSEBUTTONDOWN:
            if event.button == 1:
                if player.wall:
                    player.wall.sprite.kill()
                player.wall.add(Wall(event.pos))
                entities.add(player.wall.sprite)
            elif event.button == 3:
                player.shoot(event.pos)

        elif event.type == game.MOUSEMOTION:
            if player.wall and player.wall.sprite.drawing_mode:
                player.wall.sprite.append(WallNode(event.pos))

        elif event.type == game.MOUSEBUTTONUP:
            if event.button == 1:
                if player.wall and player.wall.sprite.drawing_mode:
                    player.wall.sprite.activate()

        elif event.type == game.WINDOWLEAVE:
            if player.wall and player.wall.sprite.drawing_mode:
                player.wall.sprite.kill()

    # fps display
    fps_surf = font.render(f'{int(clock.get_fps())}', False, 'black')
    fps_rect = fps_surf.get_rect(topleft=(0, 0))
    screen.blit(fps_surf, fps_rect)

    # health display
    for i in range(player.health):
        screen.blit(heart, heart.get_rect(topright=(WND_WIDTH - i * heart.get_width(), 0)))

    # update all entities
    entities.update()
    for entity in entities:
        if hasattr(entity, "image"):
            screen.blit(entity.image, entity.rect)

    game.display.update()
    clock.tick(60)

game.quit()
