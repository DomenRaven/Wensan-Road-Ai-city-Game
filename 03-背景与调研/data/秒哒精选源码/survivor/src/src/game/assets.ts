import mainChar1Idle from '../assets/top-down/PNG/mainChar/1/Idle.png';
import mainChar1_1 from '../assets/top-down/PNG/mainChar/1/1.png';
import mainChar1_2 from '../assets/top-down/PNG/mainChar/1/2.png';
import mainChar1_3 from '../assets/top-down/PNG/mainChar/1/3.png';
import mainChar1_4 from '../assets/top-down/PNG/mainChar/1/4.png';

import monster1_1 from '../assets/top-down/PNG/Monster/1/1.png';
import monster1_2 from '../assets/top-down/PNG/Monster/1/2.png';
import monster1_3 from '../assets/top-down/PNG/Monster/1/3.png';
import monster1_4 from '../assets/top-down/PNG/Monster/1/4.png';

import monster3_1 from '../assets/top-down/PNG/Monster/3/1.png';
import monster3_2 from '../assets/top-down/PNG/Monster/3/2.png';
import monster3_3 from '../assets/top-down/PNG/Monster/3/3.png';
import monster3_4 from '../assets/top-down/PNG/Monster/3/4.png';

import monster6_1 from '../assets/top-down/PNG/Monster/6/1.png';
import monster6_2 from '../assets/top-down/PNG/Monster/6/2.png';
import monster6_3 from '../assets/top-down/PNG/Monster/6/3.png';
import monster6_4 from '../assets/top-down/PNG/Monster/6/4.png';

import expGem from '../assets/top-down/PNG/Items02.png';
import hitFx from '../assets/top-down/PNG/Colision_Sprites/4.png';

export const AssetPaths = {
  player: {
    idle: mainChar1Idle,
    walk: [mainChar1_1, mainChar1_2, mainChar1_3, mainChar1_4],
  },
  monsters: {
    1: [monster1_1, monster1_2, monster1_3, monster1_4],
    3: [monster3_1, monster3_2, monster3_3, monster3_4],
    6: [monster6_1, monster6_2, monster6_3, monster6_4],
  },
  items: {
    expGem,
  },
  fx: {
    hit: hitFx,
  }
};
