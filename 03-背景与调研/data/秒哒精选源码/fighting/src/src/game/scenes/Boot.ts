import { Scene } from 'phaser';
import { EventBus } from '../EventBus';
import { getCharacterFrame, UI_ASSETS } from '../assets';

export class Boot extends Scene {
  constructor() {
    super('Boot');
  }

  preload() {
    // Basic loading logic to handle missing images using loaderror event
    this.load.on('loaderror', (fileObj: any) => {
      console.warn('Failed to load asset:', fileObj.key);
      const g = this.add.graphics();
      const w = this.game.config.width as number;
      const h = this.game.config.height as number;
      g.fillGradientStyle(0x667788, 0x334455, 0x334455, 0x667788);
      g.fillRect(0, 0, w, h);
      g.generateTexture(fileObj.key, 100, 100); // 100x100 square for errors
      g.destroy();
    });

    // 1. Load Background & UI
    this.load.image('bg_battle', UI_ASSETS.bg_battle);
    this.load.image('ui_hp_bg', UI_ASSETS.ui_hp_bg);
    this.load.image('ui_hp_green', UI_ASSETS.ui_hp_green);
    this.load.image('ui_hp_enemy', UI_ASSETS.ui_hp_enemy);

    // 2. Load Characters (Char1, Char2, Char3)
    const CHARS = ['Char1', 'Char2', 'Char3'];
    const ANIMS: Record<string, number> = { Idle: 10, Walk: 18, Hit: 22, GetHit: 14, Defense: 14, Death: 35, Opening: 14 };
    
    CHARS.forEach(char => {
      Object.entries(ANIMS).forEach(([anim, count]) => {
        for (let i = 0; i < count; i++) {
          const frameUrl = getCharacterFrame(char, anim, i);
          if (frameUrl) {
            this.load.image(`${char.toLowerCase()}_${anim.toLowerCase()}_${i}`, frameUrl);
          }
        }
      });
    });
  }

  create() {
    // Register animations
    const CHARS = ['Char1', 'Char2', 'Char3'];
    const ANIM_DEFS = [
      { name: 'idle',    folder: 'Idle',    frames: 10, fps: 10, repeat: -1 },
      { name: 'walk',    folder: 'Walk',    frames: 18, fps: 12, repeat: -1 },
      { name: 'hit',     folder: 'Hit',     frames: 22, fps: 18, repeat: 0  },
      { name: 'gethit',  folder: 'GetHit',  frames: 14, fps: 14, repeat: 0  },
      { name: 'defense', folder: 'Defense', frames: 14, fps: 12, repeat: -1 },
      { name: 'death',   folder: 'Death',   frames: 35, fps: 12, repeat: 0  },
      { name: 'opening', folder: 'Opening', frames: 14, fps: 12, repeat: 0  }
    ];

    CHARS.forEach(char => {
      const c = char.toLowerCase();
      ANIM_DEFS.forEach(def => {
        // Prepare frames mapping
        const framesData = [];
        for (let i = 0; i < def.frames; i++) {
          const key = `${c}_${def.name}_${i}`;
          if (this.textures.exists(key)) {
            framesData.push({ key });
          }
        }

        if (framesData.length > 0) {
          this.anims.create({
            key: `${c}_${def.name}`,
            frames: framesData,
            frameRate: def.fps,
            repeat: def.repeat
          });
        }
      });
    });

    // Notify React that boot is complete, React handles transitioning state to menu
    EventBus.emit('scene-changed', { key: 'Boot' });
  }
}
