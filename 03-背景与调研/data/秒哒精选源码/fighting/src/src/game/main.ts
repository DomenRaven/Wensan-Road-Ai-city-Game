import Phaser from 'phaser';
import { Boot } from './scenes/Boot';
import { Battle } from './scenes/Battle';
import { BATTLE_CONSTANTS } from './constants';

export const config: Phaser.Types.Core.GameConfig = {
  type: Phaser.AUTO,
  width: BATTLE_CONSTANTS.ARENA_WIDTH,
  height: BATTLE_CONSTANTS.ARENA_HEIGHT,
  parent: 'game-container',
  backgroundColor: '#F4F1EA',
  physics: {
    default: 'arcade',
    arcade: {
      gravity: { x: 0, y: BATTLE_CONSTANTS.GRAVITY },
      debug: false
    }
  },
  scale: {
    mode: Phaser.Scale.FIT,
    autoCenter: Phaser.Scale.CENTER_BOTH
  },
  scene: [Boot, Battle]
};
