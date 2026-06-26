import Phaser from 'phaser';

export const EventBus = new Phaser.Events.EventEmitter();

export const GameEvents = {
  SCENE_READY: 'scene-ready',
  START_GAME: 'start-game',
  GAME_OVER: 'game-over',
  VICTORY: 'victory',
  TRIGGER_UPGRADE: 'trigger-upgrade',
  UPGRADE_APPLIED: 'upgrade-applied',
  RESTART_GAME: 'restart-game'
};
