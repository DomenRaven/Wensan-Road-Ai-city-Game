import Phaser from 'phaser';
import { ASSETS, ASSET_SOURCES } from '../assets';

export default class Boot extends Phaser.Scene {
  constructor() {
    super('Boot');
  }

  preload() {
    // Generate fallback texture for load errors
    this.load.on('loaderror', (file: Phaser.Loader.File) => {
      const g = this.add.graphics();
      const w = this.game.config.width as number;
      const h = this.game.config.height as number;
      g.fillGradientStyle(0x667788, 0x334455, 0x334455, 0x667788);
      g.fillRect(0, 0, w, h);
      g.generateTexture(file.key, w, h);
      g.destroy();
    });

    this.load.image(ASSETS.court_bg, 'https://miaoda-site-img.cdn.bcebos.com/images/baidu_image_search_93fa6d43-a6d4-47bb-8ce7-2c140ba1e6b4.jpg');
    this.load.image(ASSETS.court_center_line, ASSET_SOURCES[ASSETS.court_center_line]);
    this.load.image(ASSETS.paddle_player, ASSET_SOURCES[ASSETS.paddle_player]);
    this.load.image(ASSETS.paddle_ai, ASSET_SOURCES[ASSETS.paddle_ai]);
    
    this.load.spritesheet(ASSETS.ball, ASSET_SOURCES[ASSETS.ball], { frameWidth: 48, frameHeight: 48 });
    this.load.image(ASSETS.ball_shadow, ASSET_SOURCES[ASSETS.ball_shadow]);
    this.load.spritesheet(ASSETS.score_digits, ASSET_SOURCES[ASSETS.score_digits], { frameWidth: 51, frameHeight: 96 });
    
    this.load.image(ASSETS.text_win, ASSET_SOURCES[ASSETS.text_win]);
    this.load.image(ASSETS.text_lose, ASSET_SOURCES[ASSETS.text_lose]);
    this.load.image(ASSETS.btn_start, ASSET_SOURCES[ASSETS.btn_start]);
    this.load.image(ASSETS.btn_again, ASSET_SOURCES[ASSETS.btn_again]);
    this.load.image(ASSETS.board, ASSET_SOURCES[ASSETS.board]);
  }

  create() {
    this.anims.create({
      key: 'ball_spin',
      frames: this.anims.generateFrameNumbers(ASSETS.ball, { start: 0, end: 5 }),
      frameRate: 12,
      repeat: -1
    });

    this.scene.start('StartScene');
  }
}
