import { Scene } from 'phaser';
import { AssetPaths } from '../assets';
import { EventBus, GameEvents } from '../EventBus';

export class Preloader extends Scene {
    constructor() {
        super('Preloader');
    }

    preload() {
        // 绘制背景和进度条
        this.cameras.main.setBackgroundColor('#FDFBF7');

        const width = this.cameras.main.width;
        const height = this.cameras.main.height;

        const progressBar = this.add.graphics();
        const progressBox = this.add.graphics();
        progressBox.fillStyle(0xdddddd, 0.8);
        progressBox.fillRect(width / 2 - 160, height / 2 - 25, 320, 50);

        this.load.on('progress', (value: number) => {
            progressBar.clear();
            progressBar.fillStyle(0x42D6A4, 1);
            progressBar.fillRect(width / 2 - 150, height / 2 - 15, 300 * value, 30);
        });

        // 绑定 loaderror，对于报错生成替补资源
        this.load.on('loaderror', (fileObj: any) => {
            console.error('Failed to load asset', fileObj);
            const g = this.add.graphics();
            g.fillStyle(0x667788, 1);
            g.fillRect(0, 0, 32, 32);
            g.generateTexture(fileObj.key, 32, 32);
            g.destroy();
        });

        // 加载玩家
        this.load.image('player_idle', AssetPaths.player.idle);
        AssetPaths.player.walk.forEach((url, i) => {
            this.load.image(`player_walk_${i + 1}`, url);
        });

        // 加载敌人
        Object.entries(AssetPaths.monsters).forEach(([type, urls]) => {
            urls.forEach((url, i) => {
                this.load.image(`monster_${type}_${i + 1}`, url);
            });
        });

        // 加载物品和特效
        this.load.image('item_exp_gem', AssetPaths.items.expGem);
        this.load.image('fx_hit', AssetPaths.fx.hit);
    }

    create() {
        // 注册全局动画
        this.anims.create({
            key: 'player_walk',
            frames: [
                { key: 'player_walk_1' },
                { key: 'player_walk_2' },
                { key: 'player_walk_3' },
                { key: 'player_walk_4' }
            ],
            frameRate: 8,
            repeat: -1
        });

        const types = ['1', '3', '6'];
        types.forEach(type => {
            this.anims.create({
                key: `enemy_walk_${type}`,
                frames: [
                    { key: `monster_${type}_1` },
                    { key: `monster_${type}_2` },
                    { key: `monster_${type}_3` },
                    { key: `monster_${type}_4` }
                ],
                frameRate: 6,
                repeat: -1
            });
        });

        // 通知 React 层，已经 ready，可以显示开始按钮
        EventBus.emit(GameEvents.SCENE_READY);
        // 但是游戏本身需要停在这里，等玩家点开始
        // 我们可以起一个空场景或者只是在 MainGame 里面 wait
        // 我们直接跳转到 MainGame，但把状态置为不开始，或者 MainGame 中通过 event bus 监听 start
        this.scene.start('MainGame');
    }
}
