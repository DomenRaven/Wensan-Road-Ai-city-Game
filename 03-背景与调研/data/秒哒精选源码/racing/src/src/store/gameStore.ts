import { create } from 'zustand';

type GameState = 'START' | 'PLAYING' | 'GAMEOVER';

interface GameStore {
  gameState: GameState;
  score: number; // Represents laps
  timeLeft: number;
  setGameState: (state: GameState) => void;
  setScore: (score: number) => void;
  addScore: (delta: number) => void;
  setTimeLeft: (time: number) => void;
  resetGame: () => void;
}

export const useGameStore = create<GameStore>((set) => ({
  gameState: 'START',
  score: 0,
  timeLeft: 90,
  setGameState: (state) => set({ gameState: state }),
  setScore: (score) => set({ score }),
  addScore: (delta) => set((state) => ({ score: state.score + delta })),
  setTimeLeft: (time) => set({ timeLeft: time }),
  resetGame: () => set({ score: 0, timeLeft: 90, gameState: 'PLAYING' }),
}));
