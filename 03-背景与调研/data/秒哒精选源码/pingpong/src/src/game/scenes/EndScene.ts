import Phaser from 'phaser';
import { ASSETS } from '../assets';
import { CONSTANTS } from '../constants';
import { useGameStore } from '../model/store';
import { startScene } from '../EventBus';

export default class EndScene extends Phaser.Scene {
  constructor() {
    super('EndScene');
  }

  create() {
    const { winner, playerScore, aiScore } = useGameStore.getState();

    // Pure black background
    this.add.rectangle(0, 0, CONSTANTS.WIDTH, CONSTANTS.HEIGHT, 0x000000).setOrigin(0);

    // Board background tinted
    const board = this.add.image(CONSTANTS.WIDTH / 2, CONSTANTS.HEIGHT / 2 - 50, ASSETS.board)
      .setDisplaySize(410, 325)
      .setTintFill(0x222222); // Dark grey block
      
    // Text based on winner
    if (winner === 'player') {
      this.add.image(CONSTANTS.WIDTH / 2, CONSTANTS.HEIGHT / 2 - 120, ASSETS.text_win)
        .setDisplaySize(370, 95)
        .setTint(0x39FF14);
    } else {
      this.add.image(CONSTANTS.WIDTH / 2, CONSTANTS.HEIGHT / 2 - 120, ASSETS.text_lose)
        .setDisplaySize(376, 101)
        .setTint(0xFF3333);
    }

    // Final score text
    this.add.text(CONSTANTS.WIDTH / 2, CONSTANTS.HEIGHT / 2 + 20, `${playerScore} - ${aiScore}`, {
      fontFamily: 'monospace',
      fontSize: '64px',
      color: '#ffffff'
    }).setOrigin(0.5);

    // Play Again button
    const againBtn = this.add.image(CONSTANTS.WIDTH / 2, CONSTANTS.HEIGHT / 2 + 200, ASSETS.btn_again)
      .setDisplaySize(87, 174)
      .setInteractive()
      .setTintFill(0x39FF14);

    this.tweens.add({
      targets: againBtn,
      alpha: { from: 1, to: 0.5 },
      duration: 500,
      ease: 'Stepped',
      easeParams: [1],
      yoyo: true,
      repeat: -1
    });

    againBtn.on('pointerdown', () => {
      useGameStore.getState().resetGame();
      startScene(this, 'GameScene');
    });

    this.input.keyboard?.once('keydown-SPACE', () => {
      useGameStore.getState().resetGame();
      startScene(this, 'GameScene');
    });
  }
}
