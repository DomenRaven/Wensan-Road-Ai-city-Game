import { useEffect, useRef, useState } from 'react';
import Phaser from 'phaser';
import { gameConfig } from './game/main';
import { EventBus } from './game/EventBus';
import { useGameStore } from './game/store';

// 游戏结束和HUD界面等之后写
export default function App() {
  const initialized = useRef(false);
  const [sceneKey, setSceneKey] = useState('Boot');
  const score = useGameStore((state) => state.score);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    
    const game = new Phaser.Game(gameConfig);
    
    EventBus.on('scene-changed', ({ key }: { key: string }) => {
      setSceneKey(key);
    });

    return () => {
      game.destroy(true);
      initialized.current = false;
    };
  }, []);

  return (
    <div className="w-screen h-screen overflow-hidden bg-[#0a0a0c] text-[#39ff14] font-mono select-none">
      <div id="game-container" className="w-full h-full absolute inset-0" />
      
      {/* 极简 HUD 信息层 */}
      {sceneKey === 'MainGame' && (
        <div className="absolute top-4 left-4 z-10 text-2xl drop-shadow-md">
          SCORE: {score.toString().padStart(6, '0')}
        </div>
      )}

      {/* 弹窗层：开始界面 */}
      {sceneKey === 'Boot' && (
        <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-black/80">
          <h1 className="text-4xl mb-12 text-[#39ff14] text-center px-4 leading-relaxed font-bold tracking-widest" style={{ textShadow: '2px 2px 0px #ff003c' }}>
            ARCADE<br/>SHOOTER
          </h1>
          <button 
            className="border-2 border-[#39ff14] px-8 py-4 text-xl uppercase tracking-widest bg-transparent hover:bg-[#39ff14] hover:text-[#0a0a0c] transition-colors duration-0 active:scale-95"
            onClick={() => {
              EventBus.emit('start-game');
            }}
          >
            INSERT COIN / START
          </button>
        </div>
      )}

      {/* 弹窗层：结束界面 */}
      {sceneKey === 'GameOver' && (
        <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-black/80">
          <h1 className="text-5xl mb-4 text-[#ff003c] font-bold tracking-widest uppercase">
            GAME OVER
          </h1>
          <div className="text-2xl mb-12 text-[#39ff14]">
            FINAL SCORE: {score.toString().padStart(6, '0')}
          </div>
          <button 
            className="border-2 border-[#39ff14] px-8 py-4 text-xl uppercase tracking-widest bg-transparent hover:bg-[#39ff14] hover:text-[#0a0a0c] transition-colors duration-0 active:scale-95"
            onClick={() => {
              EventBus.emit('restart-game');
            }}
          >
            TRY AGAIN
          </button>
        </div>
      )}
    </div>
  );
}
