import { Scene } from 'phaser';
import { EventBus } from '../EventBus';
import { CONSTANTS, ENEMY_TYPES, POWERUP_TYPES } from '../constants';
import { useGameStore } from '../store';

export class MainGame extends Scene {
  private bg!: Phaser.GameObjects.TileSprite;
  private player!: Phaser.Physics.Arcade.Sprite;
  private playerShieldObj!: Phaser.GameObjects.Sprite;
  private playerBullets!: Phaser.Physics.Arcade.Group;
  private enemies!: Phaser.Physics.Arcade.Group;
  private enemyBullets!: Phaser.Physics.Arcade.Group;
  private powerups!: Phaser.Physics.Arcade.Group;
  
  private targetX: number = 0;
  private isGameOver: boolean = false;
  private lastFired: number = 0;
  private enemySpawnTimer!: Phaser.Time.TimerEvent;
  private spawnDelay: number = CONSTANTS.ENEMY_SPAWN_RATE;

  // Boss states
  private isBossActive: boolean = false;
  private bossObj: Phaser.Physics.Arcade.Sprite | null = null;
  private nextBossScore: number = 500;
  private bossShootTimer?: Phaser.Time.TimerEvent;
  private bossTween?: Phaser.Tweens.Tween;

  // Powerup states
  private hasShield: boolean = false;
  private isDoubleShot: boolean = false;
  private hasFireRateUp: boolean = false;
  private doubleShotTimer?: Phaser.Time.TimerEvent;
  private fireRateTimer?: Phaser.Time.TimerEvent;

  // 简单的音频上下文，用于生成合成音效，以弥补没有实体音频文件的不足
  private audioCtx: AudioContext | null = null;

  constructor() {
    super('MainGame');
  }

  private playSound(type: 'shoot' | 'explosion') {
    if (!this.audioCtx) {
      try { this.audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)(); } catch (e) {}
    }
    if (!this.audioCtx) return;

    const osc = this.audioCtx.createOscillator();
    const gainNode = this.audioCtx.createGain();
    osc.connect(gainNode);
    gainNode.connect(this.audioCtx.destination);

    if (type === 'shoot') {
      osc.type = 'square';
      osc.frequency.setValueAtTime(880, this.audioCtx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(110, this.audioCtx.currentTime + 0.1);
      gainNode.gain.setValueAtTime(0.1, this.audioCtx.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioCtx.currentTime + 0.1);
      osc.start();
      osc.stop(this.audioCtx.currentTime + 0.1);
    } else {
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(100, this.audioCtx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(0.01, this.audioCtx.currentTime + 0.3);
      gainNode.gain.setValueAtTime(0.3, this.audioCtx.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioCtx.currentTime + 0.3);
      osc.start();
      osc.stop(this.audioCtx.currentTime + 0.3);
    }
  }

  create() {
    this.isGameOver = false;
    useGameStore.getState().resetGame();
    EventBus.emit('scene-changed', { key: 'MainGame' });

    // 1. 背景滚动
    this.bg = this.add.tileSprite(0, 0, CONSTANTS.GAME_WIDTH, CONSTANTS.GAME_HEIGHT, 'background').setOrigin(0, 0);

    // 2. 物理组
    this.playerBullets = this.physics.add.group();
    this.enemyBullets = this.physics.add.group();
    this.enemies = this.physics.add.group();
    this.powerups = this.physics.add.group();

    // 3. 玩家飞机
    this.player = this.physics.add.sprite(CONSTANTS.GAME_WIDTH / 2, CONSTANTS.GAME_HEIGHT - 100, 'ships', 4);
    this.player.setCollideWorldBounds(true);
    // 玩家飞机的 targetX 初始化为其当前 X
    this.targetX = this.player.x;

    // 玩家护盾特效 (初始隐藏)
    this.playerShieldObj = this.add.sprite(this.player.x, this.player.y, 'tiles', 13).setScale(2).setVisible(false);

    // 4. 输入控制
    this.input.on('pointermove', (pointer: Phaser.Input.Pointer) => {
      if (pointer.isDown && !this.isGameOver) {
        this.targetX = Phaser.Math.Clamp(pointer.x, 32, CONSTANTS.GAME_WIDTH - 32);
      }
    });
    this.input.on('pointerdown', (pointer: Phaser.Input.Pointer) => {
      if (!this.isGameOver) {
        this.targetX = Phaser.Math.Clamp(pointer.x, 32, CONSTANTS.GAME_WIDTH - 32);
        if (this.audioCtx?.state === 'suspended') this.audioCtx.resume();
      }
    });

    // 5. 敌机生成定时器
    this.enemySpawnTimer = this.time.addEvent({
      delay: this.spawnDelay,
      callback: this.spawnEnemy,
      callbackScope: this,
      loop: true
    });

    // 6. 碰撞检测
    this.physics.add.overlap(this.playerBullets, this.enemies, this.hitEnemy, undefined, this);
    this.physics.add.overlap(this.player, this.enemies, this.crashEnemy, undefined, this);
    this.physics.add.overlap(this.player, this.enemyBullets, this.hitPlayer, undefined, this);
    this.physics.add.overlap(this.player, this.powerups, this.collectPowerup, undefined, this);
  }

  private spawnEnemy() {
    if (this.isGameOver || this.isBossActive) return;

    // 随着时间减少生成间隔，增加难度
    if (this.spawnDelay > 500) {
      this.spawnDelay -= 10;
      this.enemySpawnTimer.destroy();
      this.enemySpawnTimer = this.time.addEvent({
        delay: this.spawnDelay,
        callback: this.spawnEnemy,
        callbackScope: this,
        loop: true
      });
    }

    const x = Phaser.Math.Between(32, CONSTANTS.GAME_WIDTH - 32);
    const rand = Math.random();
    let typeData = ENEMY_TYPES.NORMAL;
    
    if (rand > 0.9) typeData = ENEMY_TYPES.HEAVY;
    else if (rand > 0.6) typeData = ENEMY_TYPES.FAST;

    const enemy = this.physics.add.sprite(x, -32, typeData.key, typeData.frame);
    this.enemies.add(enemy);
    enemy.setAngle(180);
    
    const body = enemy.body as Phaser.Physics.Arcade.Body;
    body.setSize(enemy.width * 0.8, enemy.height * 0.8);
    enemy.setVelocityY(typeData.speed);
    enemy.setData('hp', typeData.hp);
    enemy.setData('score', typeData.score);
    enemy.setData('type', typeData);

    // 敌机射击定时器
    if (typeData.fireRate > 0) {
      const shootTimer = this.time.addEvent({
        delay: typeData.fireRate,
        callback: () => {
          if (!enemy.active || this.isGameOver) {
            shootTimer.remove();
            return;
          }
          this.enemyShoot(enemy);
        },
        loop: true
      });
    }
  }

  private enemyShoot(enemy: Phaser.Physics.Arcade.Sprite) {
    const bullet = this.physics.add.sprite(enemy.x, enemy.y + 20, 'tiles', 2);
    this.enemyBullets.add(bullet);
    const body = bullet.body as Phaser.Physics.Arcade.Body;
    body.setSize(8, 16);
    bullet.setVelocityY(CONSTANTS.ENEMY_BULLET_SPEED);
  }

  private hitEnemy(bulletGroupObj: any, enemyGroupObj: any) {
    if (this.isGameOver) return;
    
    const bullet = bulletGroupObj as Phaser.Physics.Arcade.Sprite;
    const enemy = enemyGroupObj as Phaser.Physics.Arcade.Sprite;

    bullet.destroy();
    let hp = enemy.getData('hp') - 1;
    enemy.setData('hp', hp);

    // 闪烁受击效果
    enemy.setTint(0xffffff);
    this.time.delayedCall(50, () => {
      if (enemy.active) enemy.clearTint();
    });

    if (hp <= 0) {
      this.playSound('explosion');
      const score = enemy.getData('score');
      useGameStore.getState().addScore(score);
      
      const boom = this.add.sprite(enemy.x, enemy.y, 'tiles', 4);
      const isBoss = enemy.getData('isBoss');
      if (isBoss) {
        boom.setScale(3);
      }
      boom.play('explode');
      boom.on('animationcomplete', () => boom.destroy());
      
      // 道具掉落
      const dropRate = enemy.getData('type').dropRate;
      if (isBoss) {
        // Boss必掉落3个道具
        for (let i = 0; i < 3; i++) {
          this.spawnPowerup(enemy.x - 30 + i * 30, enemy.y);
        }
        this.clearBoss();
      } else {
        if (Math.random() <= dropRate) {
          this.spawnPowerup(enemy.x, enemy.y);
        }
      }

      enemy.destroy();
    }
  }

  private spawnPowerup(x: number, y: number) {
    const type = Phaser.Utils.Array.GetRandom(POWERUP_TYPES);
    const powerup = this.physics.add.sprite(x, y, 'tiles', type.frame).setScale(1.5);
    this.powerups.add(powerup);
    powerup.setData('name', type.name);
    powerup.setVelocityY(CONSTANTS.POWERUP_SPEED);
  }

  private collectPowerup(playerObj: any, powerupObj: any) {
    if (this.isGameOver) return;
    const powerup = powerupObj as Phaser.Physics.Arcade.Sprite;
    const typeName = powerup.getData('name');
    powerup.destroy();
    
    this.playSound('shoot'); // 作为拾取音效

    if (typeName === 'fireRate') {
      this.hasFireRateUp = true;
      if (this.fireRateTimer) this.fireRateTimer.remove();
      this.fireRateTimer = this.time.delayedCall(CONSTANTS.POWERUP_DURATION, () => {
        this.hasFireRateUp = false;
      });
    } else if (typeName === 'doubleShot') {
      this.isDoubleShot = true;
      if (this.doubleShotTimer) this.doubleShotTimer.remove();
      this.doubleShotTimer = this.time.delayedCall(CONSTANTS.POWERUP_DURATION, () => {
        this.isDoubleShot = false;
      });
    } else if (typeName === 'shield') {
      this.hasShield = true;
      this.playerShieldObj.setVisible(true);
    }
  }

  private crashEnemy(playerObj: any, enemyObj: any) {
    if (this.isGameOver) return;
    const enemy = enemyObj as Phaser.Physics.Arcade.Sprite;
    
    const boom = this.add.sprite(enemy.x, enemy.y, 'tiles', 4);
    boom.play('explode');
    boom.on('animationcomplete', () => boom.destroy());
    
    // 如果撞到的是boss，不销毁boss，而是自己扣血/护盾
    const isBoss = enemy.getData('isBoss');
    if (!isBoss) {
      enemy.destroy();
    }

    if (this.hasShield) {
      this.hasShield = false;
      this.playerShieldObj.setVisible(false);
      this.playSound('explosion');
      return;
    }

    this.gameOver();
  }

  private hitPlayer(playerObj: any, bulletObj: any) {
    if (this.isGameOver) return;
    const bullet = bulletObj as Phaser.Physics.Arcade.Sprite;
    bullet.destroy();

    if (this.hasShield) {
      this.hasShield = false;
      this.playerShieldObj.setVisible(false);
      this.playSound('explosion');
      return;
    }

    this.gameOver();
  }

  private gameOver() {
    this.isGameOver = true;
    this.playSound('explosion');
    
    const boom = this.add.sprite(this.player.x, this.player.y, 'tiles', 4);
    boom.setScale(2);
    boom.play('explode');
    
    // 震屏效果
    this.cameras.main.shake(500, 0.02);

    this.player.setAlpha(0);
    this.player.body!.enable = false;

    this.time.delayedCall(1000, () => {
      this.scene.start('GameOver');
    });
  }

  update(time: number, delta: number) {
    if (this.isGameOver) return;

    // 检查Boss生成
    const score = useGameStore.getState().score;
    if (!this.isBossActive && score >= this.nextBossScore) {
      this.spawnBoss();
      this.nextBossScore += 1000;
    }

    // 1. 背景滚动
    this.bg.tilePositionY -= 2;

    // 2. 玩家移动 (使用 body.reset 实现 kinematic 跟随)
    const body = this.player.body as Phaser.Physics.Arcade.Body;
    // 平滑插值，手感更好
    const newX = Phaser.Math.Linear(this.player.x, this.targetX, 0.3);
    body.reset(newX, this.player.y);

    if (this.hasShield) {
      this.playerShieldObj.setPosition(this.player.x, this.player.y);
    }

    // 3. 玩家自动射击
    if (time > this.lastFired) {
      this.playerShoot();
      const delay = this.hasFireRateUp ? CONSTANTS.PLAYER_FIRE_RATE / 2 : CONSTANTS.PLAYER_FIRE_RATE;
      this.lastFired = time + delay;
    }

    // 4. 清理越界物体
    this.playerBullets.children.each((b: any) => {
      const bullet = b as Phaser.Physics.Arcade.Sprite;
      if (bullet.y < -32) bullet.destroy();
      return true;
    });

    this.enemyBullets.children.each((b: any) => {
      const bullet = b as Phaser.Physics.Arcade.Sprite;
      if (bullet.y > CONSTANTS.GAME_HEIGHT + 32) bullet.destroy();
      return true;
    });

    this.enemies.children.each((e: any) => {
      const enemy = e as Phaser.Physics.Arcade.Sprite;
      if (!enemy.getData('isBoss') && enemy.y > CONSTANTS.GAME_HEIGHT + 32) enemy.destroy();
      return true;
    });

    this.powerups.children.each((p: any) => {
      const powerup = p as Phaser.Physics.Arcade.Sprite;
      if (powerup.y > CONSTANTS.GAME_HEIGHT + 32) powerup.destroy();
      return true;
    });
  }

  private playerShoot() {
    if (this.isDoubleShot) {
      const offsets = [-15, 15];
      offsets.forEach(offset => {
        const bullet = this.physics.add.sprite(this.player.x + offset, this.player.y - 20, 'tiles', 0);
        this.playerBullets.add(bullet);
        const body = bullet.body as Phaser.Physics.Arcade.Body;
        body.setSize(8, 16);
        bullet.setVelocityY(-CONSTANTS.BULLET_SPEED);
      });
    } else {
      const bullet = this.physics.add.sprite(this.player.x, this.player.y - 20, 'tiles', 0);
      this.playerBullets.add(bullet);
      const body = bullet.body as Phaser.Physics.Arcade.Body;
      body.setSize(8, 16);
      bullet.setVelocityY(-CONSTANTS.BULLET_SPEED);
    }
    this.playSound('shoot');
  }

  private spawnBoss() {
    this.isBossActive = true;
    this.playSound('explosion'); // Boss 出现提示音
    
    this.bossObj = this.physics.add.sprite(CONSTANTS.GAME_WIDTH / 2, -100, ENEMY_TYPES.BOSS.key, ENEMY_TYPES.BOSS.frame);
    this.bossObj.setScale(ENEMY_TYPES.BOSS.scale);
    this.bossObj.setAngle(180);
    this.enemies.add(this.bossObj);
    
    const body = this.bossObj.body as Phaser.Physics.Arcade.Body;
    body.setSize(this.bossObj.width * 0.8, this.bossObj.height * 0.8);
    this.bossObj.setData('hp', ENEMY_TYPES.BOSS.hp);
    this.bossObj.setData('score', ENEMY_TYPES.BOSS.score);
    this.bossObj.setData('type', ENEMY_TYPES.BOSS);
    this.bossObj.setData('isBoss', true);

    // Boss 出场动画和移动模式
    this.bossTween = this.tweens.add({
      targets: this.bossObj,
      y: 150,
      duration: 2000,
      ease: 'Sine.easeOut',
      onComplete: () => {
        if (!this.bossObj || !this.bossObj.active || this.isGameOver) return;
        this.bossTween = this.tweens.add({
          targets: this.bossObj,
          x: { from: 100, to: CONSTANTS.GAME_WIDTH - 100 },
          duration: 3000,
          yoyo: true,
          repeat: -1,
          ease: 'Sine.easeInOut'
        });
        
        // 开始发射弹幕
        this.bossShootTimer = this.time.addEvent({
          delay: ENEMY_TYPES.BOSS.fireRate,
          callback: this.bossShoot,
          callbackScope: this,
          loop: true
        });
      }
    });
  }

  private bossShoot() {
    if (!this.bossObj || !this.bossObj.active || this.isGameOver) return;
    
    // 发射扇形弹幕
    const angles = [-20, 0, 20];
    angles.forEach(angleOffset => {
      const bullet = this.physics.add.sprite(this.bossObj!.x, this.bossObj!.y + 50, 'tiles', 2);
      this.enemyBullets.add(bullet);
      bullet.setScale(1.5);
      const body = bullet.body as Phaser.Physics.Arcade.Body;
      body.setSize(8, 16);
      
      const rad = Phaser.Math.DegToRad(90 + angleOffset);
      const vx = Math.cos(rad) * CONSTANTS.ENEMY_BULLET_SPEED;
      const vy = Math.sin(rad) * CONSTANTS.ENEMY_BULLET_SPEED;
      bullet.setVelocity(vx, vy);
    });
  }

  private clearBoss() {
    this.isBossActive = false;
    this.bossObj = null;
    if (this.bossTween) this.bossTween.stop();
    if (this.bossShootTimer) this.bossShootTimer.remove();
  }
}

