import Phaser from 'phaser';

// Used to emit events between React and Phaser
export const EventBus = new Phaser.Events.EventEmitter();

export function startScene(scene: Phaser.Scene, key: string, data?: object) {
  scene.scene.start(key, data);
  EventBus.emit('scene-changed', { key, data });
}
