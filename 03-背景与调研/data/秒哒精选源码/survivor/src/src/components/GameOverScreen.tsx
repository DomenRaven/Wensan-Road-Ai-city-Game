import React from 'react';
import { useGameStore } from '../store/gameStore';
import { EventBus, GameEvents } from '../game/EventBus';

export default function GameOverScreen() {
  const timeRemaining = useGameStore(state => state.timeRemaining);
  const survivedTime = 180 - timeRemaining;

  return (
    <div className="absolute inset-0 bg-[#333333]/80 flex flex-col items-center justify-center z-50 backdrop-blur-sm">
      <div className="bg-[#FDFBF7] border-4 border-[#333333] shadow-[8px_8px_0px_0px_#333333] rounded-3xl p-10 flex flex-col items-center max-w-md w-full">
        <h2 className="text-4xl font-extrabold text-[#FF5C77] mb-6">失 败 !</h2>
        
        <p className="text-2xl text-[#333333] font-bold mb-8">
          存活时间：{survivedTime} 秒
        </p>

        <button 
          onClick={() => EventBus.emit(GameEvents.RESTART_GAME)}
          className="px-10 py-4 bg-[#42D6A4] text-white text-xl font-bold rounded-full 
                     border-4 border-[#333333] shadow-[4px_4px_0px_0px_#333333] 
                     active:translate-y-1 active:shadow-none transition-all hover:scale-105"
        >
          再来一局
        </button>
      </div>
    </div>
  );
}
