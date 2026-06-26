extends RefCounted
class_name GroundPoundSkill

## Prefabricated skill — pound logic wired in player_platformer.gd

const BASE_COOLDOWN_SEC: float = 1.5
const POUND_SPEED: float = 520.0


static func is_enabled() -> bool:
	return GameConfig.has_skill("ground_pound")


static func cooldown_sec() -> float:
	return BASE_COOLDOWN_SEC * GameConfig.get_skill_cooldown_scale("ground_pound")
