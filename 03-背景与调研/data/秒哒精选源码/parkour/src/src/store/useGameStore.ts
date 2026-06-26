import { create } from 'zustand';

type GameStatus = 'menu' | 'playing' | 'gameover';

interface GameState {
  status: GameStatus;
  score: number;
  timeLeft: number;
  setStatus: (status: GameStatus) => void;
  setScore: (score: number) => void;
  addScore: (delta: number) => void;
  setTimeLeft: (time: number) => void;
  resetGame: () => void;
}

export const useGameStore = create<GameState>((set) => ({
  status: 'menu',
  score: 0,
  timeLeft: 60,
  setStatus: (status) => set({ status }),
  setScore: (score) => set({ score }),
  addScore: (delta) => set((state) => ({ score: state.score + delta })),
  setTimeLeft: (timeLeft) => set({ timeLeft }),
  resetGame: () => set({ status: 'playing', score: 0, timeLeft: 60 }),
}));
