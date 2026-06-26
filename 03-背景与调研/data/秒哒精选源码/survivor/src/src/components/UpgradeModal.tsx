import React, { useEffect } from 'react';
import { useGameStore, UpgradeOption } from '../store/gameStore';

export default function UpgradeModal() {
  const { applyUpgrade, setPendingUpgrades, pendingUpgrades } = useGameStore();

    useEffect(() => {
    // 每次弹出时，随机生成3个选项
    const allOptions: UpgradeOption[] = ['attack_speed', 'attack_damage', 'move_speed', 'multi_shot', 'max_hp', 'hp_regen'];
    const generated: UpgradeOption[] = [];
    // 简单随机抽3个，允许重复或不重复均可。这里做成不重复抽3个
    const shuffled = [...allOptions].sort(() => 0.5 - Math.random());
    generated.push(...shuffled.slice(0, 3));
    
    setPendingUpgrades(generated);
  }, [setPendingUpgrades]);

  const handleSelect = (option: UpgradeOption) => {
    applyUpgrade(option);
  };

  const getOptionText = (opt: UpgradeOption) => {
    switch (opt) {
      case 'attack_speed': return { title: '攻击速度', desc: '攻击间隔减少 20%' };
      case 'attack_damage': return { title: '攻击伤害', desc: '基础伤害 + 5' };
      case 'move_speed': return { title: '移动速度', desc: '移速提升 10%' };
      case 'multi_shot': return { title: '连发提升', desc: '一次发射的子弹数 + 1' };
      case 'max_hp': return { title: '血量上限', desc: '最大生命值 + 50' };
      case 'hp_regen': return { title: '自动回血', desc: '每秒自动回复 1 点生命' };
    }
  };

  if (pendingUpgrades.length === 0) return null;

  return (
    <div className="absolute inset-0 bg-[#333333]/80 flex flex-col items-center justify-center z-50 backdrop-blur-sm p-4">
      <h2 className="text-4xl font-extrabold text-[#FDFBF7] mb-8 drop-shadow-md">等级提升！</h2>
      
      <div className="flex flex-col md:flex-row gap-6 w-full max-w-4xl justify-center items-stretch">
        {pendingUpgrades.map((opt, idx) => {
          const { title, desc } = getOptionText(opt);
          return (
            <button 
              key={idx}
              onClick={() => handleSelect(opt)}
              className="flex-1 min-h-[200px] bg-[#FDFBF7] rounded-3xl p-6 flex flex-col items-center justify-center
                         border-4 border-[#333333] shadow-[8px_8px_0px_0px_#333333] 
                         active:translate-y-2 active:shadow-none transition-all hover:scale-105 hover:bg-[#42D6A4] group"
            >
              <h3 className="text-2xl font-extrabold text-[#333333] mb-4 group-hover:text-white transition-colors">{title}</h3>
              <p className="text-[#666666] font-bold group-hover:text-[#FDFBF7] transition-colors">{desc}</p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
