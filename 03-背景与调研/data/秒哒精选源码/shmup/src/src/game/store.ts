import { create } from 'zustand';

interface GameState {
  score: number;
  isGameOver: boolean;
  addScore: (points: number) => void;
  resetGame: () => void;
  setGameOver: (over: boolean) => void;
}

export const useGameStore = create<GameState>((set) => ({
  score: 0,
  isGameOver: false,
  addScore: (points) => set((state) => ({ score: state.score + points })),
  resetGame: () => set({ score: 0, isGameOver: false }),
  setGameOver: (over) => set({ isGameOver: over }),
}));
