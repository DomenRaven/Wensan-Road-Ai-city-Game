import { Scene } from 'phaser';
import { ASSETS } from '../assets';
import { EventBus } from '../EventBus';

export class Boot extends Scene {
  constructor() {
    super('Boot');
  }

  preload() {
    // 处理图片加载失败的回调（规则要求）
    this.load.on('loaderror', (file: any) => {
      const g = this.add.graphics();
      const w = this.game.config.width as number;
      const h = this.game.config.height as number;
      g.fillGradientStyle(0x667788, 0x334455, 0x334455, 0x667788);
      g.fillRect(0, 0, w, h);
      g.generateTexture(file.key, 32, 32);
      g.destroy();
    });

    this.load.spritesheet('ships', ASSETS.ships, {
      frameWidth: 32,
      frameHeight: 32,
      spacing: 1
    });

    this.load.spritesheet('tiles', ASSETS.tiles, {
      frameWidth: 16,
      frameHeight: 16,
      spacing: 1
    });

    this.load.image('background', ASSETS.background);
    
    // 我们在此处生成简单的 base64 占位音频，Phaser 会解析它们
    // shoot
    this.load.audio('shoot', 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=');
    // explosion
    this.load.audio('explosion', 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=');
  }

  create() {
    // 爆炸动画
    this.anims.create({
      key: 'explode',
      frames: this.anims.generateFrameNumbers('tiles', { frames: [4, 5, 6, 7] }),
      frameRate: 12,
      repeat: 0
    });

    EventBus.emit('scene-changed', { key: 'Boot' });

    // 等待 React 发出开始事件（玩家点击按钮）
    EventBus.on('start-game', this.startGame, this);
    
    this.events.on('shutdown', () => {
      EventBus.off('start-game', this.startGame, this);
    });
  }

  startGame() {
    this.scene.start('MainGame');
  }
}
