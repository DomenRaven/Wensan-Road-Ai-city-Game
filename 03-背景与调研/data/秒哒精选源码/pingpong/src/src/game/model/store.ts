import { create } from 'zustand';

interface GameState {
  playerScore: number;
  aiScore: number;
  status: 'menu' | 'playing' | 'gameover';
  winner: 'player' | 'ai' | null;
  addPlayerScore: () => void;
  addAiScore: () => void;
  resetGame: () => void;
  setStatus: (status: 'menu' | 'playing' | 'gameover') => void;
  setWinner: (winner: 'player' | 'ai' | null) => void;
}

export const useGameStore = create<GameState>((set) => ({
  playerScore: 0,
  aiScore: 0,
  status: 'menu',
  winner: null,
  addPlayerScore: () => set((state) => ({ playerScore: state.playerScore + 1 })),
  addAiScore: () => set((state) => ({ aiScore: state.aiScore + 1 })),
  resetGame: () => set({ playerScore: 0, aiScore: 0, winner: null }),
  setStatus: (status) => set({ status }),
  setWinner: (winner) => set({ winner }),
}));
