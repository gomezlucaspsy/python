import math
import sys
from dataclasses import dataclass

import pygame


MAP_GRID = [
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2],
    [2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2],
    [2, 0, 0, 3, 3, 3, 0, 0, 0, 4, 0, 2],
    [2, 0, 0, 3, 0, 3, 0, 0, 0, 4, 0, 2],
    [2, 0, 0, 3, 0, 3, 0, 0, 0, 4, 0, 2],
    [2, 0, 0, 3, 3, 3, 0, 0, 0, 4, 0, 2],
    [2, 0, 0, 0, 0, 0, 0, 5, 5, 5, 0, 2],
    [2, 0, 0, 0, 0, 0, 0, 5, 0, 5, 0, 2],
    [2, 0, 0, 0, 0, 0, 0, 5, 5, 5, 0, 2],
    [2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2],
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
]


@dataclass
class Drone:
    x: float = 2.5
    y: float = 2.5
    z: float = 0.7
    yaw: float = 0.0


class DroneSimulator:
    def __init__(self) -> None:
        pygame.init()
        self.screen_width = 1100
        self.screen_height = 700
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("3D Drone Simulator (Raycasting)")
        self.clock = pygame.time.Clock()

        self.fov = math.radians(70)
        self.half_fov = self.fov * 0.5
        self.max_distance = 24.0
        self.ray_step = 2
        self.proj_plane = (self.screen_width * 0.5) / math.tan(self.half_fov)

        self.drone = Drone()
        self.move_speed = 3.8
        self.strafe_speed = 3.2
        self.turn_speed = 1.9
        self.vertical_speed = 1.5
        self.collision_radius = 0.20

        self.font = pygame.font.SysFont("consolas", 20)
        self.small_font = pygame.font.SysFont("consolas", 16)

    @staticmethod
    def world_height(cell_value: int) -> float:
        if cell_value <= 0:
            return 0.0
        return 0.4 * cell_value

    @staticmethod
    def in_bounds(x: int, y: int) -> bool:
        return 0 <= y < len(MAP_GRID) and 0 <= x < len(MAP_GRID[0])

    def cell_at(self, x: float, y: float) -> int:
        gx, gy = int(x), int(y)
        if not self.in_bounds(gx, gy):
            return 2
        return MAP_GRID[gy][gx]

    def can_move_to(self, x: float, y: float) -> bool:
        points = [
            (x, y),
            (x + self.collision_radius, y),
            (x - self.collision_radius, y),
            (x, y + self.collision_radius),
            (x, y - self.collision_radius),
        ]
        return all(self.cell_at(px, py) == 0 for px, py in points)

    def cast_single_ray(self, angle: float) -> tuple[float, float, int]:
        ray_x = self.drone.x
        ray_y = self.drone.y
        step = 0.02
        sin_a = math.sin(angle)
        cos_a = math.cos(angle)

        distance = 0.0
        side = 0

        while distance < self.max_distance:
            ray_x += cos_a * step
            ray_y += sin_a * step
            distance += step

            gx, gy = int(ray_x), int(ray_y)
            if not self.in_bounds(gx, gy):
                return self.max_distance, 0.0, side

            cell = MAP_GRID[gy][gx]
            if cell > 0:
                frac_x = ray_x - gx
                frac_y = ray_y - gy
                edge_dist = min(frac_x, 1.0 - frac_x, frac_y, 1.0 - frac_y)
                side = 1 if edge_dist == min(frac_x, 1.0 - frac_x) else 0
                return distance, self.world_height(cell), side

        return self.max_distance, 0.0, side

    def handle_input(self, dt: float) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return False

        keys = pygame.key.get_pressed()

        if keys[pygame.K_q]:
            self.drone.yaw -= self.turn_speed * dt
        if keys[pygame.K_e]:
            self.drone.yaw += self.turn_speed * dt

        forward_x = math.cos(self.drone.yaw)
        forward_y = math.sin(self.drone.yaw)
        right_x = -forward_y
        right_y = forward_x

        vx = 0.0
        vy = 0.0

        if keys[pygame.K_w]:
            vx += forward_x * self.move_speed * dt
            vy += forward_y * self.move_speed * dt
        if keys[pygame.K_s]:
            vx -= forward_x * self.move_speed * dt
            vy -= forward_y * self.move_speed * dt
        if keys[pygame.K_a]:
            vx -= right_x * self.strafe_speed * dt
            vy -= right_y * self.strafe_speed * dt
        if keys[pygame.K_d]:
            vx += right_x * self.strafe_speed * dt
            vy += right_y * self.strafe_speed * dt

        next_x = self.drone.x + vx
        next_y = self.drone.y + vy

        if self.can_move_to(next_x, self.drone.y):
            self.drone.x = next_x
        if self.can_move_to(self.drone.x, next_y):
            self.drone.y = next_y

        if keys[pygame.K_r]:
            self.drone.z += self.vertical_speed * dt
        if keys[pygame.K_f]:
            self.drone.z -= self.vertical_speed * dt

        self.drone.z = max(0.2, min(2.5, self.drone.z))
        self.drone.yaw %= math.tau
        return True

    def draw_background(self) -> None:
        self.screen.fill((0, 0, 0))
        horizon = int(self.screen_height * 0.5 + (0.9 - self.drone.z) * 90)
        pygame.draw.rect(self.screen, (88, 145, 205), (0, 0, self.screen_width, horizon))
        pygame.draw.rect(
            self.screen,
            (30, 30, 30),
            (0, horizon, self.screen_width, self.screen_height - horizon),
        )

    def draw_world(self) -> None:
        self.draw_background()

        for screen_x in range(0, self.screen_width, self.ray_step):
            camera_x = (screen_x / self.screen_width) - 0.5
            ray_angle = self.drone.yaw + camera_x * self.fov
            raw_dist, wall_height, side = self.cast_single_ray(ray_angle)
            dist = raw_dist * math.cos(ray_angle - self.drone.yaw)
            if dist < 0.001:
                dist = 0.001

            if wall_height <= 0.0:
                continue

            top_world = wall_height
            bottom_world = 0.0
            y_top = int(self.screen_height * 0.5 - ((top_world - self.drone.z) / dist) * self.proj_plane)
            y_bottom = int(self.screen_height * 0.5 - ((bottom_world - self.drone.z) / dist) * self.proj_plane)

            y_top = max(-2000, min(self.screen_height + 2000, y_top))
            y_bottom = max(-2000, min(self.screen_height + 2000, y_bottom))

            if y_bottom < y_top:
                y_top, y_bottom = y_bottom, y_top

            shade = max(35, int(255 / (1.0 + dist * 0.22)))
            if side == 1:
                shade = int(shade * 0.8)
            wall_color = (shade, int(shade * 0.85), int(shade * 0.6))

            pygame.draw.rect(
                self.screen,
                wall_color,
                (screen_x, y_top, self.ray_step + 1, max(1, y_bottom - y_top)),
            )

    def draw_minimap(self) -> None:
        tile = 14
        map_w = len(MAP_GRID[0]) * tile
        map_h = len(MAP_GRID) * tile

        panel = pygame.Surface((map_w + 20, map_h + 20), pygame.SRCALPHA)
        panel.fill((10, 10, 10, 190))
        self.screen.blit(panel, (14, 14))

        for y, row in enumerate(MAP_GRID):
            for x, cell in enumerate(row):
                color = (26, 26, 26) if cell == 0 else (130, 130, 130)
                if cell >= 4:
                    color = (155, 120, 80)
                pygame.draw.rect(
                    self.screen,
                    color,
                    (24 + x * tile, 24 + y * tile, tile - 1, tile - 1),
                )

        px = 24 + self.drone.x * tile
        py = 24 + self.drone.y * tile

        pygame.draw.circle(self.screen, (80, 220, 130), (int(px), int(py)), 4)
        look_x = px + math.cos(self.drone.yaw) * 12
        look_y = py + math.sin(self.drone.yaw) * 12
        pygame.draw.line(self.screen, (80, 220, 130), (px, py), (look_x, look_y), 2)

        sensor_count = 17
        start_angle = self.drone.yaw - math.radians(45)
        end_angle = self.drone.yaw + math.radians(45)
        for i in range(sensor_count):
            t = i / (sensor_count - 1)
            angle = start_angle + t * (end_angle - start_angle)
            dist, _, _ = self.cast_single_ray(angle)
            ray_end_x = px + math.cos(angle) * dist * tile
            ray_end_y = py + math.sin(angle) * dist * tile
            pygame.draw.line(self.screen, (240, 210, 70), (px, py), (ray_end_x, ray_end_y), 1)

    def draw_hud(self, fps: float) -> None:
        info_lines = [
            f"POS: ({self.drone.x:.2f}, {self.drone.y:.2f})",
            f"ALTITUDE: {self.drone.z:.2f} m",
            f"YAW: {math.degrees(self.drone.yaw):.1f} deg",
            f"FPS: {fps:.0f}",
            "Controls: W/S move, A/D strafe, Q/E yaw, R/F altitude, ESC quit",
        ]

        y = self.screen_height - 120
        for line in info_lines:
            text_surface = self.font.render(line, True, (230, 230, 230))
            self.screen.blit(text_surface, (20, y))
            y += 24

        title = self.small_font.render("Raycast Drone Simulator", True, (240, 240, 255))
        self.screen.blit(title, (20, 20 + len(MAP_GRID) * 14 + 10))

    def run(self) -> None:
        while True:
            dt = self.clock.tick(60) / 1000.0
            if not self.handle_input(dt):
                break

            self.draw_world()
            self.draw_minimap()
            self.draw_hud(self.clock.get_fps())
            pygame.display.flip()

        pygame.quit()


def main() -> None:
    simulator = DroneSimulator()
    simulator.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pygame.quit()
        sys.exit(0)
