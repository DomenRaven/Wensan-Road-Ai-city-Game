extends RefCounted


static func clamp_float(value: float, default_value: float, ratio: float = 0.3) -> float:
	var lo: float = default_value * (1.0 - ratio)
	var hi: float = default_value * (1.0 + ratio)
	if lo > hi:
		var tmp: float = lo
		lo = hi
		hi = tmp
	return clampf(value, lo, hi)


## 专用于 jump_velocity 等「负值越大绝对值 = 效果越强」的参数
static func clamp_negative_magnitude(value: float, default_value: float, ratio: float = 0.3) -> float:
	if default_value >= 0.0:
		return clamp_float(value, default_value, ratio)
	var def_mag: float = absf(default_value)
	var val_mag: float = absf(value)
	var min_mag: float = def_mag * maxf(0.0, 1.0 - ratio)
	var max_mag: float = def_mag * (1.0 + ratio)
	return -clampf(val_mag, min_mag, max_mag)


static func clamp_int(value: int, default_value: int, ratio: float = 0.3) -> int:
	var lo: int = int(floor(float(default_value) * (1.0 - ratio)))
	var hi: int = int(ceil(float(default_value) * (1.0 + ratio)))
	if lo > hi:
		var tmp: int = lo
		lo = hi
		hi = tmp
	return clampi(value, lo, hi)
