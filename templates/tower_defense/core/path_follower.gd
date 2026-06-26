extends RefCounted
class_name PathFollower

## Core locked: preset_waypoints path mode

var waypoints: Array[Vector2] = []
var current_index: int = 0
var current_position: Vector2 = Vector2.ZERO
var finished: bool = false


func setup(points: Array[Vector2]) -> void:
	waypoints = points
	current_index = 0
	finished = waypoints.is_empty()
	if not waypoints.is_empty():
		current_position = waypoints[0]
	else:
		current_position = Vector2.ZERO


func advance(speed: float, delta: float) -> Vector2:
	if finished or waypoints.is_empty():
		finished = true
		return Vector2.ZERO
	if current_index >= waypoints.size() - 1:
		finished = true
		return Vector2.ZERO
	var target: Vector2 = waypoints[current_index + 1]
	var to_target: Vector2 = target - current_position
	var distance: float = to_target.length()
	if distance <= 0.001:
		current_index += 1
		current_position = target
		if current_index >= waypoints.size() - 1:
			finished = true
		return Vector2.ZERO
	var step: float = speed * delta
	if step >= distance:
		var move: Vector2 = to_target
		current_position = target
		current_index += 1
		if current_index >= waypoints.size() - 1:
			finished = true
		return move
	var move_partial: Vector2 = to_target.normalized() * step
	current_position += move_partial
	return move_partial


func get_progress_ratio() -> float:
	if waypoints.size() <= 1:
		return 1.0
	var segment_count: float = float(waypoints.size() - 1)
	return clampf(float(current_index) / segment_count, 0.0, 1.0)
