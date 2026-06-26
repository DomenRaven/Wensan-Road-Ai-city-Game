extends RefCounted

const BASE_COOLDOWN_SEC: float = 6.0
const ACTIVE_DURATION_SEC: float = 3.0

static var _cooldown_remaining: float = 0.0
static var _active_remaining: float = 0.0


static func is_enabled() -> bool:
	return GameConfig.has_skill("laser_beam")


static func tick(delta: float) -> void:
	if _cooldown_remaining > 0.0:
		_cooldown_remaining = maxf(0.0, _cooldown_remaining - delta)
	if _active_remaining > 0.0:
		_active_remaining = maxf(0.0, _active_remaining - delta)


static func is_active() -> bool:
	return _active_remaining > 0.0


static func can_use() -> bool:
	return is_enabled() and _cooldown_remaining <= 0.0 and not is_active()


static func try_activate() -> bool:
	if not can_use():
		return false
	var scale: float = GameConfig.get_skill_cooldown_scale("laser_beam")
	_cooldown_remaining = BASE_COOLDOWN_SEC * scale
	_active_remaining = ACTIVE_DURATION_SEC
	return true


static func get_cooldown_remaining() -> float:
	return _cooldown_remaining
