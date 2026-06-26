extends RefCounted
class_name SlideSkill

## Prefabricated skill — slide logic wired in player_runner.gd

const BASE_COOLDOWN_SEC: float = 2.0
const SLIDE_DURATION_SEC: float = 0.55


static func is_enabled() -> bool:
	return GameConfig.has_skill("slide")


static func get_cooldown_sec() -> float:
	return BASE_COOLDOWN_SEC * GameConfig.get_skill_cooldown_scale("slide")
