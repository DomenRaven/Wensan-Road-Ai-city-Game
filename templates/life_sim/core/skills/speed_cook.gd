extends RefCounted
class_name SpeedCookSkill

const BASE_COOLDOWN_SEC: float = 20.0


static func is_enabled() -> bool:
	return GameConfig.has_skill("speed_cook")


static func get_cooldown_sec() -> float:
	return BASE_COOLDOWN_SEC * GameConfig.get_skill_cooldown_scale("speed_cook")


static func get_speed_multiplier() -> float:
	return 0.5
