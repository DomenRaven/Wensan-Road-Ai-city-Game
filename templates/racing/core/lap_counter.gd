extends RefCounted
class_name LapCounter

var _lap_distance_px: float = 2800.0
var _laps_target: int = 1
var _distance_since_checkpoint: float = 0.0
var _current_lap: int = 0

signal lap_completed(lap_index: int)


func setup(lap_distance_px: float, laps_target: int) -> void:
	_lap_distance_px = maxf(800.0, lap_distance_px)
	_laps_target = clampi(laps_target, 1, 3)
	_distance_since_checkpoint = 0.0
	_current_lap = 0


func advance(scroll_delta_px: float) -> void:
	_distance_since_checkpoint += scroll_delta_px
	while _distance_since_checkpoint >= _lap_distance_px:
		_distance_since_checkpoint -= _lap_distance_px
		_current_lap += 1
		lap_completed.emit(_current_lap)


func get_current_lap() -> int:
	return _current_lap


func get_laps_target() -> int:
	return _laps_target


func is_race_complete() -> bool:
	return _current_lap >= _laps_target


func get_checkpoint_progress() -> float:
	return clampf(_distance_since_checkpoint / _lap_distance_px, 0.0, 1.0)
