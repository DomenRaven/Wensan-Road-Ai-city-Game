import Phaser from 'phaser';
import { EventBus } from '../EventBus';
import { useGameStore } from '../../store/gameStore';

const MAX_SPEED = 800;
const ACCEL = 300;
const FRICTION = 200;
const TURN_SPEED = 300;
const LAP_DISTANCE = 10000;
const GAME_DURATION = 90;

export class MainGame extends Phaser.Scene {
  private player!: Phaser.Physics.Arcade.Sprite;
  private trackTile!: Phaser.GameObjects.TileSprite;
  private npcGroup!: Phaser.Physics.Arcade.Group;
  private obstacleGroup!: Phaser.Physics.Arcade.Group;
  private cursors!: Phaser.Types.Input.Keyboard.CursorKeys;
  private spaceKey!: Phaser.Input.Keyboard.Key;
  
  private currentSpeed = 0;
  private distance = 0;
  private isPlaying = false;
  private timerEvent: Phaser.Time.TimerEvent | null = null;
  private spawnEvent: Phaser.Time.TimerEvent | null = null;
  private lastHitTime = 0;
  private hitSound!: Phaser.Sound.BaseSound;

  constructor() {
    super('MainGame');
  }

  create() {
    const width = this.scale.width;
    const height = this.scale.height;

    // Track
    this.trackTile = this.add.tileSprite(0, 0, width, height, 'track_atlas').setOrigin(0, 0);

    // Player
    this.player = this.physics.add.sprite(width / 2, height - 150, 'player_car');
    this.player.setScale(0.14);
    this.player.setCollideWorldBounds(true);
    // Adjust hitbox
    (this.player.body as Phaser.Physics.Arcade.Body).setSize(300, 600);

    // NPCs and Obstacles
    this.npcGroup = this.physics.add.group();
    this.obstacleGroup = this.physics.add.group();

    // Input
    this.cursors = this.input.keyboard!.createCursorKeys();
    this.spaceKey = this.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.SPACE);

    // Audio
    this.hitSound = this.sound.add('hitSound');

    // Collision
    this.physics.add.overlap(this.player, this.npcGroup, this.onHitNpc, undefined, this);
    this.physics.add.overlap(this.player, this.obstacleGroup, this.onHitObstacle, undefined, this);

    // Events
    EventBus.on('start-game', this.startGame, this);
    
    // Default state: wait for start
    this.isPlaying = false;
  }

  private startGame() {
    this.isPlaying = true;
    this.currentSpeed = 0;
    this.distance = 0;
    this.lastHitTime = 0;
    this.player.setPosition(this.scale.width / 2, this.scale.height - 150);
    this.npcGroup.clear(true, true);
    this.obstacleGroup.clear(true, true);
    
    useGameStore.getState().resetGame();
    useGameStore.getState().setTimeLeft(GAME_DURATION);

    if (this.timerEvent) {
      this.timerEvent.destroy();
    }

    this.timerEvent = this.time.addEvent({
      delay: 1000,
      callback: this.tickTimer,
      callbackScope: this,
      loop: true
    });

    if (this.spawnEvent) {
      this.spawnEvent.destroy();
    }

    this.scheduleNextSpawn();
  }

  private tickTimer() {
    if (!this.isPlaying) return;
    const store = useGameStore.getState();
    const newTime = store.timeLeft - 1;
    store.setTimeLeft(newTime);

    if (newTime <= 0) {
      this.gameOver();
    }
  }

  private scheduleNextSpawn() {
    if (!this.isPlaying) return;

    const score = useGameStore.getState().score;
    
    // Spawn logic
    const isObstacle = score >= 1 && Phaser.Math.FloatBetween(0, 1) > 0.6;
    const x = Phaser.Math.Between(50, this.scale.width - 50);

    if (isObstacle) {
      const obs = this.obstacleGroup.create(x, -100, 'cone') as Phaser.Physics.Arcade.Sprite;
      (obs.body as Phaser.Physics.Arcade.Body).setSize(30, 30);
    } else {
      const texture = Phaser.Math.FloatBetween(0, 1) > 0.5 ? 'npc_car_yellow' : 'npc_car_blue';
      const npc = this.npcGroup.create(x, -100, texture) as Phaser.Physics.Arcade.Sprite;
      npc.setScale(0.14);
      npc.setData('baseSpeed', Phaser.Math.Between(200, 400 + score * 20));
      if (score >= 2) {
         npc.setData('lateralSpeed', Phaser.Math.Between(-100, 100));
      } else {
         npc.setData('lateralSpeed', 0);
      }
      (npc.body as Phaser.Physics.Arcade.Body).setSize(300, 600);
    }

    // Spawn frequency increases with score
    const delay = Math.max(500, 2000 - score * 200);
    this.spawnEvent = this.time.addEvent({
      delay: delay,
      callback: this.scheduleNextSpawn,
      callbackScope: this
    });
  }

  private triggerHitFeedback(severity: number) {
    const now = this.time.now;
    if (now - this.lastHitTime > 500) {
      this.currentSpeed *= severity;
      this.lastHitTime = now;
      if (this.hitSound) {
        this.hitSound.play({ volume: 0.5 });
      }
      
      this.tweens.add({
        targets: this.player,
        scaleX: 0.12,
        scaleY: 0.12,
        duration: 100,
        yoyo: true
      });
      
      this.tweens.add({
        targets: this.player,
        x: this.player.x + Phaser.Math.Between(-15, 15),
        duration: 50,
        yoyo: true,
        repeat: 3
      });
    }
  }

  private onHitNpc(p: any, n: any) {
    this.triggerHitFeedback(0.4); // Lose 60%
  }

  private onHitObstacle(p: any, o: any) {
    this.triggerHitFeedback(0.1); // Severe penalty, lose 90%
    o.destroy();
  }

  private gameOver() {
    this.isPlaying = false;
    if (this.timerEvent) {
      this.timerEvent.destroy();
    }
    if (this.spawnEvent) {
      this.spawnEvent.destroy();
    }
    useGameStore.getState().setGameState('GAMEOVER');
  }

  update(time: number, delta: number) {
    if (!this.isPlaying) {
      (this.player.body as Phaser.Physics.Arcade.Body).setVelocity(0, 0);
      return;
    }

    const dt = delta / 1000;

    // Acceleration & Braking
    if (this.spaceKey.isDown) {
      this.currentSpeed += ACCEL * dt;
    } else {
      this.currentSpeed -= FRICTION * dt;
    }

    this.currentSpeed = Phaser.Math.Clamp(this.currentSpeed, 0, MAX_SPEED);

    // Steering
    let vx = 0;
    if (this.currentSpeed > 0) {
      if (this.cursors.left.isDown) {
        vx = -TURN_SPEED;
        this.player.angle = -5;
      } else if (this.cursors.right.isDown) {
        vx = TURN_SPEED;
        this.player.angle = 5;
      } else {
        this.player.angle = 0;
      }
    } else {
      this.player.angle = 0;
    }

    (this.player.body as Phaser.Physics.Arcade.Body).setVelocityX(vx);

    // Track scroll
    this.trackTile.tilePositionY -= this.currentSpeed * dt;

    // Distance & Laps
    this.distance += this.currentSpeed * dt;
    if (this.distance >= LAP_DISTANCE) {
      this.distance -= LAP_DISTANCE;
      useGameStore.getState().addScore(1);
    }

    // NPC movement relative to player speed
    const children = this.npcGroup.getChildren();
    for (let i = children.length - 1; i >= 0; i--) {
      const npc = children[i] as Phaser.Physics.Arcade.Sprite;
      if (!npc || !npc.active) continue;

      const baseSpeed = npc.getData('baseSpeed');
      // If player speed is 800, and npc baseSpeed is 300
      // the npc should move downwards on screen at 500 (800 - 300)
      const relativeVelocityY = this.currentSpeed - baseSpeed;
      if (npc.body) {
        (npc.body as Phaser.Physics.Arcade.Body).setVelocityY(relativeVelocityY);
        const latSpeed = npc.getData('lateralSpeed') || 0;
        (npc.body as Phaser.Physics.Arcade.Body).setVelocityX(latSpeed);
        
        if (npc.x < 50 && latSpeed < 0) npc.setData('lateralSpeed', -latSpeed);
        if (npc.x > this.scale.width - 50 && latSpeed > 0) npc.setData('lateralSpeed', -latSpeed);
      }

      // Remove off-screen NPCs
      if (npc.y > this.scale.height + 200) {
        npc.destroy();
      }
    }

    // Obstacle movement relative to player speed
    const obsChildren = this.obstacleGroup.getChildren();
    for (let i = obsChildren.length - 1; i >= 0; i--) {
      const obs = obsChildren[i] as Phaser.Physics.Arcade.Sprite;
      if (!obs || !obs.active) continue;

      if (obs.body) {
        (obs.body as Phaser.Physics.Arcade.Body).setVelocityY(this.currentSpeed);
      }

      if (obs.y > this.scale.height + 200) {
        obs.destroy();
      }
    }
  }

  shutdown() {
    EventBus.off('start-game', this.startGame, this);
  }
}
