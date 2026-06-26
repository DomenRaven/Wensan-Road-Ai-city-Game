import Phaser from 'phaser';
import { ASSETS } from '../assets';

export class Boot extends Phaser.Scene {
  constructor() {
    super('Boot');
  }

  preload() {
    this.load.spritesheet('char_idle', ASSETS.char_idle, { frameWidth: 32, frameHeight: 32 });
    this.load.spritesheet('char_run', ASSETS.char_run, { frameWidth: 32, frameHeight: 32 });
    this.load.spritesheet('char_jump', ASSETS.char_jump, { frameWidth: 32, frameHeight: 32 });
    this.load.spritesheet('char_fall', ASSETS.char_fall, { frameWidth: 32, frameHeight: 32 });
    this.load.spritesheet('char_hit', ASSETS.char_hit, { frameWidth: 32, frameHeight: 32 });
  }

  create() {
    this.anims.create({ key: 'anim_idle', frames: this.anims.generateFrameNumbers('char_idle', { start: 0, end: 10 }), frameRate: 11, repeat: -1 });
    this.anims.create({ key: 'anim_run', frames: this.anims.generateFrameNumbers('char_run', { start: 0, end: 11 }), frameRate: 12, repeat: -1 });
    this.anims.create({ key: 'anim_jump', frames: this.anims.generateFrameNumbers('char_jump', { start: 0, end: 0 }), frameRate: 1, repeat: 0 });
    this.anims.create({ key: 'anim_fall', frames: this.anims.generateFrameNumbers('char_fall', { start: 0, end: 0 }), frameRate: 1, repeat: 0 });
    this.anims.create({ key: 'anim_hit', frames: this.anims.generateFrameNumbers('char_hit', { start: 0, end: 6 }), frameRate: 10, repeat: 0 });

    this.scene.start('Game');
  }
}
