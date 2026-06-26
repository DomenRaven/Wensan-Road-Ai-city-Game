import { create } from 'zustand';

export type GameState = 'menu' | 'battle' | 'gameover';

interface StoreState {
  gameState: GameState;
  selectedChar: string | null;
  hpPlayer: number;
  hpEnemy: number;
  winner: 'player' | 'ai' | null;

  setGameState: (state: GameState) => void;
  setSelectedChar: (char: string) => void;
  setHp: (player: number, enemy: number) => void;
  setWinner: (winner: 'player' | 'ai') => void;
}

export const useGameStore = create<StoreState>((set) => ({
  gameState: 'menu',
  selectedChar: null,
  hpPlayer: 100,
  hpEnemy: 100,
  winner: null,

  setGameState: (state) => set({ gameState: state }),
  setSelectedChar: (char) => set({ selectedChar: char }),
  setHp: (hpPlayer, hpEnemy) => set({ hpPlayer, hpEnemy }),
  setWinner: (winner) => set({ winner }),
}));
