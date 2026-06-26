import Phaser from 'phaser';
import { AssetImports } from '../AssetImports';

export class Boot extends Phaser.Scene {
  constructor() {
    super('Boot');
  }

  preload() {
    // 玩家
    this.load.spritesheet('player_idle', AssetImports.playerIdle, { frameWidth: 32, frameHeight: 32 });
    this.load.spritesheet('player_run', AssetImports.playerRun, { frameWidth: 32, frameHeight: 32 });
    this.load.image('player_jump', AssetImports.playerJump);
    this.load.image('player_fall', AssetImports.playerFall);
    this.load.spritesheet('player_hit', AssetImports.playerHit, { frameWidth: 32, frameHeight: 32 });

    // 砖块
    this.load.image('box_idle', AssetImports.boxIdle);
    this.load.spritesheet('box_hit', AssetImports.boxHit, { frameWidth: 28, frameHeight: 24 });
    this.load.spritesheet('box_break', AssetImports.boxBreak, { frameWidth: 28, frameHeight: 24 });

    // 金币
    this.load.spritesheet('coin_spin', AssetImports.coinSpin, { frameWidth: 32, frameHeight: 32 });
    this.load.spritesheet('coin_collected', AssetImports.coinCollected, { frameWidth: 32, frameHeight: 32 });

    // 终点
    this.load.image('goal_idle', AssetImports.goalIdle);
    this.load.spritesheet('goal_pressed', AssetImports.goalPressed, { frameWidth: 64, frameHeight: 64 });

    // 背景
    this.load.image('background', AssetImports.backgroundBlue);

    // 自动生成缺失贴图
    this.load.on('loaderror', (file: any) => {
      console.warn('Load error, generating fallback for:', file.key);
      const g = this.add.graphics();
      g.fillStyle(0xff00ff);
      g.fillRect(0, 0, 32, 32);
      g.generateTexture(file.key, 32, 32);
      g.destroy();
    });
  }

  create() {
    // 创建缺失的材质 (敌人、管道、地面)
    const gEnemy = this.add.graphics();
    gEnemy.fillStyle(0x00aa00); // 绿色敌人
    gEnemy.fillRect(0, 0, 32, 32);
    gEnemy.generateTexture('enemy', 32, 32);
    gEnemy.destroy();

    const gPipe = this.add.graphics();
    gPipe.fillStyle(0x00cc00); // 绿色管道
    gPipe.fillRect(0, 0, 48, 96);
    gPipe.generateTexture('pipe', 48, 96);
    gPipe.destroy();

    const gGround = this.add.graphics();
    gGround.fillStyle(0x8B4513); // 棕色地面
    gGround.fillRect(0, 0, 32, 32);
    gGround.generateTexture('ground', 32, 32);
    gGround.destroy();

    // 注册动画
    this.anims.create({ key: 'player_idle', frames: this.anims.generateFrameNumbers('player_idle', { start: 0, end: 10 }), frameRate: 10, repeat: -1 });
    this.anims.create({ key: 'player_run', frames: this.anims.generateFrameNumbers('player_run', { start: 0, end: 11 }), frameRate: 12, repeat: -1 });
    this.anims.create({ key: 'player_hit', frames: this.anims.generateFrameNumbers('player_hit', { start: 0, end: 6 }), frameRate: 10, repeat: 0 });

    this.anims.create({ key: 'box_hit', frames: this.anims.generateFrameNumbers('box_hit', { start: 0, end: 2 }), frameRate: 10, repeat: 0 });
    this.anims.create({ key: 'box_break', frames: this.anims.generateFrameNumbers('box_break', { start: 0, end: 3 }), frameRate: 10, repeat: 0 });

    this.anims.create({ key: 'coin_spin', frames: this.anims.generateFrameNumbers('coin_spin', { start: 0, end: 16 }), frameRate: 12, repeat: -1 });
    this.anims.create({ key: 'coin_collected', frames: this.anims.generateFrameNumbers('coin_collected', { start: 0, end: 5 }), frameRate: 12, repeat: 0 });

    this.anims.create({ key: 'goal_pressed', frames: this.anims.generateFrameNumbers('goal_pressed', { start: 0, end: 7 }), frameRate: 8, repeat: 0 });

    // 不要在这里启动MainGame，让React来启动
    // this.scene.start('MainGame');

    // 监听React发出的启动信号
    import('../EventBus').then(({ EventBus }) => {
      EventBus.on('scene-changed', (data: any) => {
        if (data && data.key === 'MainGame') {
          this.scene.start('MainGame');
        }
      });
    });
  }
}
