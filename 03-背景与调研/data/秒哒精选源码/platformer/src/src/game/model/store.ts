import { create } from 'zustand';

interface GameState {
  score: number;
  lives: number;
  level: number;
  coins: number;
  gameStatus: 'start' | 'playing' | 'gameover' | 'victory';
  addScore: (points: number) => void;
  addCoin: () => void;
  loseLife: () => void;
  setStatus: (status: 'start' | 'playing' | 'gameover' | 'victory') => void;
  nextLevel: () => void;
  resetGame: () => void;
}

export const useGameStore = create<GameState>((set) => ({
  score: 0,
  lives: 3,
  level: 1,
  coins: 0,
  gameStatus: 'start',
  addScore: (points) => set((state) => ({ score: state.score + points })),
  addCoin: () => set((state) => ({ coins: state.coins + 1, score: state.score + 10 })),
  loseLife: () => set((state) => ({ lives: Math.max(0, state.lives - 1) })),
  setStatus: (status) => set({ gameStatus: status }),
  nextLevel: () => set((state) => ({ level: state.level + 1 })),
  resetGame: () => set({ score: 0, lives: 3, level: 1, coins: 0, gameStatus: 'playing' }),
}));
