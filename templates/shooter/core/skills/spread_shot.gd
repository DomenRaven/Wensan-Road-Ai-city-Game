extends RefCounted

const BASE_COOLDOWN_SEC: float = 3.0
const SPREAD_ANGLES: Array[float] = [-18.0, 0.0, 18.0]

static var _cooldown_remaining: float = 0.0


static func is_enabled() -> bool:
	return GameConfig.has_skill("spread_shot")


static func tick(delta: float) -> void:
	if _cooldown_remaining > 0.0:
		_cooldown_remaining = maxf(0.0, _cooldown_remaining - delta)


static func can_fire_spread() -> bool:
	return is_enabled() and _cooldown_remaining <= 0.0


static func consume_spread() -> void:
	if not is_enabled():
		return
	var scale: float = GameConfig.get_skill_cooldown_scale("spread_shot")
	_cooldown_remaining = BASE_COOLDOWN_SEC * scale


static func get_angles() -> Array[float]:
	return SPREAD_ANGLES
