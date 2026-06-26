import Phaser from 'phaser';
import { EventBus, EVENTS } from '../EventBus';
import { CONSTANTS } from '../constants';

export class GameOver extends Phaser.Scene {
  constructor() {
    super('GameOver');
  }

  create() {
    // 监听重新开始事件
    const onRestart = () => {
      this.scene.start('Game');
    };
    
    EventBus.once('ui-restart-game', onRestart);

    this.events.on('shutdown', () => {
      EventBus.off('ui-restart-game', onRestart);
    });
  }
}
