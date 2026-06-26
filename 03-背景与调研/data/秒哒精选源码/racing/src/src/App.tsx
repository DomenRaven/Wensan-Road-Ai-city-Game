import { useEffect, useRef } from 'react';
import Phaser from 'phaser';
import { GAME_CONFIG } from './game/main';
import { useGameStore } from './store/gameStore';
import { StartScreen } from './components/StartScreen';
import { GameOverScreen } from './components/GameOverScreen';
import { HUD } from './components/HUD';

function App() {
  const initialized = useRef(false);
  const gameState = useGameStore(state => state.gameState);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    const game = new Phaser.Game(GAME_CONFIG);
    
    return () => {
      game.destroy(true);
      initialized.current = false;
    };
  }, []);

  return (
    <div className="relative w-screen h-screen overflow-hidden bg-[#87CEEB] flex justify-center items-center font-mono font-bold select-none">
      <div className="relative w-[540px] h-[960px] max-w-full max-h-full">
        {/* Phaser Canvas Container */}
        <div id="game-container" className="absolute inset-0 w-full h-full" />
        
        {/* React UI Overlays */}
        {gameState === 'START' && <StartScreen />}
        {gameState === 'PLAYING' && <HUD />}
        {gameState === 'GAMEOVER' && <GameOverScreen />}
      </div>
    </div>
  );
}

export default App;
