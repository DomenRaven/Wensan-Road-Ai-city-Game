import { Boot } from './scenes/Boot';
import { MainGame } from './scenes/MainGame';
import { GameOver } from './scenes/GameOver';
import { CONSTANTS } from './constants';
import Phaser from 'phaser';

export const gameConfig: Phaser.Types.Core.GameConfig = {
  type: Phaser.AUTO,
  width: CONSTANTS.GAME_WIDTH,
  height: CONSTANTS.GAME_HEIGHT,
  parent: 'game-container',
  scene: [Boot, MainGame, GameOver],
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
  pixelArt: true, // 保持像素风格不模糊
  transparent: false,
  backgroundColor: '#0a0a0c', // 深邃宇宙黑
};
