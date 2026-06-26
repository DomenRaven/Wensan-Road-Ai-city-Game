extends RefCounted

const BASE_COOLDOWN_SEC: float = 8.0
const SHIELD_DURATION_SEC: float = 2.0

static var _cooldown_remaining: float = 0.0
static var _shield_remaining: float = 0.0


static func is_enabled() -> bool:
	return GameConfig.has_skill("shield_burst")


static func tick(delta: float) -> void:
	if _cooldown_remaining > 0.0:
		_cooldown_remaining = maxf(0.0, _cooldown_remaining - delta)
	if _shield_remaining > 0.0:
		_shield_remaining = maxf(0.0, _shield_remaining - delta)


static func is_active() -> bool:
	return _shield_remaining > 0.0


static func try_activate() -> bool:
	if not is_enabled() or _cooldown_remaining > 0.0 or _shield_remaining > 0.0:
		return false
	var scale: float = GameConfig.get_skill_cooldown_scale("shield_burst")
	_cooldown_remaining = BASE_COOLDOWN_SEC * scale
	_shield_remaining = SHIELD_DURATION_SEC
	return true
