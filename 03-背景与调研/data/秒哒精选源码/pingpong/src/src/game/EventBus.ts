import Phaser from 'phaser';

export const EventBus = new Phaser.Events.EventEmitter();

export function startScene(scene: Phaser.Scene, key: string, data?: object) {
  if (!scene.scene.isActive(key)) {
    scene.scene.start(key, data);
    EventBus.emit('scene-changed', { key, data });
  }
}
