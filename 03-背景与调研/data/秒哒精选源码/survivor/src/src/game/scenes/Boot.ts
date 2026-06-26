import { Scene } from 'phaser';

export class Boot extends Scene {
    constructor() {
        super('Boot');
    }

    preload() {
        // 在 Boot 场景中只加载极少量的资源，比如 Preloader 用的进度条图片等
        // 这里没有所以直接略过
    }

    create() {
        this.scene.start('Preloader');
    }
}
