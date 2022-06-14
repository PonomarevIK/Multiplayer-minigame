import pygame as game
from numpy import array as np_arr
from numpy import linalg as np_linalg
import math
from collections import deque
from itertools import pairwise, islice
from constants import *
import socket
import pickle


class Network:
    def __init__(self, host="localhost", port=9999):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = port
        self.address = (self.host, self.port)
        self.client_id = None
        self.other_players = []

    def request_id(self) -> str:
        if self.host == "0":  # offline mode for testing
            return "0"

        print("Connecting...")
        try:
            self.socket.connect(self.address)
            print(f"Successfully connected to {self.host}:{self.port}")
            return self.socket.recv(1024).decode()
        except socket.error as error:
            print(error)

    def send(self, data: bytes):
        if self.host == "0":  # offline mode for testing
            return

        try:
            self.socket.send(data)
            self.process_response(self.socket.recv(1024))
        except socket.error as error:
            print(error)

    def process_response(self, data: bytes):
        """Responses from server come in a form of player_id-action1:action1_data;action2:action2_data ..."""
        if data == b"empty":  # if there are no other players
            return

        sender_id, _, actions = data.partition(b"-")
        for message in actions.split(b";"):
            action, _, action_data = message.partition(b":")

            if action == b"idle":
                return
            elif action == b"joined":
                entities.add(Enemy(sender_id))
            elif action == b"move":
                pos_x, _, pos_y = action_data.partition(b",")
                for entity in entities:
                    if isinstance(entity, Enemy) and entity.id == int(sender_id):
                        entity.move(int(pos_x), int(pos_y))
                        break
            elif action == b"shoot":
                origin_x, origin_y, target_x, target_y = action_data.split(b",", maxsplit=3)
                entities.add(Bullet((int(origin_x), int(origin_y)),
                                    (int(target_x), int(target_y)), is_hostile=True))
            elif action == b"wall":
                entities.add(Wall.unpickle(action_data))
            elif action == b"quit":
                for entity in entities:
                    if isinstance(entity, Enemy) and entity.id == int(sender_id):
                        print(f"Player #{sender_id!s} left the game")
                        entity.kill()
                        break


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
        self.image = game.image.load("graphics/player.png")
        self.rect = self.image.get_rect(center=SPAWN_POSITIONS[self.id])
        self.health = 3
        self.bullet_cooldown = 0
        self.wall = None

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
            move_back = False
            for entity in entities:
                if entity is self:
                    continue
                if isinstance(entity, Wall):
                    if Collide.rect_and_wall(self.rect, entity):
                        move_back = True
                        break
                elif isinstance(entity, Player):
                    if self.rect.colliderect(entity.rect):
                        move_back = True
                        break
            if move_back:
                self.rect.move_ip(-x_velocity, -y_velocity)
            else:
                message_buffer.append(f"move:{self.rect.x},{self.rect.y}".encode())

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
            message_buffer.append(f"shoot:{self.rect.center[0]},{self.rect.center[1]},{target[0]},{target[1]}".encode())


class Enemy(Player):
    def __init__(self, id):
        Player.__init__(self, id)
        self.image = game.image.load("graphics/enemy.png")
        self.rect = self.image.get_rect(center=SPAWN_POSITIONS[self.id])
        self.health = 3

    def move(self, x, y):
        self.rect.move_ip(x - self.rect.x, y - self.rect.y)

    def update(self):
        game.sprite.Sprite.update(self)


class Bullet(game.sprite.Sprite):
    def __init__(self, origin: tuple[int, int], target: tuple[int, int], is_hostile=False):
        game.sprite.Sprite.__init__(self)
        self.origin = np_arr(origin, dtype=float)
        self.vector = np_arr([target[0] - origin[0], target[1] - origin[1]], dtype=float)
        self.vector = self.vector * BULLET_LENGTH / np_linalg.norm(self.vector)
        self.is_hostile = is_hostile
        sounds["pew"].play()

    def update(self):
        game.draw.line(screen, color="red" if self.is_hostile else "green",
                       start_pos=self.origin, end_pos=self.origin+self.vector, width=7)
        self.origin += BULLET_SPEED * self.vector
        if not screen.get_rect().collidepoint(tuple(self.origin)):
            self.kill()

        for entity in entities:
            if isinstance(entity, Wall):
                if not Collide.wall_and_line(entity, tuple(self.origin), tuple(self.origin+self.vector)):
                    continue
                # upon hitting a wall bullet bounces and becomes hostile - now it can also damage the shooter
                entity.take_damage()
                self.vector = -self.vector
                self.is_hostile = True
            elif isinstance(entity, Player):
                if not Collide.rect_and_line(entity.rect, tuple(self.origin), tuple(self.origin + self.vector)):
                    continue
                self.kill()
                if isinstance(entity, Enemy) or self.is_hostile:
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
    @classmethod
    def unpickle(cls, pickled_wall):
        pickled_nodes = pickle.loads(pickled_wall)
        new_wall = Wall(pickled_nodes[0])
        for node in islice(pickled_nodes, 1, None):
            new_wall.append(node)
        new_wall.activate(send_to_server=False)
        return new_wall

    def __init__(self, first_node: WallNode):
        game.sprite.Sprite.__init__(self)
        self.nodes = deque((first_node,))
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

    def kill(self, silent=False):
        if not silent:
            sounds["wall_break"].play()
        game.sprite.Sprite.kill(self)
        player.wall = None

    def take_damage(self):
        self.health -= 1
        if self.health > 0:
            sounds["wall_hit"].play()
        else:
            self.kill(silent=False)

    def activate(self, send_to_server=True):
        self.drawing_mode = False
        self.is_active = True
        self.color = WALL_COLOR_ACTIVE
        self.rect = self.get_rect()
        if len(self.nodes) < 2:
            self.kill(silent=True)
            return
        for entity in entities:
            if isinstance(entity, Player):
                if Collide.rect_and_wall(entity.rect, self):
                    self.kill(silent=False)
                    return
        if send_to_server:
            message_buffer.append(b"wall:" + pickle.dumps(self.nodes))

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


# network
server_ip = input("Enter server ip (leave blank for localhost): ") or "localhost"
network = Network(server_ip, 9999)
client_id = network.request_id()

# Initialisation
game.init()
running = True
screen = game.display.set_mode(size=(WND_WIDTH, WND_HEIGHT))
game.display.set_caption(GAME_TITLE)

# Game objects
clock = game.time.Clock()
player = Player(client_id)
entities = game.sprite.Group(player)
message_buffer = deque()

# Resources
heart = game.image.load("Graphics/heart.png")
font = game.font.Font("Fonts/Pixeltype.ttf", 40)
sounds = {"pew": game.mixer.Sound("Sounds/pew.wav"),
          "wall_hit": game.mixer.Sound("Sounds/wall_hit.wav"),
          "wall_break": game.mixer.Sound("Sounds/wall_break.wav"),
          "player_damage": game.mixer.Sound("Sounds/player_damage.wav")}

# Game Loop
while running:
    screen.fill("white")
    message_buffer.clear()

    for event in game.event.get():
        if event.type == game.QUIT:
            running = False

        elif event.type == game.KEYDOWN:
            if event.key == game.K_ESCAPE:
                game.event.post(game.event.Event(game.QUIT))

        elif event.type == game.MOUSEBUTTONDOWN:
            if event.button == 1:
                if player.wall:
                    player.wall.kill()
                player.wall = Wall(WallNode(event.pos))
                entities.add(player.wall)
            elif event.button == 3:
                player.shoot(event.pos)

        elif event.type == game.MOUSEMOTION:
            if player.wall and player.wall.drawing_mode:
                player.wall.append(WallNode(event.pos))

        elif event.type == game.MOUSEBUTTONUP:
            if event.button == 1:
                if player.wall and player.wall.drawing_mode:
                    player.wall.activate()

        elif event.type == game.WINDOWLEAVE:
            if player.wall and player.wall.drawing_mode:
                player.wall.kill()

    # fps display
    fps_surf = font.render(f"{int(clock.get_fps())}", False, "black")
    fps_rect = fps_surf.get_rect(topleft=(0, 0))
    screen.blit(fps_surf, fps_rect)

    # health display
    for i in range(player.health):
        screen.blit(heart, heart.get_rect(topright=(WND_WIDTH - i * heart.get_width(), 0)))

    # update and draw all entities
    entities.update()
    for entity in entities:
        if hasattr(entity, "image"):
            screen.blit(entity.image, entity.rect)

    if len(message_buffer) == 0:
        network.send(b"idle:")
    else:
        network.send(b";".join(message_buffer))

    game.display.update()
    clock.tick(60)

network.send(b"quit:")
game.quit()
