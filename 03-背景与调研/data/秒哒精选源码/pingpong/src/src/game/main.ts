import Phaser from 'phaser';
import Boot from './scenes/Boot';
import StartScene from './scenes/StartScene';
import GameScene from './scenes/GameScene';
import EndScene from './scenes/EndScene';
import { CONSTANTS } from './constants';

export const config: Phaser.Types.Core.GameConfig = {
  type: Phaser.AUTO,
  parent: 'game-container',
  width: CONSTANTS.WIDTH,
  height: CONSTANTS.HEIGHT,
  scene: [Boot, StartScene, GameScene, EndScene],
  physics: {
    default: 'arcade',
    arcade: {
      gravity: { y: 0, x: 0 },
      debug: false
    }
  },
  scale: {
    mode: Phaser.Scale.FIT,
    autoCenter: Phaser.Scale.CENTER_BOTH
  },
  backgroundColor: '#000000',
  pixelArt: true // Ensures crisp rendering for pixel art aesthetics
};
