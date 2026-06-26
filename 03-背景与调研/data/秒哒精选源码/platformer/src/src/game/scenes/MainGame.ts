import Phaser from 'phaser';
import { CONSTANTS } from '../constants';
import { useGameStore } from '../model/store';
import { EventBus } from '../EventBus';

export class MainGame extends Phaser.Scene {
  private player!: Phaser.Physics.Arcade.Sprite;
  private cursors!: Phaser.Types.Input.Keyboard.CursorKeys;
  private wasdKeys!: any;
  private enemies!: Phaser.Physics.Arcade.Group;
  private coins!: Phaser.Physics.Arcade.StaticGroup;
  private blocks!: Phaser.Physics.Arcade.StaticGroup;
  private ground!: Phaser.Physics.Arcade.StaticGroup;
  private goal!: Phaser.Physics.Arcade.Image;

  private isGameOver = false;
  private isInvincible = false;

  constructor() {
    super('MainGame');
  }

  create() {
    this.isGameOver = false;
    this.isInvincible = false;

    // 获取当前关卡并根据关卡重置状态
    const level = useGameStore.getState().level;

    // 设置物理世界边界 (关卡宽度)
    const levelWidth = CONSTANTS.GAME_WIDTH * 3;
    this.physics.world.setBounds(0, 0, levelWidth, CONSTANTS.GAME_HEIGHT);

    // 平铺背景
    this.add.tileSprite(0, 0, levelWidth, CONSTANTS.GAME_HEIGHT, 'background').setOrigin(0, 0);

    // 创建地面
    this.ground = this.physics.add.staticGroup();
    for (let x = 0; x < levelWidth; x += 32) {
      this.ground.create(x + 16, CONSTANTS.GAME_HEIGHT - 16, 'ground');
    }

    // 创建管道
    const pipe1 = this.physics.add.staticImage(400, CONSTANTS.GAME_HEIGHT - 32 - 48, 'pipe');
    const pipe2 = this.physics.add.staticImage(800, CONSTANTS.GAME_HEIGHT - 32 - 48, 'pipe');

    // 创建玩家
    this.player = this.physics.add.sprite(100, CONSTANTS.GAME_HEIGHT - 100, 'player_idle');
    this.player.setCollideWorldBounds(true);
    // 调整碰撞体大小以避免被卡住
    (this.player.body as Phaser.Physics.Arcade.Body).setSize(20, 24);
    (this.player.body as Phaser.Physics.Arcade.Body).setOffset(6, 8);
    this.player.play('player_idle');

    // 摄像机跟随
    this.cameras.main.startFollow(this.player, true, 0.1, 0.1);
    this.cameras.main.setBounds(0, 0, levelWidth, CONSTANTS.GAME_HEIGHT);

    // 创建输入
    if (this.input.keyboard) {
      this.cursors = this.input.keyboard.createCursorKeys();
      this.wasdKeys = this.input.keyboard.addKeys({
        up: Phaser.Input.Keyboard.KeyCodes.W,
        down: Phaser.Input.Keyboard.KeyCodes.S,
        left: Phaser.Input.Keyboard.KeyCodes.A,
        right: Phaser.Input.Keyboard.KeyCodes.D,
        space: Phaser.Input.Keyboard.KeyCodes.SPACE
      });
      // 避免按键页面滚动
      this.input.keyboard.addCapture('UP,DOWN,LEFT,RIGHT,SPACE');
    }

    // 敌人分组
    this.enemies = this.physics.add.group();
    
    // 金币分组
    this.coins = this.physics.add.staticGroup();

    // 砖块分组
    this.blocks = this.physics.add.staticGroup();

    // 终点
    this.goal = this.physics.add.staticImage(levelWidth - 100, CONSTANTS.GAME_HEIGHT - 32 - 32, 'goal_idle');

    this.generateLevelData(levelWidth);

    // 碰撞设置
    this.physics.add.collider(this.player, this.ground);
    this.physics.add.collider(this.player, pipe1);
    this.physics.add.collider(this.player, pipe2);
    this.physics.add.collider(this.enemies, this.ground);
    this.physics.add.collider(this.enemies, pipe1);
    this.physics.add.collider(this.enemies, pipe2);

    this.physics.add.collider(this.player, this.blocks, this.hitBlock, undefined, this);
    this.physics.add.overlap(this.player, this.coins, this.collectCoin, undefined, this);
    this.physics.add.collider(this.player, this.enemies, this.hitEnemy, undefined, this);
    this.physics.add.overlap(this.player, this.goal, this.reachGoal, undefined, this);

    // Eventbus 监听 React 重置游戏事件
    EventBus.off('restart-game', this.restartGame, this);
    EventBus.on('restart-game', this.restartGame, this);
  }

  shutdown() {
    EventBus.off('restart-game', this.restartGame, this);
  }

  private restartGame() {
    this.scene.restart();
  }

  private generateLevelData(width: number) {
    // 随机生成一些砖块、金币和敌人
    for (let x = 600; x < width - 300; x += 150) {
      // 随机生成砖块
      if (Phaser.Math.Between(0, 100) > 30) {
        const block = this.blocks.create(x, CONSTANTS.GAME_HEIGHT - 150, 'box_idle');
        (block.body as Phaser.Physics.Arcade.Body).setSize(28, 24);
      }

      // 随机生成金币
      if (Phaser.Math.Between(0, 100) > 40) {
        const coin = this.coins.create(x + 30, CONSTANTS.GAME_HEIGHT - 100, 'coin_spin');
        coin.play('coin_spin');
      } else if (Phaser.Math.Between(0, 100) > 70) {
        const coin = this.coins.create(x, CONSTANTS.GAME_HEIGHT - 200, 'coin_spin');
        coin.play('coin_spin');
      }

      // 随机生成敌人
      if (Phaser.Math.Between(0, 100) > 50) {
        const enemy = this.enemies.create(x + 50, CONSTANTS.GAME_HEIGHT - 64, 'enemy');
        enemy.setVelocityX(Phaser.Math.Between(0, 1) === 0 ? CONSTANTS.ENEMY_SPEED : -CONSTANTS.ENEMY_SPEED);
        enemy.setBounceX(1);
        enemy.setCollideWorldBounds(true);
      }
    }
  }

  update() {
    if (this.isGameOver) return;

    // 敌人行为
    this.enemies.getChildren().forEach((enemyGO) => {
      const enemy = enemyGO as Phaser.Physics.Arcade.Sprite;
      if (enemy.body && enemy.body.velocity.x === 0) {
        enemy.setVelocityX(Phaser.Math.Between(0, 1) === 0 ? CONSTANTS.ENEMY_SPEED : -CONSTANTS.ENEMY_SPEED);
      }
    });

    const isLeftDown = this.cursors.left.isDown || this.wasdKeys.left.isDown;
    const isRightDown = this.cursors.right.isDown || this.wasdKeys.right.isDown;
    const isJumpDown = Phaser.Input.Keyboard.JustDown(this.cursors.up) || Phaser.Input.Keyboard.JustDown(this.wasdKeys.up) || Phaser.Input.Keyboard.JustDown(this.wasdKeys.space);
    const body = this.player.body as Phaser.Physics.Arcade.Body;
    const isGrounded = body.blocked.down || body.touching.down;

    // 水平移动
    if (isLeftDown) {
      this.player.setVelocityX(-CONSTANTS.PLAYER_SPEED);
      this.player.setFlipX(true);
      if (isGrounded && !this.isInvincible) this.player.play('player_run', true);
    } else if (isRightDown) {
      this.player.setVelocityX(CONSTANTS.PLAYER_SPEED);
      this.player.setFlipX(false);
      if (isGrounded && !this.isInvincible) this.player.play('player_run', true);
    } else {
      this.player.setVelocityX(0);
      if (isGrounded && !this.isInvincible) this.player.play('player_idle', true);
    }

    // 跳跃
    if (isJumpDown && isGrounded) {
      this.player.setVelocityY(CONSTANTS.PLAYER_JUMP);
    }

    // 空中动画
    if (!isGrounded && !this.isInvincible) {
      if (body.velocity.y < 0) {
        this.player.setTexture('player_jump');
      } else {
        this.player.setTexture('player_fall');
      }
    }

    // 掉出世界判定 (深坑)
    if (this.player.y > CONSTANTS.GAME_HEIGHT + 50) {
      this.handlePlayerDeath();
    }
  }

  private hitBlock(playerGO: any, blockGO: any) {
    if (this.isGameOver) return;
    
    const body = this.player.body as Phaser.Physics.Arcade.Body;
    const blockBody = blockGO.body as Phaser.Physics.Arcade.Body;
    
    // 如果玩家从下往上顶
    if (body.touching.up && blockBody.touching.down) {
      const block = blockGO as Phaser.Physics.Arcade.Sprite;
      
      // 停止上升
      this.player.setVelocityY(0);
      
      block.play('box_hit');
      
      // 有概率出金币
      if (Phaser.Math.Between(0, 100) > 50) {
        const coin = this.coins.create(block.x, block.y - 32, 'coin_spin');
        coin.play('coin_spin');
      } else {
        // 碎裂
        block.play('box_break');
        block.once('animationcomplete', () => {
          block.destroy();
        });
        (block.body as Phaser.Physics.Arcade.Body).enable = false;
      }
    }
  }

  private collectCoin(playerGO: any, coinGO: any) {
    if (this.isGameOver) return;
    const coin = coinGO as Phaser.Physics.Arcade.Sprite;
    
    // 禁用物理体，防止重复触发
    (coin.body as Phaser.Physics.Arcade.Body).enable = false;
    
    coin.play('coin_collected');
    useGameStore.getState().addCoin();
    
    coin.once('animationcomplete', () => {
      coin.destroy();
    });
  }

  private hitEnemy(playerGO: any, enemyGO: any) {
    if (this.isGameOver || this.isInvincible) return;

    const body = this.player.body as Phaser.Physics.Arcade.Body;
    const enemyBody = enemyGO.body as Phaser.Physics.Arcade.Body;
    const enemy = enemyGO as Phaser.Physics.Arcade.Sprite;

    // 踩踏判定：玩家在下落且接触敌人上方
    if (body.velocity.y > 0 && body.bottom < enemyBody.center.y) {
      // 踩死敌人
      this.player.setVelocityY(CONSTANTS.BOUNCE_ON_ENEMY);
      enemy.destroy();
      useGameStore.getState().addScore(CONSTANTS.SCORE_ENEMY);
    } else {
      // 受到伤害
      this.handlePlayerDeath();
    }
  }

  private handlePlayerDeath() {
    if (this.isGameOver || this.isInvincible) return;

    this.isInvincible = true;
    this.player.play('player_hit');
    
    const store = useGameStore.getState();
    store.loseLife();

    if (store.lives <= 0) {
      this.isGameOver = true;
      this.player.setTint(0xff0000);
      this.player.setVelocity(0, 0);
      this.physics.pause();
      
      this.time.delayedCall(1000, () => {
        store.setStatus('gameover');
      });
    } else {
      // 重置位置
      this.player.setVelocity(0, 0);
      this.player.setTint(0xff0000);
      
      // 无敌闪烁
      this.tweens.add({
        targets: this.player,
        alpha: { from: 1, to: 0.2 },
        duration: 100,
        yoyo: true,
        repeat: CONSTANTS.INVINCIBLE_TIME / 200,
        onComplete: () => {
          this.isInvincible = false;
          this.player.clearTint();
          this.player.setAlpha(1);
        }
      });

      // 如果掉下坑，重置到开头
      if (this.player.y > CONSTANTS.GAME_HEIGHT) {
        (this.player.body as Phaser.Physics.Arcade.Body).reset(100, CONSTANTS.GAME_HEIGHT - 100);
      }
    }
  }

  private reachGoal(playerGO: any, goalGO: any) {
    if (this.isGameOver) return;
    
    this.isGameOver = true;
    this.physics.pause();
    
    // 把 goal 临时当成 Sprite 播放动画（这里使用了staticImage，但是也可以用Sprite）
    // 为了播放动画，需要将其转换为Sprite
    const x = this.goal.x;
    const y = this.goal.y;
    this.goal.destroy();
    
    const goalSprite = this.add.sprite(x, y, 'goal_pressed');
    goalSprite.play('goal_pressed');

    useGameStore.getState().addScore(CONSTANTS.SCORE_GOAL);
    
    this.time.delayedCall(1500, () => {
      const store = useGameStore.getState();
      store.nextLevel();
      store.setStatus('victory');
    });
  }
}
