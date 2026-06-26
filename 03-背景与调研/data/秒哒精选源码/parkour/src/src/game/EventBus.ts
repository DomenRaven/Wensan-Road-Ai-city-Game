import Phaser from 'phaser';

export const EventBus = new Phaser.Events.EventEmitter();

export const EVENTS = {
  SCENE_READY: 'scene-ready',
  GAME_START: 'game-start',
  GAME_OVER: 'game-over',
  SCORE_UPDATE: 'score-update',
  TIME_UPDATE: 'time-update',
};
