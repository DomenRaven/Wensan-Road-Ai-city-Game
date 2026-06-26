import { Scene } from 'phaser';
import { AssetUrls } from '../assets';

export class Boot extends Scene {
  constructor() {
    super('Boot');
  }

  preload() {
    this.load.image('player_car', AssetUrls.playerCar);
    this.load.image('npc_car_yellow', AssetUrls.npcCarYellow);
    this.load.image('npc_car_blue', AssetUrls.npcCarBlue);
    this.load.image('track_atlas', AssetUrls.trackAtlas);
    this.load.image('background', AssetUrls.background);
    this.load.image('logo', AssetUrls.logo);
    
    // Auto-generate fallback textures for load errors
    this.load.on('loaderror', (file: any) => {
      const g = this.add.graphics();
      const w = this.game.config.width as number;
      const h = this.game.config.height as number;
      g.fillGradientStyle(0x667788, 0x334455, 0x334455, 0x667788);
      g.fillRect(0, 0, w, h);
      g.generateTexture(file.key, w, h);
      g.destroy();
    });
  }

  create() {
    // Generate 'cone' obstacle texture
    const g = this.add.graphics();
    g.fillStyle(0xFF4500, 1);
    g.beginPath();
    g.moveTo(20, 0);
    g.lineTo(40, 40);
    g.lineTo(0, 40);
    g.closePath();
    g.fillPath();
    g.fillStyle(0xFFFFFF, 1);
    g.fillRect(8, 15, 24, 10);
    g.generateTexture('cone', 40, 40);
    g.destroy();

    // Generate Hit Sound
    try {
      const audioCtx = (this.sound as any).context as AudioContext;
      if (audioCtx) {
        const buffer = audioCtx.createBuffer(1, audioCtx.sampleRate * 0.2, audioCtx.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < buffer.length; i++) {
          data[i] = (Math.random() * 2 - 1) * Math.exp(-i / (audioCtx.sampleRate * 0.05));
        }
        this.cache.audio.add('hitSound', buffer);
      }
    } catch (e) {
      console.warn('Audio generation failed', e);
    }

    this.scene.start('MainGame');
  }
}
