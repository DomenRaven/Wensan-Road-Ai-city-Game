extends RefCounted
class_name GoldRushSkill

const BASE_COOLDOWN_MS: int = 45000


static func is_enabled() -> bool:
	return GameConfig.has_skill("gold_rush")


static func get_cooldown_sec() -> float:
	var scale: float = GameConfig.get_skill_cooldown_scale("gold_rush")
	return float(BASE_COOLDOWN_MS) * scale / 1000.0


static func activate() -> bool:
	return is_enabled()
