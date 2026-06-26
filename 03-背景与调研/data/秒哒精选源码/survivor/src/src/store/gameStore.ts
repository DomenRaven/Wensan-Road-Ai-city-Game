import { create } from 'zustand';

export type UpgradeOption = 'attack_speed' | 'attack_damage' | 'move_speed' | 'multi_shot' | 'max_hp' | 'hp_regen';

interface GameState {
  status: 'menu' | 'playing' | 'paused' | 'upgrading' | 'boss_fight' | 'gameover' | 'victory';
  score: number;
  timeRemaining: number;
  bossFightTime: number; // boss战耗时
  level: number;
  exp: number;
  maxExp: number;
  
  // 玩家状态
  playerHp: number;
  playerMaxHp: number;
  attackSpeed: number; // 攻击间隔(ms)
  attackDamage: number;
  moveSpeed: number;
  multiShotCount: number; // 连发数
  hpRegen: number; // 每秒回血量
  
  // 供升级使用
  pendingUpgrades: UpgradeOption[];

  // Actions
  setStatus: (status: GameState['status']) => void;
  updateTime: (time: number) => void;
  incrementBossFightTime: () => void;
  addExp: (amount: number) => void;
  takeDamage: (amount: number) => void;
  healHp: (amount: number) => void;
  applyUpgrade: (type: UpgradeOption) => void;
  setPendingUpgrades: (upgrades: UpgradeOption[]) => void;
  resetGame: () => void;
}

const INITIAL_STATE = {
  status: 'menu' as const,
  score: 0,
  timeRemaining: 180,
  bossFightTime: 0,
  level: 1,
  exp: 0,
  maxExp: 100, // 初始所需经验
  
  playerHp: 100,
  playerMaxHp: 100,
  attackSpeed: 500, // 初始发射间隔：改为 500ms（原来是 1000ms，射速翻倍）
  attackDamage: 10,
  moveSpeed: 150,
  multiShotCount: 1,
  hpRegen: 0,
  
  pendingUpgrades: []
};

export const useGameStore = create<GameState>((set, get) => ({
  ...INITIAL_STATE,

  setStatus: (status) => set({ status }),
  updateTime: (timeRemaining) => set({ timeRemaining }),
  incrementBossFightTime: () => set((state) => ({ bossFightTime: state.bossFightTime + 1 })),
  
  addExp: (amount) => set((state) => {
    let newExp = state.exp + amount;
    let newLevel = state.level;
    let newMaxExp = state.maxExp;
    let triggerUpgrade = false;

    // 简化处理：一次最多升一级，多余经验保留
    if (newExp >= newMaxExp) {
      newExp -= newMaxExp;
      newLevel += 1;
      newMaxExp = Math.floor(newMaxExp * 1.5); // 经验曲线
      triggerUpgrade = true;
    }

    return { exp: newExp, level: newLevel, maxExp: newMaxExp, status: triggerUpgrade ? 'upgrading' : state.status };
  }),
  
  takeDamage: (amount) => set((state) => {
    const newHp = Math.max(0, state.playerHp - amount);
    if (newHp === 0 && (state.status === 'playing' || state.status === 'boss_fight')) {
      return { playerHp: newHp, status: 'gameover' };
    }
    return { playerHp: newHp };
  }),

  healHp: (amount) => set((state) => {
    const newHp = Math.min(state.playerMaxHp, state.playerHp + amount);
    return { playerHp: newHp };
  }),

  setPendingUpgrades: (pendingUpgrades) => set({ pendingUpgrades }),

  applyUpgrade: (type) => set((state) => {
    const updates: Partial<GameState> = { status: 'playing' };
    switch (type) {
      case 'attack_speed':
        updates.attackSpeed = Math.max(200, state.attackSpeed * 0.8); // 攻速提升，攻击间隔减少 20%
        break;
      case 'attack_damage':
        updates.attackDamage = state.attackDamage + 5; // 每次加 5 点固定伤害
        break;
      case 'move_speed':
        updates.moveSpeed = state.moveSpeed * 1.1; // 移速提升 10%
        break;
      case 'multi_shot':
        updates.multiShotCount = state.multiShotCount + 1; // 连发数 +1
        break;
      case 'max_hp':
        updates.playerMaxHp = state.playerMaxHp + 50; // 最大生命 +50
        updates.playerHp = state.playerHp + 50; // 当前生命同步增加
        break;
      case 'hp_regen':
        updates.hpRegen = state.hpRegen + 1; // 每秒回血 +1
        break;
    }
    return updates;
  }),
  
  resetGame: () => set({ ...INITIAL_STATE, status: 'playing' })
}));
