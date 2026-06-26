extends RefCounted

const BASE_COOLDOWN_SEC: float = 4.0
const DOUBLE_TAP_WINDOW_SEC: float = 0.32
const FrameDataRes = preload("res://core/frame_data.gd")

static var _cooldown_remaining: float = 0.0
static var _last_attack_time: float = -999.0


static func is_enabled() -> bool:
	return GameConfig.has_skill("special_uppercut")


static func tick(delta: float) -> void:
	if _cooldown_remaining > 0.0:
		_cooldown_remaining = maxf(0.0, _cooldown_remaining - delta)


static func register_attack_attempt(now_sec: float) -> bool:
	if not is_enabled() or _cooldown_remaining > 0.0:
		_last_attack_time = now_sec
		return false
	var is_double: bool = now_sec - _last_attack_time <= DOUBLE_TAP_WINDOW_SEC
	_last_attack_time = now_sec
	if is_double:
		var scale: float = GameConfig.get_skill_cooldown_scale("special_uppercut")
		_cooldown_remaining = BASE_COOLDOWN_SEC * scale
		return true
	return false


static func build_move_data(light_data: Resource) -> Resource:
	var data: Resource = FrameDataRes.new()
	data.startup_frames = maxi(4, light_data.startup_frames - 2)
	data.active_frames = light_data.active_frames + 1
	data.recovery_frames = light_data.recovery_frames + 4
	data.damage = int(round(float(light_data.damage) * 1.6))
	data.hitstun_frames = light_data.hitstun_frames + 6
	data.knockback = light_data.knockback * 1.8
	data.hitbox_size = Vector2(light_data.hitbox_size.x, light_data.hitbox_size.y + 12.0)
	data.hitbox_offset = Vector2(light_data.hitbox_offset.x, light_data.hitbox_offset.y - 10.0)
	return data
