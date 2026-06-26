extends RefCounted


static func clamp_float(value: float, default_value: float, ratio: float = 0.3) -> float:
	var lo: float = default_value * (1.0 - ratio)
	var hi: float = default_value * (1.0 + ratio)
	return clampf(value, lo, hi)


static func clamp_int(value: int, default_value: int, ratio: float = 0.3) -> int:
	var lo: int = int(floor(float(default_value) * (1.0 - ratio)))
	var hi: int = int(ceil(float(default_value) * (1.0 + ratio)))
	return clampi(value, lo, hi)
