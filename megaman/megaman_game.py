import pygame
import sys
import math
import random

# Initialize Pygame
pygame.init()

# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
DARKBLUE = (0, 0, 139)

# Physics
GRAVITY = 0.5
JUMP_STRENGTH = 15
PLAYER_SPEED = 5
ENEMY_SPEED = 2

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, spritesheet=None, character_index=0):
        super().__init__()
        
        # Load sprite sheet if provided
        if spritesheet is not None:
            try:
                self.spritesheet = spritesheet
                sheet_width = self.spritesheet.get_width()
                sheet_height = self.spritesheet.get_height()
                
                # Calculate sprite size (5 across, 2 rows per character)
                self.sprite_width = sheet_width // 5
                # Determine character height (total height / number of characters)
                # Each character has 2 rows of animation
                self.num_characters = sheet_height // (self.sprite_width * 2)
                self.character_index = character_index % self.num_characters
                self.sprite_height = self.sprite_width  # Square sprites
                
                print(f"Sprite sheet: {sheet_width}x{sheet_height}")
                print(f"Sprite size: {self.sprite_width}x{self.sprite_height}")
                print(f"Characters available: {self.num_characters}")
                print(f"Selected character: {self.character_index + 1}/{self.num_characters}")
                
                self.use_sprites = True
                
                # Extract frames for selected character (5 across, 2 rows)
                self.frames = []
                char_row_start = character_index * 2  # Each character has 2 rows
                
                for row in range(2):
                    for col in range(5):
                        x = col * self.sprite_width
                        y = (char_row_start + row) * self.sprite_height
                        
                        # Ensure we're within bounds
                        if y + self.sprite_height <= sheet_height:
                            frame = self.spritesheet.subsurface(
                                (x, y, self.sprite_width, self.sprite_height)
                            )
                            self.frames.append(frame)
                
                print(f"Extracted {len(self.frames)} frames")
                self.current_frame = 0
                self.animation_counter = 0
                self.image = self.frames[0] if self.frames else pygame.Surface((48, 48))
            except Exception as e:
                print(f"Sprite loading failed: {e}")
                self.use_sprites = False
                self.image = pygame.Surface((48, 48))
                self.image.fill(BLUE)
        else:
            # No sprite sheet provided
            self.use_sprites = False
            self.image = pygame.Surface((48, 48))
            self.image.fill(BLUE)
        
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.max_health = 100
        self.health = self.max_health
        self.shoot_cooldown = 0
        self.direction = 1  # 1 for right, -1 for left
        
    def handle_input(self, keys):
        self.vel_x = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x = -PLAYER_SPEED
            self.direction = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = PLAYER_SPEED
            self.direction = 1
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vel_y = -JUMP_STRENGTH
            self.on_ground = False
    
    def update(self, platforms, enemies):
        # Apply gravity
        self.vel_y += GRAVITY
        self.vel_y = min(self.vel_y, 20)  # Terminal velocity
        
        # Update position
        self.rect.x += self.vel_x
        self.check_collisions_x(platforms)
        
        self.rect.y += self.vel_y
        self.on_ground = False
        self.check_collisions_y(platforms)
        
        # Wrap around screen horizontally
        if self.rect.right < 0:
            self.rect.left = SCREEN_WIDTH
        if self.rect.left > SCREEN_WIDTH:
            self.rect.right = 0
        
        # Die if fall off screen
        if self.rect.top > SCREEN_HEIGHT:
            return False
        
        # Update cooldown
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        
        # Update animation
        if self.use_sprites and self.frames:
            self.animation_counter += 1
            # Change frame every 8 updates (slower animation)
            if self.animation_counter >= 8:
                self.animation_counter = 0
                # Always cycle through frames 
                self.current_frame = (self.current_frame + 1) % len(self.frames)
            
            # Get current frame and flip if moving left
            if self.current_frame < len(self.frames):
                frame = self.frames[self.current_frame]
                if self.direction == -1:
                    frame = pygame.transform.flip(frame, True, False)
                
                # Preserve rect position
                old_rect = self.rect.copy()
                self.image = frame
                self.rect = self.image.get_rect()
                self.rect.topleft = old_rect.topleft
        
        return True
    
    def check_collisions_x(self, platforms):
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vel_x > 0:  # Moving right
                    self.rect.right = platform.rect.left
                elif self.vel_x < 0:  # Moving left
                    self.rect.left = platform.rect.right
    
    def check_collisions_y(self, platforms):
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vel_y > 0:  # Falling
                    self.rect.bottom = platform.rect.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:  # Jumping
                    self.rect.top = platform.rect.bottom
                    self.vel_y = 0
    
    def shoot(self):
        if self.shoot_cooldown <= 0:
            self.shoot_cooldown = 10
            return Projectile(self.rect.centerx, self.rect.centery, self.direction)
        return None
    
    def take_damage(self, damage):
        self.health -= damage
        if self.health < 0:
            self.health = 0
        return self.health > 0
    
    def draw_health(self, surface):
        # Draw health bar
        bar_width = 200
        bar_height = 20
        bar_x = 10
        bar_y = 10
        
        # Background
        pygame.draw.rect(surface, RED, (bar_x, bar_y, bar_width, bar_height))
        # Health
        health_width = (self.health / self.max_health) * bar_width
        pygame.draw.rect(surface, GREEN, (bar_x, bar_y, health_width, bar_height))
        # Border
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 2)
        
        # Draw health text
        font = pygame.font.Font(None, 24)
        text = font.render(f"HP: {int(self.health)}/{int(self.max_health)}", True, WHITE)
        surface.blit(text, (bar_x, bar_y + bar_height + 5))


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, enemy_type="basic"):
        super().__init__()
        self.enemy_type = enemy_type
        
        if enemy_type == "basic":
            self.image = pygame.Surface((32, 32))
            self.image.fill(RED)
            self.health = 20
            self.speed = ENEMY_SPEED
            self.shoot_cooldown = 60
        elif enemy_type == "armored":
            self.image = pygame.Surface((40, 40))
            self.image.fill((139, 0, 0))
            self.health = 50
            self.speed = ENEMY_SPEED * 0.7
            self.shoot_cooldown = 80
        elif enemy_type == "boss":
            self.image = pygame.Surface((60, 60))
            self.image.fill(YELLOW)
            self.health = 150
            self.speed = ENEMY_SPEED
            self.shoot_cooldown = 30
        
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        
        self.vel_y = 0
        self.direction = 1
        self.move_timer = 0
        self.max_shoot_cooldown = self.shoot_cooldown
    
    def update(self, platforms, player):
        # Apply gravity
        self.vel_y += GRAVITY
        self.vel_y = min(self.vel_y, 20)
        
        # Movement
        self.rect.x += self.direction * self.speed
        self.rect.y += self.vel_y
        
        # Collision with platforms
        self.on_ground = False
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vel_y > 0:
                    self.rect.bottom = platform.rect.top
                    self.vel_y = 0
                    self.on_ground = True
        
        # Change direction at edges
        if self.rect.left < 0 or self.rect.right > SCREEN_WIDTH:
            self.direction *= -1
        
        # Jump occasionally
        self.move_timer += 1
        if self.move_timer > 120 and self.on_ground:
            self.vel_y = -JUMP_STRENGTH * 0.8
            self.move_timer = 0
        
        # Update shoot cooldown
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
    
    def shoot(self):
        if self.shoot_cooldown <= 0:
            self.shoot_cooldown = self.max_shoot_cooldown
            return Projectile(self.rect.centerx, self.rect.centery, self.direction, is_enemy=True)
        return None
    
    def take_damage(self, damage):
        self.health -= damage
        if self.health <= 0:
            return True  # Dead
        return False


class Projectile(pygame.sprite.Sprite):
    def __init__(self, x, y, direction, is_enemy=False):
        super().__init__()
        self.image = pygame.Surface((8, 8))
        if is_enemy:
            self.image.fill(RED)
        else:
            self.image.fill(YELLOW)
        
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.centery = y
        
        self.vel_x = direction * 10
        self.vel_y = 0
        self.is_enemy = is_enemy
        self.damage = 10 if is_enemy else 25
        self.lifetime = 300
    
    def update(self):
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y
        self.lifetime -= 1
        
        # Remove if out of bounds or lifetime expired
        if (self.rect.right < 0 or self.rect.left > SCREEN_WIDTH or 
            self.rect.top > SCREEN_HEIGHT or self.lifetime <= 0):
            self.kill()


class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(GREEN)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Megaman Game")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.large_font = pygame.font.Font(None, 72)
        
        # Load sprite sheet AFTER creating display
        try:
            self.spritesheet = pygame.image.load("megaman_sprites.png").convert_alpha()
            print("✓ Sprite sheet loaded successfully")
        except Exception as e:
            print(f"✗ Could not load sprite sheet: {e}")
            self.spritesheet = None
        
        # Character selection
        self.selected_character = 0
        self.num_characters = self.get_num_characters()
        self.in_character_select = True
        
        self.current_level = 1
        self.score = 0
        self.game_over = False
        self.game_won = False
    
    def get_num_characters(self):
        """Calculate number of characters in the sprite sheet"""
        if self.spritesheet is None:
            return 1
        sheet_width = self.spritesheet.get_width()
        sheet_height = self.spritesheet.get_height()
        sprite_width = sheet_width // 5
        num_chars = sheet_height // (sprite_width * 2)  # Each char has 2 rows
        print(f"Available characters: {num_chars}")
        return max(1, num_chars)
    
    def create_level(self, level):
        """Create platforms based on level"""
        platforms = pygame.sprite.Group()
        
        # Ground
        platforms.add(Platform(0, SCREEN_HEIGHT - 40, SCREEN_WIDTH, 40))
        
        if level == 1:
            # Level 1 platforms
            platforms.add(Platform(100, 450, 150, 20))
            platforms.add(Platform(350, 380, 150, 20))
            platforms.add(Platform(600, 320, 150, 20))
            platforms.add(Platform(150, 250, 150, 20))
            platforms.add(Platform(500, 200, 150, 20))
        elif level == 2:
            # Level 2 platforms
            platforms.add(Platform(50, 450, 100, 20))
            platforms.add(Platform(200, 400, 100, 20))
            platforms.add(Platform(350, 350, 100, 20))
            platforms.add(Platform(500, 300, 100, 20))
            platforms.add(Platform(650, 250, 100, 20))
            platforms.add(Platform(300, 150, 400, 20))
        elif level == 3:
            # Level 3 platforms - Boss level
            platforms.add(Platform(100, 500, 100, 20))
            platforms.add(Platform(300, 450, 200, 20))
            platforms.add(Platform(600, 400, 100, 20))
            platforms.add(Platform(200, 300, 100, 20))
            platforms.add(Platform(500, 250, 100, 20))
            platforms.add(Platform(350, 150, 100, 20))
        
        return platforms
    
    def create_enemies(self, level):
        """Create enemies based on level"""
        enemies = pygame.sprite.Group()
        
        if level == 1:
            enemies.add(Enemy(300, 350, "basic"))
            enemies.add(Enemy(500, 280, "basic"))
            enemies.add(Enemy(200, 200, "basic"))
        elif level == 2:
            enemies.add(Enemy(200, 350, "basic"))
            enemies.add(Enemy(400, 300, "armored"))
            enemies.add(Enemy(600, 250, "basic"))
            enemies.add(Enemy(150, 120, "basic"))
        elif level == 3:
            enemies.add(Enemy(SCREEN_WIDTH // 2, 200, "boss"))
        
        return enemies
    
    def reset_level(self):
        self.platforms = self.create_level(self.current_level)
        self.enemies = self.create_enemies(self.current_level)
        self.player = Player(50, SCREEN_HEIGHT - 200, self.spritesheet, self.selected_character)
        self.projectiles = pygame.sprite.Group()
        self.enemy_projectiles = pygame.sprite.Group()
        self.wave_timer = 0
    
    def next_level(self):
        self.current_level += 1
        if self.current_level > 3:
            self.game_won = True
            return
        self.reset_level()
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif self.in_character_select:
                    if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                        self.selected_character = (self.selected_character - 1) % self.num_characters
                    elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                        self.selected_character = (self.selected_character + 1) % self.num_characters
                    elif event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                        self.in_character_select = False
                        self.reset_level()
        return True
    
    def update(self):
        if self.in_character_select:
            return
        
        if self.game_over or self.game_won:
            return
        
        keys = pygame.key.get_pressed()
        self.player.handle_input(keys)
        
        # Shooting
        if keys[pygame.K_z] or keys[pygame.K_SPACE]:
            projectile = self.player.shoot()
            if projectile:
                self.projectiles.add(projectile)
        
        # Update player
        if not self.player.update(self.platforms, self.enemies):
            self.game_over = True
        
        # Update enemies
        for enemy in self.enemies:
            enemy.update(self.platforms, self.player)
            
            # Enemy shooting
            if random.random() < 0.02:  # 2% chance per frame to shoot
                projectile = enemy.shoot()
                if projectile:
                    self.enemy_projectiles.add(projectile)
        
        # Update projectiles
        self.projectiles.update()
        self.enemy_projectiles.update()
        
        # Check projectile collisions with enemies
        for projectile in self.projectiles:
            for enemy in self.enemies:
                if projectile.rect.colliderect(enemy.rect):
                    if enemy.take_damage(projectile.damage):
                        self.score += 100 * (2 if enemy.enemy_type == "boss" else 1)
                        enemy.kill()
                    projectile.kill()
        
        # Check enemy projectile collisions with player
        for projectile in self.enemy_projectiles:
            if projectile.rect.colliderect(self.player.rect):
                if not self.player.take_damage(projectile.damage):
                    self.game_over = True
                projectile.kill()
        
        # Check if all enemies defeated
        if len(self.enemies) == 0:
            self.next_level()
    
    def draw_character_select(self):
        """Draw the character selection screen"""
        self.screen.fill(DARKBLUE)
        
        # Title
        title_text = self.large_font.render("SELECT CHARACTER", True, WHITE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 50))
        self.screen.blit(title_text, title_rect)
        
        # Character preview
        if self.spritesheet is not None:
            try:
                sheet_width = self.spritesheet.get_width()
                sprite_width = sheet_width // 5
                # Get first frame of selected character
                frame = self.spritesheet.subsurface(
                    (0, self.selected_character * sprite_width * 2, sprite_width, sprite_width)
                )
                # Scale up for display
                scaled_frame = pygame.transform.scale(frame, (150, 150))
                preview_rect = scaled_frame.get_rect(center=(SCREEN_WIDTH // 2, 250))
                self.screen.blit(scaled_frame, preview_rect)
            except:
                pass
        
        # Character info
        char_text = self.font.render(f"Character {self.selected_character + 1} of {self.num_characters}", True, YELLOW)
        char_rect = char_text.get_rect(center=(SCREEN_WIDTH // 2, 420))
        self.screen.blit(char_text, char_rect)
        
        # Instructions
        left_text = self.font.render("← LEFT / A", True, WHITE)
        right_text = self.font.render("RIGHT / D →", True, WHITE)
        self.screen.blit(left_text, (50, SCREEN_HEIGHT - 150))
        self.screen.blit(right_text, (SCREEN_WIDTH - 300, SCREEN_HEIGHT - 150))
        
        select_text = self.font.render("SPACE / ENTER to Start", True, GREEN)
        select_rect = select_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 80))
        self.screen.blit(select_text, select_rect)
        
        pygame.display.flip()
    
    def draw(self):
        if self.in_character_select:
            self.draw_character_select()
            return
        
        # Draw platforms
        for platform in self.platforms:
            self.screen.blit(platform.image, platform.rect)
        
        # Draw player
        self.screen.blit(self.player.image, self.player.rect)
        
        # Draw enemies
        for enemy in self.enemies:
            self.screen.blit(enemy.image, enemy.rect)
        
        # Draw projectiles
        for projectile in self.projectiles:
            self.screen.blit(projectile.image, projectile.rect)
        
        for projectile in self.enemy_projectiles:
            self.screen.blit(projectile.image, projectile.rect)
        
        # Draw health
        self.player.draw_health(self.screen)
        
        # Draw level and score
        level_text = self.font.render(f"Level: {self.current_level}", True, WHITE)
        score_text = self.font.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(level_text, (SCREEN_WIDTH - 250, 10))
        self.screen.blit(score_text, (SCREEN_WIDTH - 250, 50))
        
        # Draw game over or won message
        if self.game_over:
            game_over_text = self.font.render("GAME OVER! Press ESC to quit", True, RED)
            text_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(game_over_text, text_rect)
        
        if self.game_won:
            won_text = self.font.render(f"YOU WIN! Final Score: {self.score}", True, GREEN)
            text_rect = won_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(won_text, text_rect)
        
        pygame.display.flip()
    
    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)
        
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()
