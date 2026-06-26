import Phaser from 'phaser';
import { Boot } from './scenes/Boot';
import { MainGame } from './scenes/MainGame';

export const GAME_CONFIG: Phaser.Types.Core.GameConfig = {
  type: Phaser.AUTO,
  parent: 'game-container',
  width: 540,
  height: 960,
  scene: [Boot, MainGame],
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
  backgroundColor: '#87CEEB'
};
