import Phaser from 'phaser';
import { ASSETS } from '../assets';
import { startScene } from '../EventBus';
import { CONSTANTS } from '../constants';
import { useGameStore } from '../model/store';

export default class StartScene extends Phaser.Scene {
  constructor() {
    super('StartScene');
  }

  create() {
    // According to aesthetic template: Pure black background
    this.add.rectangle(0, 0, CONSTANTS.WIDTH, CONSTANTS.HEIGHT, 0x000000).setOrigin(0);

    // Title
    const title = this.add.text(CONSTANTS.WIDTH / 2, CONSTANTS.HEIGHT * 0.3, 'K12 乒乓球', {
      fontFamily: 'monospace',
      fontSize: '64px',
      color: '#39FF14'
    }).setOrigin(0.5);

    // Start Button
    const startBtn = this.add.image(CONSTANTS.WIDTH / 2, CONSTANTS.HEIGHT * 0.6, ASSETS.btn_start)
      .setDisplaySize(145, 310)
      .setInteractive({ useHandCursor: true })
      .setTintFill(0x39FF14); // Apply neon green solid block to the start button

    // Blinking effect for start button
    this.tweens.add({
      targets: startBtn,
      alpha: { from: 1, to: 0.1 },
      duration: 500,
      yoyo: true,
      repeat: -1
    });

    startBtn.on('pointerdown', () => {
      useGameStore.getState().resetGame();
      startScene(this, 'GameScene');
    });

    if (this.input.keyboard) {
      this.input.keyboard.once('keydown-SPACE', () => {
        useGameStore.getState().resetGame();
        startScene(this, 'GameScene');
      });
    }
  }
}
