## 街机飞机射击游戏 — Phaser.js 素材使用说明

### 素材包路径
`assets/pixel-plane-shmup/`

---

### 1. preload() 加载代码

```javascript
const BASE = 'assets/pixel-plane-shmup';
// 飞船 spritesheet（32x32，间距1px，4列×6行，共24帧）
this.load.spritesheet('ships', BASE + '/Tilemap/ships_packed (128x192)[frames=1].png', {
  frameWidth: 32, frameHeight: 32, spacing: 1
});
// 场景/子弹/爆炸 spritesheet（16x16，间距1px，12列×10行，共120帧）
this.load.spritesheet('tiles', BASE + '/Tilemap/tiles_packed (192x160)[frames=1].png', {
  frameWidth: 16, frameHeight: 16, spacing: 1
});
// 背景大图
this.load.image('background', BASE + '/Tilemap/background.png');
```

---

### 2. 游戏角色 → Frame 对照表

| 游戏角色 | key | frame | 说明 |
|---------|-----|-------|------|
| 玩家飞机 | `ships` | **4** | 蓝色战斗机（细长机身） |
| 普通敌机 | `ships` | **9** | 红色小型飞船，得10分 |
| 快速敌机 | `ships` | **5** | 红色战斗机，得20分 |
| 强化敌机 | `ships` | **1** | 红色重型飞船，得30分 |
| 玩家子弹 | `tiles` | **0** | 黄弹/能量条(1)，向上飞 |
| 敌机子弹 | `tiles` | **2** | 黄弹/能量条(3)，向下飞 |
| 爆炸动画 | `tiles` | **4~7** | 橙色爆炸/星形，4帧动画 |

---

### 3. create() 关键代码片段

```javascript
// 爆炸动画注册（在 create() 中执行一次）
this.anims.create({
  key: 'explode',
  frames: this.anims.generateFrameNumbers('tiles', { frames: [4, 5, 6, 7] }),
  frameRate: 12,
  repeat: 0
});

// 玩家飞机
const player = this.physics.add.sprite(centerX, gameHeight - 80, 'ships', 4);
player.setCollideWorldBounds(true);

// 普通敌机（生成时）
const enemy = this.physics.add.sprite(x, -32, 'ships', 9);
enemy.setAngle(180); // ⚠️ 敌机图片朝上，需旋转180°使其朝下

// 快速敌机
const fastEnemy = this.physics.add.sprite(x, -32, 'ships', 5);
fastEnemy.setAngle(180);

// 强化敌机
const heavyEnemy = this.physics.add.sprite(x, -32, 'ships', 1);
heavyEnemy.setAngle(180);

// 玩家子弹
const bullet = this.physics.add.sprite(player.x, player.y - 20, 'tiles', 0);
bullet.setVelocityY(-400);

// 敌机子弹
const eBullet = this.physics.add.sprite(enemy.x, enemy.y + 20, 'tiles', 2);
eBullet.setVelocityY(250);

// 爆炸效果（敌机被击毁时）
const boom = this.add.sprite(x, y, 'tiles', 4);
boom.play('explode');
boom.on('animationcomplete', () => boom.destroy());

// 滚动背景（tileSprite）
const bg = this.add.tileSprite(0, 0, gameWidth, gameHeight, 'background').setOrigin(0, 0);
```

### 4. update() 背景滚动

```javascript
bg.tilePositionY -= 2; // 每帧向下滚动2px，模拟飞行感
```

### 5. 碰撞检测

```javascript
// 玩家子弹 vs 敌机
this.physics.add.overlap(playerBullets, enemies, (bullet, enemy) => {
  bullet.destroy();
  // 播放爆炸、更新分数
});
// 敌机子弹 vs 玩家
this.physics.add.overlap(enemyBullets, player, () => {
  this.scene.start('GameOverScene');
});
// 玩家 vs 敌机（碰撞即死）
this.physics.add.overlap(player, enemies, () => {
  this.scene.start('GameOverScene');
});
```

### 6. ⚠️ 重要注意事项

- **敌机旋转**：所有飞船图片默认朝上，敌机必须调用 `enemy.setAngle(180)` 或 `enemy.setFlipY(true)` 使其朝下
- **frame 索引公式**：`index = row * COLUMNS + col`（0起始）
  - ships: COLUMNS=4；tiles: COLUMNS=12
- **spacing**：两个 spritesheet 均有 1px 间距，加载时必须传 `spacing: 1`
- **背景滚动**：需使用 `this.add.tileSprite(...)` 而非 `this.add.image(...)` 才能实现 `tilePositionY` 滚动
