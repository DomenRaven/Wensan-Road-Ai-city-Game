import React from 'react';
import { useGameStore } from '../store/gameStore';
import { EventBus, GameEvents } from '../game/EventBus';

export default function StartScreen() {
  return (
    <div className="absolute inset-0 bg-[#FDFBF7] flex flex-col items-center justify-center z-50">
      <h1 className="text-5xl font-extrabold text-[#333333] mb-12 drop-shadow-md tracking-wider">
        K12 割草幸存者
      </h1>
      
      <button 
        onClick={() => EventBus.emit(GameEvents.START_GAME)}
        className="px-12 py-4 bg-[#42D6A4] text-white text-2xl font-bold rounded-full 
                   border-4 border-[#333333] shadow-[4px_4px_0px_0px_#333333] 
                   active:translate-y-1 active:shadow-none transition-all
                   hover:scale-105"
      >
        开始游戏
      </button>

      <p className="mt-8 text-xl text-[#666666] font-bold text-center leading-relaxed">
        操作说明：<br />
        使用 W A S D 移动<br />
        鼠标点击屏幕改变角色朝向，角色会自动向朝向发射子弹
      </p>
    </div>
  );
}
