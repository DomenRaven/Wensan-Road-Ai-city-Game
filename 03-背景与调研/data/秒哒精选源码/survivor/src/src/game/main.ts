import { Boot } from './scenes/Boot';
import { Preloader } from './scenes/Preloader';
import { MainGame } from './scenes/MainGame';

export const GameConfig: Phaser.Types.Core.GameConfig = {
    type: Phaser.AUTO,
    parent: 'game-container',
    width: 800,
    height: 600,
    backgroundColor: '#FDFBF7', // 奶油白
    physics: {
        default: 'arcade',
        arcade: {
            gravity: { x: 0, y: 0 },
            debug: false
        }
    },
    scale: {
        mode: Phaser.Scale.FIT,
        autoCenter: Phaser.Scale.CENTER_BOTH
    },
    scene: [Boot, Preloader, MainGame]
};

export const createGame = () => {
    return new Phaser.Game(GameConfig);
};
