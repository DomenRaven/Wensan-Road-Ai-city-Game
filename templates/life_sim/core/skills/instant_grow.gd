extends RefCounted
class_name InstantGrowSkill

const BASE_COOLDOWN_SEC: float = 25.0


static func is_enabled() -> bool:
	return GameConfig.has_skill("instant_grow")


static func get_cooldown_sec() -> float:
	return BASE_COOLDOWN_SEC * GameConfig.get_skill_cooldown_scale("instant_grow")
