import React, { useEffect, useRef } from 'react';
import Phaser from 'phaser';
import { useGameStore } from './store/useGameStore';
import { EventBus, EVENTS } from './game/EventBus';
import { Boot } from './game/scenes/Boot';
import { GameScene } from './game/scenes/Game';
import { GameOver } from './game/scenes/GameOver';
import { CONSTANTS } from './game/constants';
import { Play, RotateCcw } from 'lucide-react';

export default function App() {
  const initialized = useRef(false);
  const { status, score, timeLeft, setStatus, setScore, setTimeLeft, resetGame } = useGameStore();

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    const game = new Phaser.Game({
      type: Phaser.AUTO,
      parent: 'game-container',
      width: CONSTANTS.WIDTH,
      height: CONSTANTS.HEIGHT,
      scene: [Boot, GameScene, GameOver],
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
      backgroundColor: '#87CEEB', // 天空蓝背景
    });

    const onGameStart = () => {
      resetGame();
    };

    const onGameOver = (finalScore: number) => {
      setStatus('gameover');
      setScore(finalScore);
    };

    const onScoreUpdate = (newScore: number) => {
      setScore(newScore);
    };

    const onTimeUpdate = (newTime: number) => {
      setTimeLeft(newTime);
    };

    EventBus.on(EVENTS.GAME_START, onGameStart);
    EventBus.on(EVENTS.GAME_OVER, onGameOver);
    EventBus.on(EVENTS.SCORE_UPDATE, onScoreUpdate);
    EventBus.on(EVENTS.TIME_UPDATE, onTimeUpdate);

    return () => {
      game.destroy(true);
      initialized.current = false;
      EventBus.off(EVENTS.GAME_START, onGameStart);
      EventBus.off(EVENTS.GAME_OVER, onGameOver);
      EventBus.off(EVENTS.SCORE_UPDATE, onScoreUpdate);
      EventBus.off(EVENTS.TIME_UPDATE, onTimeUpdate);
    };
  }, [resetGame, setStatus, setScore, setTimeLeft]);

  const startGame = () => {
    EventBus.emit('ui-start-game');
  };

  const restartGame = () => {
    EventBus.emit('ui-restart-game');
  };

  return (
    <div className="w-screen h-screen overflow-hidden bg-gray-900 relative font-sans">
      <div id="game-container" className="w-full h-full" />

      {/* HUD Layer */}
      {status === 'playing' && (
        <div className="absolute top-0 left-0 w-full p-6 flex justify-between items-start pointer-events-none text-2xl md:text-4xl font-bold text-white drop-shadow-md">
          <div className="text-left">
            <span className="text-gray-800" style={{ WebkitTextStroke: '2px white' }}>距离: {Math.floor(score)}m</span>
          </div>
          <div className={`text-right ${timeLeft <= 10 ? 'text-orange-500 animate-pulse' : 'text-gray-800'}`} style={{ WebkitTextStroke: '2px white' }}>
            倒计时: {Math.floor(timeLeft)}s
          </div>
        </div>
      )}

      {/* Start Screen */}
      {status === 'menu' && (
        <div className="absolute inset-0 bg-black/60 flex items-center justify-center pointer-events-auto">
          <div className="bg-white rounded-2xl p-8 max-w-md w-full text-center border-4 border-gray-800 shadow-[0_8px_0_#333333]">
            <h1 className="text-4xl font-black text-green-500 mb-4" style={{ WebkitTextStroke: '1px #333' }}>K12 无尽跑酷</h1>
            <p className="text-gray-600 mb-8 font-medium">
              按 <kbd className="bg-gray-100 border-2 border-gray-300 rounded px-2 py-1 mx-1">空格</kbd> 跳跃高栏<br/>
              按 <kbd className="bg-gray-100 border-2 border-gray-300 rounded px-2 py-1 mx-1">↓</kbd> 滑铲通过低栏
            </p>
            <button
              onClick={startGame}
              className="bg-green-500 hover:bg-green-400 active:translate-y-1 active:shadow-none text-white font-bold text-2xl py-4 px-8 rounded-xl w-full border-4 border-gray-800 shadow-[0_6px_0_#388E3C] transition-all flex items-center justify-center gap-2"
            >
              <Play size={28} />
              立即创作
            </button>
          </div>
        </div>
      )}

      {/* Game Over Screen */}
      {status === 'gameover' && (
        <div className="absolute inset-0 bg-black/60 flex items-center justify-center pointer-events-auto">
          <div className="bg-white rounded-2xl p-8 max-w-md w-full text-center border-4 border-gray-800 shadow-[0_8px_0_#333333]">
            <h1 className="text-4xl font-black text-orange-500 mb-4" style={{ WebkitTextStroke: '1px #333' }}>游戏结束</h1>
            <div className="text-6xl font-black text-gray-800 mb-8">
              {Math.floor(score)}
              <span className="text-2xl ml-2">m</span>
            </div>
            <button
              onClick={restartGame}
              className="bg-green-500 hover:bg-green-400 active:translate-y-1 active:shadow-none text-white font-bold text-2xl py-4 px-8 rounded-xl w-full border-4 border-gray-800 shadow-[0_6px_0_#388E3C] transition-all flex items-center justify-center gap-2"
            >
              <RotateCcw size={28} />
              再来一次
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
