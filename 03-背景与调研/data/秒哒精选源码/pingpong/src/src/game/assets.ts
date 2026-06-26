export const ASSETS = {
  court_bg: 'court_bg',
  court_center_line: 'court_center_line',
  paddle_player: 'paddle_player',
  paddle_ai: 'paddle_ai',
  ball: 'ball',
  ball_shadow: 'ball_shadow',
  score_digits: 'score_digits',
  text_win: 'text_win',
  text_lose: 'text_lose',
  btn_start: 'btn_start',
  btn_again: 'btn_again',
  board: 'board',
} as const;

import courtBgSrc from '../assets/pong-football/assets/png/court_01.png';
import courtCenterLineSrc from '../assets/pong-football/assets/png/court_center_line.png';
import paddlePlayerSrc from '../assets/pong-football/assets/png/pud_left.png';
import paddleAiSrc from '../assets/pong-football/assets/png/pud_right.png';
import ballFramesSrc from '../assets/pong-football/assets/png/ball_frames.png';
import ballShadowSrc from '../assets/pong-football/assets/png/ball_shadow.png';
import numbersScoreSrc from '../assets/pong-football/assets/png/numbers_score.png';
import textWinSrc from '../assets/pong-football/assets/png/text_win.png';
import textLoseSrc from '../assets/pong-football/assets/png/text_lose.png';
import btnStartSrc from '../assets/pong-football/assets/png/btn_menu_h_start.png';
import btnAgainSrc from '../assets/pong-football/assets/png/btn_round_again.png';
import boardSrc from '../assets/pong-football/assets/png/board.png';

export const ASSET_SOURCES = {
  [ASSETS.court_bg]: courtBgSrc,
  [ASSETS.court_center_line]: courtCenterLineSrc,
  [ASSETS.paddle_player]: paddlePlayerSrc,
  [ASSETS.paddle_ai]: paddleAiSrc,
  [ASSETS.ball]: ballFramesSrc,
  [ASSETS.ball_shadow]: ballShadowSrc,
  [ASSETS.score_digits]: numbersScoreSrc,
  [ASSETS.text_win]: textWinSrc,
  [ASSETS.text_lose]: textLoseSrc,
  [ASSETS.btn_start]: btnStartSrc,
  [ASSETS.btn_again]: btnAgainSrc,
  [ASSETS.board]: boardSrc,
};
