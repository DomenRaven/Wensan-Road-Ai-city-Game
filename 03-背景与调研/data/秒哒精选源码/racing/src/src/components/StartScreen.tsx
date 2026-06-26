import { EventBus } from '../game/EventBus';
import { useGameStore } from '../store/gameStore';

export const StartScreen = () => {
  const setGameState = useGameStore(state => state.setGameState);

  const handleStart = () => {
    setGameState('PLAYING');
    EventBus.emit('start-game');
  };

  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#87CEEB] z-10 p-4">
      {/* Title Card */}
      <div className="bg-white border-4 border-[#1A1A1A] p-6 mb-12 shadow-[8px_8px_0_#1A1A1A]">
        <h1 className="text-4xl text-[#FF4500] text-center mb-2">K12 欢乐赛车</h1>
        <p className="text-[#1A1A1A] text-lg text-center">快乐竞速，挑战极限！</p>
      </div>

      {/* Instructions */}
      <div className="bg-white border-4 border-[#1A1A1A] p-6 mb-12 shadow-[8px_8px_0_#1A1A1A] max-w-sm w-full text-[#1A1A1A]">
        <h2 className="text-2xl text-center mb-4 text-[#FFD700] bg-[#1A1A1A] py-1">操作说明</h2>
        <ul className="space-y-4 text-lg">
          <li className="flex justify-between items-center">
            <span>← →</span>
            <span>左右转向</span>
          </li>
          <li className="flex justify-between items-center">
            <span>Space (空格)</span>
            <span>长按加速</span>
          </li>
          <li className="flex justify-between items-center">
            <span>目标</span>
            <span>90秒跑出最多圈数</span>
          </li>
        </ul>
      </div>

      {/* Start Button */}
      <button
        onClick={handleStart}
        className="bg-[#FFD700] border-4 border-[#1A1A1A] text-[#1A1A1A] text-3xl py-4 px-12 shadow-[8px_8px_0_#1A1A1A] active:shadow-[0_0_0_#1A1A1A] active:translate-y-2 transition-all"
      >
        开始游戏
      </button>
    </div>
  );
};
