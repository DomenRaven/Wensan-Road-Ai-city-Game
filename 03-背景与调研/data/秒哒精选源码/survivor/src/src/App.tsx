import { useEffect, useRef } from 'react';
import Phaser from 'phaser';
import { createGame } from './game/main';
import { useGameStore } from './store/gameStore';
import { EventBus, GameEvents } from './game/EventBus';

// Components
import HUD from './components/HUD';
import StartScreen from './components/StartScreen';
import UpgradeModal from './components/UpgradeModal';
import GameOverScreen from './components/GameOverScreen';
import VictoryScreen from './components/VictoryScreen';

function App() {
  const initialized = useRef(false);
  const { status, setStatus, resetGame } = useGameStore();

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    const game = createGame();

    return () => {
      game.destroy(true);
      initialized.current = false;
    };
  }, []);

  useEffect(() => {
    // 注册全局游戏事件的监听，方便与 Zustand / React 通信
    const onGameOver = () => setStatus('gameover');
    const onVictory = () => setStatus('victory');
    const onRestart = () => {
      resetGame();
      EventBus.emit(GameEvents.START_GAME);
    };

    EventBus.on(GameEvents.GAME_OVER, onGameOver);
    EventBus.on(GameEvents.VICTORY, onVictory);
    EventBus.on(GameEvents.RESTART_GAME, onRestart);

    return () => {
      EventBus.off(GameEvents.GAME_OVER, onGameOver);
      EventBus.off(GameEvents.VICTORY, onVictory);
      EventBus.off(GameEvents.RESTART_GAME, onRestart);
    };
  }, [setStatus, resetGame]);

  return (
    <div className="relative w-screen h-screen overflow-hidden bg-[#FDFBF7] select-none">
      {/* Phaser Canvas Container */}
      <div id="game-container" className="w-full h-full" />

      {/* UI Layers overlay */}
      {status === 'menu' && <StartScreen />}
      {(status === 'playing' || status === 'boss_fight') && <HUD />}
      {status === 'upgrading' && <UpgradeModal />}
      {status === 'gameover' && <GameOverScreen />}
      {status === 'victory' && <VictoryScreen />}
    </div>
  );
}

export default App;
