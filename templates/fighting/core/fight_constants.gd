extends RefCounted

const REF_WIDTH: float = 960.0
const SPRITE_FRAME_H: float = 96.0
const SPRITE_SCALE: float = 0.72
const FOOT_OFFSET_Y: float = 12.0


static func combat_cfg() -> Dictionary:
	return GameConfig.get_tuning().get("combat", {}) as Dictionary


static func floor_surface_y() -> float:
	return float_val("floor_surface_y", 318.0)


static func fighter_body_y() -> float:
	return floor_surface_y() - FOOT_OFFSET_Y


static func sprite_offset_y() -> float:
	var half_h: float = SPRITE_FRAME_H * SPRITE_SCALE * 0.5
	return FOOT_OFFSET_Y - half_h

static func scale_x(value: float, arena_width: float) -> float:
	return value * (arena_width / REF_WIDTH)


static func int_scaled(key: String, default_value: int, arena_width: float) -> int:
	var raw: float = float(combat_cfg().get(key, default_value))
	return int(round(raw * (arena_width / REF_WIDTH)))


static func float_val(key: String, default_value: float) -> float:
	return float(combat_cfg().get(key, default_value))
