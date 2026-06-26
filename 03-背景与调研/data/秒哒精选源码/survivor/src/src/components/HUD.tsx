import React from 'react';
import { useGameStore } from '../store/gameStore';

export default function HUD() {
  const { timeRemaining, exp, maxExp, level, playerHp, playerMaxHp } = useGameStore();

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const expPercent = Math.min(100, Math.max(0, (exp / maxExp) * 100));
  const hpPercent = Math.min(100, Math.max(0, (playerHp / playerMaxHp) * 100));

  return (
    <div className="absolute inset-0 pointer-events-none z-10 flex flex-col p-4">
      {/* 顶部经验条与倒计时 */}
      <div className="flex flex-col items-center w-full max-w-2xl mx-auto space-y-4">
        
        {/* 倒计时警示 / BOSS提示 */}
        <div className={`text-4xl font-extrabold px-6 py-2 rounded-2xl border-4 border-[#333333] shadow-[4px_4px_0px_0px_#333333] 
          ${timeRemaining <= 10 && timeRemaining > 0 ? 'bg-[#FF5C77] text-white animate-pulse' : 'bg-[#FDFBF7] text-[#333333]'}`}
        >
          {useGameStore.getState().status === 'boss_fight' ? 'BOSS 战' : formatTime(timeRemaining)}
        </div>

        {/* 经验条 */}
        <div className="w-full flex items-center space-x-4 bg-[#FDFBF7] p-2 rounded-full border-4 border-[#333333] shadow-[4px_4px_0px_0px_#333333]">
          <div className="font-bold text-[#333333] px-2 whitespace-nowrap">Lv.{level}</div>
          <div className="flex-1 h-6 bg-[#E5E0D8] rounded-full overflow-hidden border-2 border-[#333333]">
            <div 
              className="h-full bg-[#42D6A4] transition-all duration-300 ease-out" 
              style={{ width: `${expPercent}%` }}
            />
          </div>
        </div>
        
      </div>

      {/* 底部血条 (稍微偏移，或者放在左上角) */}
      <div className="mt-auto mb-8 w-64 mx-auto flex flex-col items-center bg-[#FDFBF7] p-2 rounded-2xl border-4 border-[#333333] shadow-[4px_4px_0px_0px_#333333]">
        <div className="w-full flex justify-between text-sm font-bold text-[#333333] mb-1 px-1">
          <span>HP</span>
          <span>{Math.ceil(playerHp)} / {playerMaxHp}</span>
        </div>
        <div className="w-full h-4 bg-[#E5E0D8] rounded-full overflow-hidden border-2 border-[#333333]">
          <div 
            className="h-full bg-[#FF5C77] transition-all duration-200"
            style={{ width: `${hpPercent}%` }}
          />
        </div>
      </div>
    </div>
  );
}
