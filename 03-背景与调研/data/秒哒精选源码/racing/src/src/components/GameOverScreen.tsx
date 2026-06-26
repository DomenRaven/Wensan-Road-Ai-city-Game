import { EventBus } from '../game/EventBus';
import { useGameStore } from '../store/gameStore';

export const GameOverScreen = () => {
  const setGameState = useGameStore(state => state.setGameState);
  const score = useGameStore(state => state.score);

  const handleRestart = () => {
    setGameState('PLAYING');
    EventBus.emit('start-game');
  };

  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#87CEEB]/90 z-20 p-4">
      {/* Result Card */}
      <div className="bg-white border-4 border-[#1A1A1A] p-8 mb-12 shadow-[8px_8px_0_#1A1A1A] flex flex-col items-center max-w-sm w-full">
        <h2 className="text-4xl text-[#FF4500] mb-6">时间到！</h2>
        
        <div className="text-2xl text-[#1A1A1A] mb-2">你的成绩：</div>
        <div className="text-6xl text-[#FFD700] text-stroke-black mb-8" style={{ textShadow: '2px 2px 0 #1A1A1A, -2px -2px 0 #1A1A1A, 2px -2px 0 #1A1A1A, -2px 2px 0 #1A1A1A' }}>
          {score} 圈
        </div>

        <button
          onClick={handleRestart}
          className="w-full bg-[#FFD700] border-4 border-[#1A1A1A] text-[#1A1A1A] text-2xl py-4 shadow-[6px_6px_0_#1A1A1A] active:shadow-[0_0_0_#1A1A1A] active:translate-y-1.5 transition-all"
        >
          再玩一次
        </button>
      </div>
    </div>
  );
};
