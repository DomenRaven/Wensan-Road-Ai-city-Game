import Phaser from 'phaser';
import { EventBus, EVENTS } from '../EventBus';
import { CONSTANTS } from '../constants';

export class GameScene extends Phaser.Scene {
  player!: Phaser.Physics.Arcade.Sprite;
  ground!: Phaser.GameObjects.TileSprite;
  obstacles!: Phaser.Physics.Arcade.Group;
  
  isPlaying = false;
  score = 0;
  timeLeft = CONSTANTS.GAME_DURATION;
  speed = CONSTANTS.SPEED_START;
  
  nextObstacleTime = 0;
  gameTimer!: Phaser.Time.TimerEvent;

  cursors!: Phaser.Types.Input.Keyboard.CursorKeys;
  spaceKey!: Phaser.Input.Keyboard.Key;
  downKey!: Phaser.Input.Keyboard.Key;

  constructor() {
    super('Game');
  }

  create() {
    this.isPlaying = false;
    this.score = 0;
    this.timeLeft = CONSTANTS.GAME_DURATION;
    this.speed = CONSTANTS.SPEED_START;

    // Background (Sky is set in config, add some clouds)
    this.createClouds();

    // Ground
    const groundHeight = CONSTANTS.HEIGHT - CONSTANTS.GROUND_Y;
    this.ground = this.add.tileSprite(0, CONSTANTS.GROUND_Y, CONSTANTS.WIDTH, groundHeight, 'char_idle').setOrigin(0, 0);
    // Wait, we don't have a ground texture. We should generate one or use a graphics.
    this.ground.destroy();
    
    // Generate a ground texture
    const g = this.make.graphics({ x: 0, y: 0 }, false);
    g.fillStyle(0x4CAF50, 1);
    g.fillRect(0, 0, 64, groundHeight);
    g.lineStyle(4, 0x388E3C, 1);
    g.moveTo(0, 0);
    g.lineTo(64, 0);
    g.strokePath();
    g.generateTexture('ground_tex', 64, groundHeight);
    g.destroy();

    this.ground = this.add.tileSprite(0, CONSTANTS.GROUND_Y, CONSTANTS.WIDTH, groundHeight, 'ground_tex').setOrigin(0, 0);
    this.physics.add.existing(this.ground, true); // static body
    (this.ground.body as Phaser.Physics.Arcade.Body).setSize(CONSTANTS.WIDTH, groundHeight);

    // Generate Obstacle Textures
    this.createObstacleTextures();

    // Player
    this.player = this.physics.add.sprite(CONSTANTS.PLAYER_X, CONSTANTS.GROUND_Y - 32, 'char_idle');
    this.player.setOrigin(0.5, 1);
    this.player.setScale(2);
    // Adjust body size
    (this.player.body as Phaser.Physics.Arcade.Body).setSize(16, 24);
    (this.player.body as Phaser.Physics.Arcade.Body).setOffset(8, 8);
    this.player.play('anim_idle');

    // Obstacles
    this.obstacles = this.physics.add.group();

    // Collisions
    this.physics.add.collider(this.player, this.ground);
    this.physics.add.overlap(this.player, this.obstacles, this.hitObstacle, undefined, this);

    // Input
    this.spaceKey = this.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.SPACE);
    this.downKey = this.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.DOWN);

    // Event Listeners
    const onStart = () => {
      this.startGame();
    };
    EventBus.once('ui-start-game', onStart);

    this.events.on('shutdown', () => {
      EventBus.off('ui-start-game', onStart);
    });
  }

  createClouds() {
    const cg = this.make.graphics({ x: 0, y: 0 }, false);
    cg.fillStyle(0xFFFFFF, 0.8);
    cg.fillCircle(30, 30, 30);
    cg.fillCircle(60, 20, 20);
    cg.fillCircle(80, 30, 30);
    cg.fillRect(30, 30, 50, 30);
    cg.generateTexture('cloud_tex', 110, 60);
    cg.destroy();

    for(let i=0; i<5; i++) {
      const x = Phaser.Math.Between(0, CONSTANTS.WIDTH);
      const y = Phaser.Math.Between(50, 200);
      const cloud = this.add.image(x, y, 'cloud_tex').setAlpha(0.6);
      this.tweens.add({
        targets: cloud,
        x: -150,
        duration: Phaser.Math.Between(20000, 40000),
        repeat: -1,
        onRepeat: (tween, target) => {
          target.x = CONSTANTS.WIDTH + 150;
          target.y = Phaser.Math.Between(50, 200);
        }
      });
    }
  }

  createObstacleTextures() {
    // Low obstacle (slide)
    const low = this.make.graphics({ x: 0, y: 0 }, false);
    low.fillStyle(0xFF9800, 1);
    low.fillRect(0, 0, 32, 64);
    low.lineStyle(4, 0x333333, 1);
    low.strokeRect(0, 0, 32, 64);
    low.generateTexture('obs_low', 32, 64);
    low.destroy();

    // High obstacle (jump)
    const high = this.make.graphics({ x: 0, y: 0 }, false);
    high.fillStyle(0xFF9800, 1);
    high.fillRect(0, 0, 32, 96);
    high.lineStyle(4, 0x333333, 1);
    high.strokeRect(0, 0, 32, 96);
    high.generateTexture('obs_high', 32, 96);
    high.destroy();
  }

  startGame() {
    this.isPlaying = true;
    EventBus.emit(EVENTS.GAME_START);
    this.player.play('anim_run');
    this.nextObstacleTime = this.time.now + Phaser.Math.Between(1000, 2000);

    this.gameTimer = this.time.addEvent({
      delay: 1000,
      callback: this.tickTimer,
      callbackScope: this,
      loop: true
    });
  }

  tickTimer() {
    if (!this.isPlaying) return;
    this.timeLeft -= 1;
    EventBus.emit(EVENTS.TIME_UPDATE, this.timeLeft);
    
    // Increase speed over time slightly
    this.speed -= 5;

    if (this.timeLeft <= 0) {
      this.endGame();
    }
  }

  spawnObstacle() {
    const isHigh = Phaser.Math.Between(0, 1) === 1;
    const tex = isHigh ? 'obs_high' : 'obs_low';
    
    // Obstacle placement
    // High obstacle: sits on ground. Wait, low obstacle needs sliding.
    // Actually, "low" obstacle means it is floating high so you must slide UNDER it.
    // "High" obstacle means it sits on ground and you must jump OVER it.
    let y = CONSTANTS.GROUND_Y;
    let originY = 1;
    if (!isHigh) {
      // It's a hanging obstacle (needs sliding)
      y = CONSTANTS.GROUND_Y - 40;
    }

    const obs = this.physics.add.sprite(CONSTANTS.WIDTH + 50, y, tex);
    obs.setOrigin(0.5, originY);
    this.obstacles.add(obs);
    
    (obs.body as Phaser.Physics.Arcade.Body).setAllowGravity(false);
    (obs.body as Phaser.Physics.Arcade.Body).setVelocityX(this.speed);
    (obs.body as Phaser.Physics.Arcade.Body).setImmovable(true);

    this.nextObstacleTime = this.time.now + Phaser.Math.Between(CONSTANTS.OBSTACLE_MIN_GAP, CONSTANTS.OBSTACLE_MAX_GAP) * (300 / Math.abs(this.speed));
  }

  hitObstacle() {
    if (!this.isPlaying) return;
    this.endGame();
  }

  endGame() {
    this.isPlaying = false;
    this.gameTimer?.remove();
    this.physics.pause();
    this.player.play('anim_hit');
    
    this.player.once('animationcomplete-anim_hit', () => {
      EventBus.emit(EVENTS.GAME_OVER, this.score);
      this.scene.start('GameOver');
    });
  }

  update(time: number, delta: number) {
    if (!this.isPlaying) return;

    // Score update
    this.score += (Math.abs(this.speed) * delta) / 10000;
    EventBus.emit(EVENTS.SCORE_UPDATE, this.score);

    // Ground scrolling
    this.ground.tilePositionX += (Math.abs(this.speed) * delta) / 1000;

    // Obstacle generation
    if (time > this.nextObstacleTime) {
      this.spawnObstacle();
    }

    // Obstacle cleanup
    this.obstacles.getChildren().forEach((child) => {
      const obs = child as Phaser.Physics.Arcade.Sprite;
      if (obs.x < -100) {
        obs.destroy();
      } else {
        // sync speed
        (obs.body as Phaser.Physics.Arcade.Body).setVelocityX(this.speed);
      }
    });

    this.handleInput();
  }

  handleInput() {
    const body = this.player.body as Phaser.Physics.Arcade.Body;
    const onGround = body.touching.down || body.blocked.down;

    if (onGround) {
      if (this.spaceKey.isDown) {
        body.setVelocityY(CONSTANTS.JUMP_VELOCITY);
        this.player.play('anim_jump', true);
        this.player.setScale(2, 2);
        body.setSize(16, 24);
        body.setOffset(8, 8);
      } else if (this.downKey.isDown) {
        // Slide
        this.player.play('anim_fall', true);
        this.player.setScale(2, 1);
        // adjust body for sliding
        body.setSize(16, 12);
        body.setOffset(8, 20);
      } else {
        // Run normally
        this.player.play('anim_run', true);
        this.player.setScale(2, 2);
        body.setSize(16, 24);
        body.setOffset(8, 8);
      }
    } else {
      // In air
      if (body.velocity.y > 0) {
        this.player.play('anim_fall', true);
      }
    }
  }
}
