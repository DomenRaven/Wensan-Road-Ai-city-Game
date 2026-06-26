extends RefCounted

const BASE_COOLDOWN_SEC: float = 15.0

static var _cooldown_remaining: float = 0.0


static func is_enabled() -> bool:
	return GameConfig.has_skill("bomb")


static func tick(delta: float) -> void:
	if _cooldown_remaining > 0.0:
		_cooldown_remaining = maxf(0.0, _cooldown_remaining - delta)


static func can_use() -> bool:
	return is_enabled() and _cooldown_remaining <= 0.0


static func try_activate() -> bool:
	if not can_use():
		return false
	var scale: float = GameConfig.get_skill_cooldown_scale("bomb")
	_cooldown_remaining = BASE_COOLDOWN_SEC * scale
	return true


static func get_cooldown_remaining() -> float:
	return _cooldown_remaining
