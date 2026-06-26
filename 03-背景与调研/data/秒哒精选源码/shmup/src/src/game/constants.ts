export const CONSTANTS = {
  GAME_WIDTH: 540,
  GAME_HEIGHT: 960,
  PLAYER_SPEED: 300,
  PLAYER_FIRE_RATE: 200, // 每多少毫秒发射一次
  BULLET_SPEED: 500,
  ENEMY_BULLET_SPEED: 300,
  ENEMY_BASE_SPEED: 100,
  ENEMY_SPAWN_RATE: 1500, // 初始生成频率
  POWERUP_DURATION: 15000,
  POWERUP_SPEED: 100,
};

export const ENEMY_TYPES = {
  NORMAL: {
    key: 'ships',
    frame: 9,
    score: 10,
    hp: 1,
    speed: 150,
    fireRate: 2000, // 会发射子弹
    scale: 1,
    dropRate: 0.3
  },
  FAST: {
    key: 'ships',
    frame: 5,
    score: 20,
    hp: 1,
    speed: 250,
    fireRate: 0, // 不发子弹
    scale: 1,
    dropRate: 0.4
  },
  HEAVY: {
    key: 'ships',
    frame: 1,
    score: 30,
    hp: 3,
    speed: 80,
    fireRate: 1500,
    scale: 1.2,
    dropRate: 0.5
  },
  BOSS: {
    key: 'ships',
    frame: 1,
    score: 200,
    hp: 100,
    speed: 50,
    fireRate: 800,
    scale: 2.5,
    dropRate: 1.0 // boss drops multiple
  }
};

export const POWERUP_TYPES = [
  { frame: 12, name: 'fireRate' }, // 红十字医疗箱作为火力强化
  { frame: 1, name: 'doubleShot' }, // 黄弹/能量条(2)作为双倍子弹
  { frame: 13, name: 'shield' } // 蓝盾牌作为护盾
];
