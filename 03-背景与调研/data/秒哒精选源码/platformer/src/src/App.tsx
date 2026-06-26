import React, { useEffect, useRef } from 'react';
import Phaser from 'phaser';
import { GAME_SCENES } from './game/scenes';
import { CONSTANTS } from './game/constants';
import { useGameStore } from './game/model/store';
import { EventBus } from './game/EventBus';

export default function App() {
  const initialized = useRef(false);
  const { gameStatus, score, lives, level, coins, setStatus, resetGame } = useGameStore();

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    const game = new Phaser.Game({
      type: Phaser.AUTO,
      parent: 'game-container',
      width: CONSTANTS.GAME_WIDTH,
      height: CONSTANTS.GAME_HEIGHT,
      scene: GAME_SCENES,
      physics: {
        default: 'arcade',
        arcade: {
          gravity: { x: 0, y: CONSTANTS.GRAVITY },
          debug: false,
        },
      },
      scale: {
        mode: Phaser.Scale.FIT,
        autoCenter: Phaser.Scale.CENTER_BOTH,
      },
      backgroundColor: '#5C94FC', // 天蓝色
      pixelArt: true,
    });

    return () => {
      game.destroy(true);
      initialized.current = false;
    };
  }, []);

  const handleStart = () => {
    resetGame();
    // 通知Phaser场景启动
    EventBus.emit('scene-changed', { key: 'MainGame' });
    // TODO: 目前不能直接调用 scene.start，因为React没有scene实例，我们使用EventBus，或者在Boot中延迟启动
    // 在这里我们采取简单做法，由于Boot已经加载完，我们可以让MainGame通过 EventBus 监听
  };

  const handleRestart = () => {
    resetGame();
    EventBus.emit('restart-game');
  };

  const handleNextLevel = () => {
    setStatus('playing');
    EventBus.emit('restart-game');
  };

  // UI 样式
  const uiOverlayStyle = "absolute inset-0 z-10 flex flex-col items-center justify-center pointer-events-none";
  const panelStyle = "bg-black border-4 border-white p-8 pointer-events-auto shadow-lg flex flex-col items-center gap-6";
  const btnStyle = "bg-[#E52521] border-4 border-white px-6 py-3 text-white text-xl font-bold uppercase cursor-pointer hover:translate-y-[2px] transition-transform active:bg-red-700 font-mono tracking-widest";
  const textStyle = "text-white font-mono uppercase tracking-wider";

  return (
    <div className="relative w-screen h-screen overflow-hidden bg-black font-mono">
      <div id="game-container" className="absolute inset-0 w-full h-full z-0" />

      {/* HUD (只在 playing 状态显示) */}
      {gameStatus === 'playing' && (
        <div className="absolute top-0 left-0 w-full p-4 flex justify-between px-10 pointer-events-none z-10">
          <div className="flex flex-col items-start">
            <span className="text-white text-xl font-bold drop-shadow-md">SCORE</span>
            <span className="text-white text-2xl drop-shadow-md">{score.toString().padStart(6, '0')}</span>
          </div>
          <div className="flex flex-col items-center">
            <span className="text-white text-xl font-bold drop-shadow-md">COINS</span>
            <span className="text-[#FBD000] text-2xl drop-shadow-md">x {coins.toString().padStart(2, '0')}</span>
          </div>
          <div className="flex flex-col items-center">
            <span className="text-white text-xl font-bold drop-shadow-md">LEVEL</span>
            <span className="text-white text-2xl drop-shadow-md">{level}</span>
          </div>
          <div className="flex flex-col items-end">
            <span className="text-white text-xl font-bold drop-shadow-md">LIVES</span>
            <span className="text-[#E52521] text-2xl drop-shadow-md">{'♥'.repeat(lives)}</span>
          </div>
        </div>
      )}

      {/* Start Screen */}
      {gameStatus === 'start' && (
        <div className={uiOverlayStyle}>
          <div className="flex flex-col items-center pointer-events-auto mb-16">
            <h1 className="text-6xl font-bold text-white tracking-widest drop-shadow-[4px_4px_0_#E52521] mb-20 animate-pulse">
              PIXEL MARIO
            </h1>
            <button className={btnStyle} onClick={handleStart}>
              START GAME
            </button>
            <div className="mt-8 text-white text-sm opacity-80 text-center leading-relaxed">
              <p>ARROWS / WASD to Move</p>
              <p>SPACE or UP to Jump</p>
            </div>
          </div>
        </div>
      )}

      {/* Game Over Screen */}
      {gameStatus === 'gameover' && (
        <div className={uiOverlayStyle}>
          <div className={panelStyle}>
            <h2 className="text-5xl font-bold text-[#E52521] tracking-widest drop-shadow-[2px_2px_0_#FFF]">
              GAME OVER
            </h2>
            <div className="flex flex-col items-center gap-2 my-4">
              <span className={textStyle}>FINAL SCORE</span>
              <span className="text-3xl text-white font-bold">{score}</span>
            </div>
            <div className="flex gap-4">
              <button className={btnStyle} onClick={handleRestart}>TRY AGAIN</button>
              <button className="bg-gray-800 border-4 border-white px-6 py-3 text-white text-xl font-bold hover:bg-gray-700 cursor-pointer" onClick={() => setStatus('start')}>MENU</button>
            </div>
          </div>
        </div>
      )}

      {/* Victory Screen */}
      {gameStatus === 'victory' && (
        <div className={uiOverlayStyle}>
          <div className={panelStyle}>
            <h2 className="text-5xl font-bold text-[#FBD000] tracking-widest drop-shadow-[2px_2px_0_#FFF]">
              LEVEL CLEARED!
            </h2>
            <div className="flex flex-col items-center gap-2 my-4">
              <span className={textStyle}>SCORE</span>
              <span className="text-3xl text-white font-bold">{score}</span>
            </div>
            <button className={btnStyle} onClick={handleNextLevel}>
              NEXT LEVEL
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
