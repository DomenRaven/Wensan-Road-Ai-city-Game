export const characterImages: Record<string, string> = import.meta.glob('../assets/gladiators/PNG/Characters/**/*.png', { eager: true, query: '?url', import: 'default' });

export const backgroundImages: Record<string, string> = import.meta.glob('../assets/gladiators/PNG/Backgrounds/**/*.png', { eager: true, query: '?url', import: 'default' });

export const uiImages: Record<string, string> = import.meta.glob('../assets/gladiators/PNG/Ui/**/*.png', { eager: true, query: '?url', import: 'default' });

// Function to resolve character frame URL
export function getCharacterFrame(char: string, anim: string, frame: number): string | undefined {
  // Format: ../assets/gladiators/PNG/Characters/Char1/Idle/skeleton-Idle_0.png
  const path = `../assets/gladiators/PNG/Characters/${char}/${anim}/skeleton-${anim}_${frame}.png`;
  return characterImages[path];
}

// Map UI keys to simple paths
export const UI_ASSETS = {
  bg_battle: backgroundImages['../assets/gladiators/PNG/Backgrounds/BG1/Full.png'],
  ui_knight1: uiImages['../assets/gladiators/PNG/Ui/Knight1.png'],
  ui_knight2: uiImages['../assets/gladiators/PNG/Ui/Knight2.png'],
  ui_btn_start: uiImages['../assets/gladiators/PNG/Ui/Button1.png'],
  ui_btn_replay: uiImages['../assets/gladiators/PNG/Ui/Button2.png'],
  ui_hp_bg: uiImages['../assets/gladiators/PNG/Ui/Healthpoint_bg.png'],
  ui_hp_green: uiImages['../assets/gladiators/PNG/Ui/GreenHp.png'],
  ui_hp_enemy: uiImages['../assets/gladiators/PNG/Ui/EnemyHpbar.png'],
  ui_win: uiImages['../assets/gladiators/PNG/Ui/WinBar.png'],
  ui_defeat: uiImages['../assets/gladiators/PNG/Ui/DefeatBar.png'],
  ui_popup: uiImages['../assets/gladiators/PNG/Ui/popupBox.png'],
};
