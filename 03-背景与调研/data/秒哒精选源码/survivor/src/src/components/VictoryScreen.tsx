import React from 'react';
import { EventBus, GameEvents } from '../game/EventBus';
import { useGameStore } from '../store/gameStore';

export default function VictoryScreen() {
  const { level, bossFightTime } = useGameStore();
  const totalTime = 180 + bossFightTime;

  return (
    <div className="absolute inset-0 bg-[#333333]/80 flex flex-col items-center justify-center z-50 backdrop-blur-sm">
      <div className="bg-[#FDFBF7] border-4 border-[#333333] shadow-[8px_8px_0px_0px_#333333] rounded-3xl p-10 flex flex-col items-center max-w-md w-full">
        <h2 className="text-4xl font-extrabold text-[#42D6A4] mb-6 drop-shadow-sm">胜 利 !</h2>
        
        <p className="text-2xl text-[#333333] font-bold mb-4 text-center">
          你成功击败了BOSS！
        </p>

        <div className="bg-white w-full rounded-2xl border-4 border-[#E5E0D8] p-4 mb-8 flex flex-col space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-[#999999] font-bold">最终等级</span>
            <span className="text-[#333333] font-black text-xl">Lv.{level}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-[#999999] font-bold">存活总时长</span>
            <span className="text-[#42D6A4] font-black text-xl">{totalTime}秒</span>
          </div>
        </div>

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
