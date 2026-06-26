import { useGameStore } from '../store/gameStore';

export const HUD = () => {
  const score = useGameStore(state => state.score);
  const timeLeft = useGameStore(state => state.timeLeft);

  // Time warning styles
  const isTimeRunningOut = timeLeft <= 10;
  const timeColor = isTimeRunningOut ? 'text-[#FF4500]' : 'text-white';
  const timeAnimation = isTimeRunningOut ? 'animate-pulse scale-110' : '';

  return (
    <div className="absolute top-0 left-0 w-full p-4 flex justify-between items-start z-10 pointer-events-none">
      
      {/* Timer */}
      <div className="bg-[#1A1A1A] border-4 border-white p-2 shadow-[4px_4px_0_#FFD700]">
        <div className="text-white text-sm mb-1">时间</div>
        <div className={`text-3xl transition-transform ${timeColor} ${timeAnimation}`}>
          {timeLeft}s
        </div>
      </div>

      {/* Laps */}
      <div className="bg-[#FFD700] border-4 border-[#1A1A1A] p-2 shadow-[4px_4px_0_#1A1A1A] text-right">
        <div className="text-[#1A1A1A] text-sm mb-1">圈数</div>
        <div className="text-3xl text-[#1A1A1A]">
          {score}
        </div>
      </div>
      
    </div>
  );
};
