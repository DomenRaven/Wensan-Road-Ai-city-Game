import { Scene } from 'phaser';
import { EventBus } from '../EventBus';

export class GameOver extends Scene {
  constructor() {
    super('GameOver');
  }

  create() {
    EventBus.emit('scene-changed', { key: 'GameOver' });

    // 等待 React 发出重启事件
    this.events.once('shutdown', () => {
      EventBus.off('restart-game', this.onRestart, this);
    });

    EventBus.on('restart-game', this.onRestart, this);
  }

  onRestart() {
    this.scene.start('MainGame');
  }
}
