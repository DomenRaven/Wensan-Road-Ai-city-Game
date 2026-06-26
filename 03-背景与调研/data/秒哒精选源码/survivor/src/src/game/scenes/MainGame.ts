import { Scene, Physics, Math as PhaserMath } from 'phaser';
import { EventBus, GameEvents } from '../EventBus';
import { useGameStore } from '../../store/gameStore';
import { CONSTANTS } from '../constants';

export class MainGame extends Scene {
    private player!: Physics.Arcade.Sprite;
    private cursors!: Phaser.Types.Input.Keyboard.CursorKeys;
    private wasd!: any;
    
    private enemies!: Physics.Arcade.Group;
    private gems!: Physics.Arcade.Group;
    private bullets!: Physics.Arcade.Group;
    private bossBullets!: Physics.Arcade.Group;
    
    private boss: Physics.Arcade.Sprite | null = null;
    private bossHpText: Phaser.GameObjects.Text | null = null;
    private bossLastShotTime: number = 0;
    private bossLastSummonTime: number = 0;
    
    // 激光技能状态
    private bossLaserState: 'idle' | 'aiming' | 'firing' = 'idle';
    private bossLaserTimer: number = 0;
    private bossLaserLine: Phaser.GameObjects.Graphics | null = null;
    private bossLaserTarget: Phaser.Math.Vector2 | null = null;

    private isGameStarted: boolean = false;
    private isGameOver: boolean = false;
    private isPaused: boolean = false; // 用于升级时暂停

    private lastShotTime: number = 0;
    private lastRegenTime: number = 0;
    private nextSpawnTime: number = 0;
    
    private timerEvent!: Phaser.Time.TimerEvent;
    
    // 鼠标控制
    private mousePointer!: Phaser.Input.Pointer;
    private currentShootAngle: number = 0; // 记录当前射击朝向
    
    constructor() {
        super('MainGame');
    }

    create() {
        // 重置状态
        this.isGameStarted = false;
        this.isGameOver = false;
        this.isPaused = false;
        this.lastShotTime = 0;

        // 设置物理边界(假设世界很大)
        this.physics.world.setBounds(0, 0, 3000, 3000);
        
        // 画个地板网格背景方便看到移动
        this.add.grid(1500, 1500, 3000, 3000, 100, 100, 0xFDFBF7).setAltFillStyle(0xF5F0E6).setOutlineStyle();

        // 玩家创建
        this.player = this.physics.add.sprite(1500, 1500, 'player_idle');
        this.player.setCollideWorldBounds(true);
        this.player.setDepth(10);
        (this.player.body as Physics.Arcade.Body).setSize(20, 20);

        // 镜头跟随
        this.cameras.main.startFollow(this.player);
        this.cameras.main.setBounds(0, 0, 3000, 3000);

        // 输入
        this.cursors = this.input.keyboard!.createCursorKeys();
        this.wasd = this.input.keyboard!.addKeys('W,A,S,D');
        
        // 鼠标输入
        this.mousePointer = this.input.activePointer;
        this.input.on('pointerdown', this.handleMouseClick, this);

        // 群组
        this.enemies = this.physics.add.group();
        this.gems = this.physics.add.group();
        this.bullets = this.physics.add.group();

        // 碰撞
        this.physics.add.overlap(this.player, this.enemies, this.handlePlayerEnemyCollision, undefined, this);
        this.physics.add.overlap(this.player, this.gems, this.handlePlayerGemCollision, undefined, this);
        this.physics.add.overlap(this.bullets, this.enemies, this.handleBulletEnemyCollision, undefined, this);

        // 监听 React 的事件
        EventBus.on(GameEvents.START_GAME, this.startGame, this);
        EventBus.on(GameEvents.RESTART_GAME, this.restartGame, this);
        
        // 升级逻辑
        this.events.on('pause', () => { this.isPaused = true; });
        this.events.on('resume', () => { 
            this.isPaused = false; 
            
            // 升级恢复时，检查是否处于boss战，是的话触发boss回血机制
            if (useGameStore.getState().status === 'boss_fight' && this.boss && this.boss.active) {
                this.handleBossHealOnUpgrade();
            }
        });
    }

    private handleBossHealOnUpgrade() {
        if (!this.boss || !this.boss.active) return;
        
        // 1. Boss 回满血
        this.boss.setData('hp', CONSTANTS.BOSS_HP);
        
        // 2. 改变 Boss 颜色 (随机颜色)
        const randomColor = Phaser.Display.Color.RandomRGB().color;
        this.boss.setTint(randomColor);
        
        // 3. 屏幕提示
        const text = this.add.text(this.cameras.main.centerX, this.cameras.main.centerY - 100, 'boss的力量回复了！', {
            fontSize: '32px',
            color: '#ff0000',
            fontStyle: 'bold',
            stroke: '#ffffff',
            strokeThickness: 6
        }).setOrigin(0.5).setScrollFactor(0); // 固定在屏幕中间
        
        text.setDepth(100);
        
        // 提示文字上升并渐隐
        this.tweens.add({
            targets: text,
            y: text.y - 50,
            alpha: 0,
            duration: 2000,
            ease: 'Power2',
            onComplete: () => {
                text.destroy();
            }
        });
    }

    private startGame() {
        this.isGameStarted = true;
        this.isGameOver = false;
        this.isPaused = false;
        
        // 同步 store
        useGameStore.getState().resetGame();
        
        // 每秒发一次倒计时更新
        this.timerEvent = this.time.addEvent({
            delay: 1000,
            callback: this.tickTimer,
            callbackScope: this,
            loop: true
        });
    }

    private restartGame() {
        this.scene.restart();
    }

    private tickTimer() {
        if (this.isGameOver || this.isPaused) return;

        const store = useGameStore.getState();
        if (store.status === 'boss_fight') {
            store.incrementBossFightTime();
            return; 
        }
        
        const newTime = store.timeRemaining - 1;
        if (newTime <= 0) {
            store.updateTime(0);
            useGameStore.getState().setStatus('boss_fight');
            this.spawnBoss();
        } else {
            store.updateTime(newTime);
        }
    }

    private victory() {
        this.isGameOver = true;
        this.isGameStarted = false;
        if (this.timerEvent) this.timerEvent.remove(false);
        EventBus.emit(GameEvents.VICTORY);
    }

    private gameOver() {
        this.isGameOver = true;
        this.isGameStarted = false;
        this.player.setTint(0xff0000);
        if (this.timerEvent) this.timerEvent.remove(false);
        // EventBus 已经由 store 管理触发，不需要这里再发，但为了稳妥可以交给 store 处理或这里触发。
        // 这里只是物理表现。store.takeDamage 里已经有判断 gameover 的逻辑，但为了防止没触发，补一个：
        const store = useGameStore.getState();
        if (store.status !== 'gameover') {
            store.setStatus('gameover');
        }
    }

    update(time: number, delta: number) {
        // 同步 React state: 如果状态在升级中，我们就暂停物理与逻辑
        const store = useGameStore.getState();
        if (store.status === 'upgrading') {
            if (!this.isPaused) {
                this.physics.pause();
                this.isPaused = true;
            }
            return;
        } else if (store.status === 'playing' && this.isPaused) {
            this.physics.resume();
            this.isPaused = false;
        }

        if (!this.isGameStarted || this.isGameOver) {
            (this.player.body as Physics.Arcade.Body).setVelocity(0);
            return;
        }

        // --- 1. 玩家移动 ---
        const moveSpeed = store.moveSpeed;
        let vx = 0;
        let vy = 0;

        if (this.cursors.left.isDown || this.wasd.A.isDown) vx = -1;
        if (this.cursors.right.isDown || this.wasd.D.isDown) vx = 1;
        if (this.cursors.up.isDown || this.wasd.W.isDown) vy = -1;
        if (this.cursors.down.isDown || this.wasd.S.isDown) vy = 1;

        const body = this.player.body as Physics.Arcade.Body;
        if (vx !== 0 || vy !== 0) {
            const mag = Math.sqrt(vx * vx + vy * vy);
            body.setVelocity((vx / mag) * moveSpeed, (vy / mag) * moveSpeed);
            this.player.play('player_walk', true);
        } else {
            body.setVelocity(0);
            this.player.setTexture('player_idle');
        }
        
        // --- 1.5 根据当前设定的方向翻转角色 ---
        if (Math.abs(this.currentShootAngle) > Math.PI / 2) {
            this.player.setFlipX(true);
        } else {
            this.player.setFlipX(false);
        }

        // --- 2. 敌人生成 ---
        if (time > this.nextSpawnTime) {
            this.spawnEnemy();
            // 随着时间推移，加快生成速度
            const factor = Math.max(0.2, store.timeRemaining / CONSTANTS.GAME_DURATION);
            this.nextSpawnTime = time + CONSTANTS.ENEMY_SPAWN_RATE_BASE * factor;
        }

        // --- 3. 敌人 AI 向玩家移动 ---
        this.enemies.getChildren().forEach((child) => {
            const enemy = child as Physics.Arcade.Sprite;
            const ex = enemy.x;
            const ey = enemy.y;
            const angle = PhaserMath.Angle.Between(ex, ey, this.player.x, this.player.y);
            const speed = (enemy.getData('speed') || 50);
            (enemy.body as Physics.Arcade.Body).setVelocity(Math.cos(angle) * speed, Math.sin(angle) * speed);
            
            if (Math.cos(angle) < 0) enemy.setFlipX(true);
            else enemy.setFlipX(false);
        });

        // --- 4. 自动发射子弹机制 ---
        if (time > this.lastShotTime + store.attackSpeed) {
            this.fireBullets();
            this.lastShotTime = time;
        }

        // --- 4.5 自动回血机制 ---
        if (store.hpRegen > 0 && time > this.lastRegenTime + 1000) {
            useGameStore.getState().healHp(store.hpRegen);
            this.lastRegenTime = time;
        }

        // --- 5. 检查死亡 ---
        if (store.playerHp <= 0 && !this.isGameOver) {
            this.gameOver();
        }

        this.updateBossHpText();
    }

    private spawnEnemy() {
        // 环形生成
        const angle = Math.random() * Math.PI * 2;
        const radius = 600; // 屏幕外围
        const px = this.player.x + Math.cos(angle) * radius;
        const py = this.player.y + Math.sin(angle) * radius;

        // 随机类型
        const types = ['1', '3', '6'];
        const type = Phaser.Utils.Array.GetRandom(types);

        const enemy = this.enemies.create(px, py, `monster_${type}_1`) as Physics.Arcade.Sprite;
        enemy.play(`enemy_walk_${type}`);
        enemy.setDepth(5);
        (enemy.body as Physics.Arcade.Body).setSize(24, 24);
        
        // 初始化敌人属性
        const baseHp = 10; // 敌人初始血量减半 (原本是 20)
        const levelFactor = 1 + (CONSTANTS.GAME_DURATION - useGameStore.getState().timeRemaining) / 60; // 每60秒强化一倍
        enemy.setData('hp', baseHp * levelFactor);
        enemy.setData('speed', 50 + Math.random() * 30);
    }

    private handleBossLaser(time: number) {
        if (!this.boss || !this.boss.active) return;
        
        // 确保 graphics 存在
        if (!this.bossLaserLine) {
            this.bossLaserLine = this.add.graphics();
            this.bossLaserLine.setDepth(15);
        }

        // 状态机
        if (this.bossLaserState === 'idle') {
            // 每3秒触发一次瞄准
            if (time > this.bossLaserTimer + 3000) {
                this.bossLaserState = 'aiming';
                this.bossLaserTimer = time;
                // 锁定当前玩家位置
                this.bossLaserTarget = new Phaser.Math.Vector2(this.player.x, this.player.y);
            }
        } 
        else if (this.bossLaserState === 'aiming') {
            // 瞄准阶段持续1秒，绘制红色警告线
            this.bossLaserLine.clear();
            if (this.bossLaserTarget) {
                this.bossLaserLine.lineStyle(2, 0xff0000, 0.5); // 半透明红线
                this.bossLaserLine.strokeLineShape(new Phaser.Geom.Line(this.boss.x, this.boss.y, this.bossLaserTarget.x, this.bossLaserTarget.y));
            }

            if (time > this.bossLaserTimer + 1000) {
                this.bossLaserState = 'firing';
                this.bossLaserTimer = time;
            }
        } 
        else if (this.bossLaserState === 'firing') {
            // 发射激光持续0.5秒，绘制粗红线并进行伤害判定
            this.bossLaserLine.clear();
            if (this.bossLaserTarget) {
                this.bossLaserLine.lineStyle(15, 0xff0000, 1); // 不透明粗红线
                const laserLine = new Phaser.Geom.Line(this.boss.x, this.boss.y, this.bossLaserTarget.x, this.bossLaserTarget.y);
                this.bossLaserLine.strokeLineShape(laserLine);

                // 激光伤害判定（射线与圆的交点判断，简单起见计算点到直线的距离）
                const playerCircle = new Phaser.Geom.Circle(this.player.x, this.player.y, 20);
                // Phaser提供简单的相交检测
                if (Phaser.Geom.Intersects.LineToCircle(laserLine, playerCircle)) {
                    // 为了防止0.5秒内每帧扣血，可以记录激光击中状态或给无敌帧
                    // 我们依赖玩家受击自带的无敌时间（因为有扣血后的tint和短暂不可见，但没有真正免疫）
                    // 稍作修改：依靠激光本身的 tick，我们只在 firing 开始的第一帧造成伤害，或者依赖系统的 takeDamage 频控。
                    // 简便起见，每次检测到就触发 takeDamage（如果不做频控会秒杀玩家，所以我们用 player 身上一个简单的标识）
                    if (!this.player.getData('laserHit')) {
                        useGameStore.getState().takeDamage(30); // 激光伤害更高
                        this.player.setData('laserHit', true);
                        this.player.setTint(0xff0000);
                        this.time.delayedCall(500, () => { // 无敌或受击冷却
                            if (this.player && this.player.active) {
                                this.player.clearTint();
                                this.player.setData('laserHit', false);
                            }
                        });
                    }
                }
            }

            if (time > this.bossLaserTimer + 500) {
                // 结束
                this.bossLaserLine.clear();
                this.bossLaserState = 'idle';
                this.bossLaserTimer = time;
                if (this.player) this.player.setData('laserHit', false);
            }
        }
    }

    private spawnBoss() {
        // 清理所有小怪
        this.enemies.getChildren().forEach((child) => child.destroy());
        this.enemies.clear(true, true);

        // 在玩家上方一段距离生成 Boss
        this.boss = this.physics.add.sprite(this.player.x, this.player.y - 300, 'monster_1');
        this.boss.setScale(3); // 体积放大
        this.boss.setTint(0xffaaaa); // 变点色
        this.boss.setData('hp', CONSTANTS.BOSS_HP);
        this.boss.setData('isBoss', true);
        this.boss.play('monster_1_walk');

        const body = this.boss.body as Physics.Arcade.Body;
        body.setSize(20, 20);

        // 加入 enemies 组以便复用已有的受击判定，但我们将额外处理 boss 逻辑
        this.enemies.add(this.boss);

        // 创建血条文本
        this.bossHpText = this.add.text(this.boss.x, this.boss.y - 60, `BOSS HP: ${CONSTANTS.BOSS_HP}`, {
            fontSize: '16px',
            color: '#ff0000',
            fontStyle: 'bold'
        }).setOrigin(0.5);

        // Boss登场特效
        this.cameras.main.shake(500, 0.02); // 震屏 0.5s，强度 0.02
        this.createParticles(this.boss.x, this.boss.y, 0xffaaaa);
    }

    private createParticles(x: number, y: number, color: number) {
        // 简易的自爆/登场粒子特效，使用已经 preload 好的 fx_hit 作为贴图
        const emitter = this.add.particles(x, y, 'fx_hit', {
            speed: { min: 100, max: 300 },
            angle: { min: 0, max: 360 },
            scale: { start: 1, end: 0 },
            tint: color,
            blendMode: 'ADD',
            lifespan: 800,
            quantity: 30
        });
        emitter.setDepth(20);
        // 自动销毁
        this.time.delayedCall(1000, () => {
            emitter.destroy();
        });
    }

    private fireBossBullet() {
        if (!this.boss || !this.boss.active) return;
        const speed = 200;
        const angle = PhaserMath.Angle.Between(this.boss.x, this.boss.y, this.player.x, this.player.y);
        
        const bullet = this.bossBullets.create(this.boss.x, this.boss.y, 'fx_hit') as Physics.Arcade.Sprite;
        bullet.setScale(0.8);
        bullet.setTint(0x000000); // 黑色子弹以区分
        bullet.setData('damage', 10);
        
        const body = bullet.body as Physics.Arcade.Body;
        body.setSize(10, 10);
        body.setVelocity(Math.cos(angle) * speed, Math.sin(angle) * speed);

        this.time.delayedCall(3000, () => {
            if (bullet && bullet.active) bullet.destroy();
        });
    }

    private updateBossHpText() {
        if (this.boss && this.boss.active && this.bossHpText) {
            this.bossHpText.setPosition(this.boss.x, this.boss.y - 60);
            this.bossHpText.setText(`BOSS HP: ${this.boss.getData('hp')}`);
        }
    }
    private handleMouseClick() {
        if (!this.isGameStarted || this.isGameOver || this.isPaused) return;

        // 获取鼠标世界坐标，更新当前射击朝向
        const worldPoint = this.cameras.main.getWorldPoint(this.mousePointer.x, this.mousePointer.y);
        this.currentShootAngle = PhaserMath.Angle.Between(this.player.x, this.player.y, worldPoint.x, worldPoint.y);
    }

    private fireBullets() {
        const store = useGameStore.getState();
        const count = store.multiShotCount;
        const damage = store.attackDamage;
        const baseAngle = this.currentShootAngle;
        const speed = 400; // 子弹速度

        // 连发机制：如果是多发，在基础角度两侧展开
        const spreadAngle = Math.PI / 12; // 每发之间的角度间隔 (15度)
        const startAngle = baseAngle - ((count - 1) / 2) * spreadAngle;

        for (let i = 0; i < count; i++) {
            const angle = startAngle + i * spreadAngle;
            
            // 使用 fx_hit 作为子弹图，缩放一下
            const bullet = this.bullets.create(this.player.x, this.player.y, 'fx_hit') as Physics.Arcade.Sprite;
            bullet.setScale(0.8); // 稍微放大显示
            bullet.setData('damage', damage);
            bullet.setDepth(6);
            
            const body = bullet.body as Physics.Arcade.Body;
            body.setSize(24, 24); // 增大碰撞判定范围
            body.setVelocity(Math.cos(angle) * speed, Math.sin(angle) * speed);

            // 子弹存活时间 (飞行一段距离后销毁)
            this.time.delayedCall(1500, () => {
                if (bullet && bullet.active) bullet.destroy();
            });
        }
    }

    private handlePlayerBossBulletCollision(p: any, b: any) {
        if (this.isGameOver || this.isPaused) return;

        const bullet = b as Physics.Arcade.Sprite;
        const damage = bullet.getData('damage');
        bullet.destroy();

        useGameStore.getState().takeDamage(damage);

        this.player.setTint(0xff0000);
        this.time.delayedCall(100, () => {
            if (this.player && this.player.active && !this.isGameOver) this.player.clearTint();
        });
    }

    private handleBulletEnemyCollision(b: any, e: any) {
        if (this.isGameOver || this.isPaused) return;

        const bullet = b as Physics.Arcade.Sprite;
        const enemy = e as Physics.Arcade.Sprite;

        const damage = bullet.getData('damage');
        bullet.destroy(); // 击中销毁

        const hp = enemy.getData('hp') - damage;
        if (hp <= 0) {
            if (enemy.getData('isBoss')) {
                // Boss 死亡
                if (this.bossHpText) this.bossHpText.destroy();
                this.cameras.main.shake(800, 0.03); // 死亡剧烈震屏
                this.createParticles(enemy.x, enemy.y, 0xff0000); // 死亡粒子
                enemy.destroy();
                this.time.delayedCall(1000, () => {
                    this.victory();
                });
            } else {
                this.dropGem(enemy.x, enemy.y);
                enemy.destroy();
            }
        } else {
            enemy.setData('hp', hp);
            enemy.setTint(0xff5c77);
            this.time.delayedCall(100, () => {
                if (enemy && enemy.active) enemy.clearTint();
            });
        }
    }

    private dropGem(x: number, y: number) {
        const gem = this.gems.create(x, y, 'item_exp_gem') as Physics.Arcade.Sprite;
        gem.setScale(0.8);
        gem.setDepth(4);
    }

    private handlePlayerEnemyCollision(p: any, e: any) {
        if (this.isGameOver || this.isPaused) return;

        const enemy = e as Physics.Arcade.Sprite;
        
        // 为了防止连续扣血，给敌人加个 cooldown
        const lastHit = enemy.getData('lastHitPlayerTime') || 0;
        const now = this.time.now;
        if (now - lastHit > 500) {
            enemy.setData('lastHitPlayerTime', now);
            useGameStore.getState().takeDamage(5); // 固定碰一下掉 5 点血
            
            // 玩家闪红
            this.player.setTint(0xff5c77);
            this.time.delayedCall(100, () => {
                if (this.player && this.player.active && !this.isGameOver) this.player.clearTint();
            });
        }
    }

    private handlePlayerGemCollision(p: any, g: any) {
        if (this.isGameOver || this.isPaused) return;

        const gem = g as Physics.Arcade.Sprite;
        gem.destroy(); // 销毁宝石
        
        // 增加经验
        useGameStore.getState().addExp(CONSTANTS.EXP_GEM_BASE_VALUE);
    }
}
