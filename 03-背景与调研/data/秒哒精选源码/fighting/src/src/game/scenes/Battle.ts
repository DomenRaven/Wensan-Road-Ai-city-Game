import { Scene } from 'phaser';
import { EventBus } from '../EventBus';
import { BATTLE_CONSTANTS } from '../constants';
import { useGameStore } from '../store';

export class Battle extends Scene {
  private player!: Phaser.Physics.Arcade.Sprite;
  private enemy!: Phaser.Physics.Arcade.Sprite;
  private playerHpBar!: Phaser.GameObjects.Image;
  private enemyHpBar!: Phaser.GameObjects.Image;
  private keys!: Record<string, Phaser.Input.Keyboard.Key>;

  private aiNextActionTime = 0;

  constructor() {
    super('Battle');
  }

  create(data: { playerChar: string }) {
    // 1. Setup Background
    const bg = this.add.image(0, 0, 'bg_battle').setOrigin(0, 0);
    // Scale background to fit arena
    bg.setDisplaySize(BATTLE_CONSTANTS.ARENA_WIDTH, BATTLE_CONSTANTS.ARENA_HEIGHT);

    // Setup bounds
    this.physics.world.setBounds(0, 0, BATTLE_CONSTANTS.ARENA_WIDTH, BATTLE_CONSTANTS.ARENA_HEIGHT);

    const playerChar = data.playerChar.toLowerCase();
    const enemyChar = 'char3'; // AI is always Char3

    // 2. Setup UI HP Bars
    const maxHp = BATTLE_CONSTANTS.HP_MAX;
    
    // Player HP
    this.add.image(200, 50, 'ui_hp_bg').setScale(0.8);
    this.playerHpBar = this.add.image(200 - (384 * 0.8 / 2) + 20, 50, 'ui_hp_green')
      .setOrigin(0, 0.5)
      .setScale(0.8);

    // Enemy HP
    this.add.image(BATTLE_CONSTANTS.ARENA_WIDTH - 200, 50, 'ui_hp_bg').setScale(0.8);
    this.enemyHpBar = this.add.image(BATTLE_CONSTANTS.ARENA_WIDTH - 200 + (384 * 0.8 / 2) - 20, 50, 'ui_hp_enemy')
      .setOrigin(1, 0.5)
      .setScale(0.8);

    // 3. Setup Characters
    this.player = this.physics.add.sprite(200, BATTLE_CONSTANTS.GROUND_Y, `${playerChar}_idle_0`);
    this.enemy = this.physics.add.sprite(BATTLE_CONSTANTS.ARENA_WIDTH - 200, BATTLE_CONSTANTS.GROUND_Y, `${enemyChar}_idle_0`);

    [this.player, this.enemy].forEach(sprite => {
      sprite.setCollideWorldBounds(true);
      (sprite.body as Phaser.Physics.Arcade.Body).setSize(100, 200); // Base hitbox
      (sprite.body as Phaser.Physics.Arcade.Body).setOffset(150, 100);
      sprite.setDepth(10);
    });

    this.enemy.setFlipX(true); // AI faces left

    // Set state
    this.player.setData('char', playerChar);
    this.player.setData('state', 'idle'); // idle, walk, hit, gethit, defense, death
    this.player.setData('hp', maxHp);
    
    this.enemy.setData('char', enemyChar);
    this.enemy.setData('state', 'idle');
    this.enemy.setData('hp', maxHp);

    this.player.play(`${playerChar}_idle`);
    this.enemy.play(`${enemyChar}_idle`);

    // 4. Input Setup
    if (this.input.keyboard) {
      this.keys = this.input.keyboard.addKeys('LEFT,RIGHT,J,K') as Record<string, Phaser.Input.Keyboard.Key>;
      this.input.keyboard.addCapture('LEFT,RIGHT,J,K,SPACE,UP,DOWN');
    }

    // 5. Setup Animation Callbacks for Damage
    this.player.on('animationupdate', (anim: Phaser.Animations.Animation, frame: Phaser.Animations.AnimationFrame) => {
      this.checkHitFrame(anim, frame, this.player, this.enemy);
    });

    this.enemy.on('animationupdate', (anim: Phaser.Animations.Animation, frame: Phaser.Animations.AnimationFrame) => {
      this.checkHitFrame(anim, frame, this.enemy, this.player);
    });

    // Completion callbacks
    this.player.on('animationcomplete', this.onAnimationComplete, this);
    this.enemy.on('animationcomplete', this.onAnimationComplete, this);
  }

  private checkHitFrame(anim: Phaser.Animations.Animation, frame: Phaser.Animations.AnimationFrame, attacker: Phaser.Physics.Arcade.Sprite, defender: Phaser.Physics.Arcade.Sprite) {
    const char = attacker.getData('char');
    const attackerState = attacker.getData('state');
    
    if (anim.key === `${char}_hit` && attackerState === 'hit') {
      const fi = frame.index - 1;
      // Active frames: 7 to 14
      if (fi === 7) { 
        // Only trigger once at start of active frame
        // Check distance
        const distance = Math.abs(attacker.x - defender.x);
        if (distance < 200) {
          // Hit!
          this.applyDamage(attacker, defender);
        }
      }
    }
  }

  private onAnimationComplete(anim: Phaser.Animations.Animation, frame: Phaser.Animations.AnimationFrame, sprite: Phaser.GameObjects.Sprite) {
    const s = sprite as Phaser.Physics.Arcade.Sprite;
    const char = s.getData('char');
    if (anim.key === `${char}_hit` || anim.key === `${char}_gethit`) {
      if (s.getData('state') !== 'death') {
        s.setData('state', 'idle');
        s.play(`${char}_idle`);
      }
    } else if (anim.key === `${char}_death`) {
      // Game over transition handled in update loop when HP <= 0 is detected
    }
  }

  private applyDamage(attacker: Phaser.Physics.Arcade.Sprite, defender: Phaser.Physics.Arcade.Sprite) {
    const defenderState = defender.getData('state');
    if (defenderState === 'death') return;

    let damage = BATTLE_CONSTANTS.BASE_DAMAGE;
    if (defenderState === 'defense') {
      damage = damage * BATTLE_CONSTANTS.DEFENSE_REDUCTION;
    } else {
      // Only play gethit if not defending
      defender.setData('state', 'gethit');
      defender.play(`${defender.getData('char')}_gethit`);
      (defender.body as Phaser.Physics.Arcade.Body).setVelocityX(defender.flipX ? BATTLE_CONSTANTS.KNOCKBACK_FORCE : -BATTLE_CONSTANTS.KNOCKBACK_FORCE);
      
      // Visual feedback
      defender.setTint(0xffffff);
      this.time.delayedCall(50, () => defender.clearTint());
    }

    const newHp = Math.max(0, defender.getData('hp') - damage);
    defender.setData('hp', newHp);

    // Update Store & UI
    if (defender === this.player) {
      useGameStore.getState().setHp(newHp, useGameStore.getState().hpEnemy);
      this.playerHpBar.scaleX = 0.8 * (newHp / BATTLE_CONSTANTS.HP_MAX);
    } else {
      useGameStore.getState().setHp(useGameStore.getState().hpPlayer, newHp);
      this.enemyHpBar.scaleX = 0.8 * (newHp / BATTLE_CONSTANTS.HP_MAX);
    }

    if (newHp <= 0) {
      defender.setData('state', 'death');
      defender.play(`${defender.getData('char')}_death`);
      (defender.body as Phaser.Physics.Arcade.Body).setVelocityX(0);

      // Trigger Game Over
      this.time.delayedCall(1500, () => {
        useGameStore.getState().setWinner(defender === this.player ? 'ai' : 'player');
        useGameStore.getState().setGameState('gameover');
      });
    }
  }

  update(time: number, delta: number) {
    if (useGameStore.getState().gameState !== 'battle') return;

    const pState = this.player.getData('state');
    const eState = this.enemy.getData('state');
    const pChar = this.player.getData('char');
    const eChar = this.enemy.getData('char');

    // Reset velocities if grounded
    if (pState !== 'gethit') {
      (this.player.body as Phaser.Physics.Arcade.Body).setVelocityX(0);
    }
    if (eState !== 'gethit') {
      (this.enemy.body as Phaser.Physics.Arcade.Body).setVelocityX(0);
    }

    // Facing logic (always face each other)
    if (pState !== 'death' && eState !== 'death') {
      this.player.setFlipX(this.player.x > this.enemy.x);
      this.enemy.setFlipX(this.enemy.x < this.player.x);
    }

    // Player Input Handling
    if (pState === 'idle' || pState === 'walk' || pState === 'defense') {
      if (this.keys.K.isDown) {
        if (pState !== 'defense') {
          this.player.setData('state', 'defense');
          this.player.play(`${pChar}_defense`);
        }
      } else if (this.keys.J.isDown) {
        this.player.setData('state', 'hit');
        this.player.play(`${pChar}_hit`);
      } else if (this.keys.LEFT.isDown) {
        this.player.setData('state', 'walk');
        (this.player.body as Phaser.Physics.Arcade.Body).setVelocityX(-BATTLE_CONSTANTS.PLAYER_SPEED);
        if (this.player.anims.currentAnim?.key !== `${pChar}_walk`) {
          this.player.play(`${pChar}_walk`);
        }
      } else if (this.keys.RIGHT.isDown) {
        this.player.setData('state', 'walk');
        (this.player.body as Phaser.Physics.Arcade.Body).setVelocityX(BATTLE_CONSTANTS.PLAYER_SPEED);
        if (this.player.anims.currentAnim?.key !== `${pChar}_walk`) {
          this.player.play(`${pChar}_walk`);
        }
      } else {
        if (pState !== 'idle') {
          this.player.setData('state', 'idle');
          this.player.play(`${pChar}_idle`);
        }
      }
    }

    // AI Handling
    if (time > this.aiNextActionTime && eState !== 'death' && pState !== 'death') {
      this.processAi();
      this.aiNextActionTime = time + 100 + Math.random() * 300; // Fast reaction
    }
  }

  private processAi() {
    const eState = this.enemy.getData('state');
    if (eState === 'hit' || eState === 'gethit') return;

    const distance = Math.abs(this.player.x - this.enemy.x);
    const pState = this.player.getData('state');
    const eChar = this.enemy.getData('char');

    // Simple state machine
    if (distance < 180) {
      // Close range
      if (pState === 'hit' && Math.random() > 0.3) {
        // Block if player is attacking
        this.enemy.setData('state', 'defense');
        this.enemy.play(`${eChar}_defense`);
      } else {
        // Attack
        this.enemy.setData('state', 'hit');
        this.enemy.play(`${eChar}_hit`);
      }
    } else {
      // Far range - move closer
      this.enemy.setData('state', 'walk');
      this.enemy.play(`${eChar}_walk`);
      const dir = this.player.x > this.enemy.x ? 1 : -1;
      (this.enemy.body as Phaser.Physics.Arcade.Body).setVelocityX(BATTLE_CONSTANTS.PLAYER_SPEED * dir * 0.8);
    }
  }
}
