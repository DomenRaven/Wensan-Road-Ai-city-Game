extends Node2D

const HURDLE_SCENE: PackedScene = preload("res://scenes/prefabs/hurdle.tscn")

signal hurdle_hit_player

var _runner_speed: float = 240.0
var _density: float = 0.4
var _min_gap_px: float = 200.0
var _distance_since_spawn: float = 999.0
var _hurdle_texture: Texture2D = null
var _game_over: bool = false

@onready var _hurdles_root: Node2D = $Hurdles


func setup(
	runner_speed: float,
	density: float,
	min_gap_px: float,
	hurdle_texture: Texture2D
) -> void:
	_runner_speed = runner_speed
	_density = clampf(density, 0.3, 1.0)
	_min_gap_px = clampf(min_gap_px, 120.0, 280.0)
	_hurdle_texture = hurdle_texture


func set_game_over(value: bool) -> void:
	_game_over = value


func set_scroll_speed(speed: float) -> void:
	_runner_speed = speed
	for child: Node in _hurdles_root.get_children():
		if child.has_method("set_scroll_speed"):
			child.call("set_scroll_speed", speed)


func advance_distance(_delta: float, distance_delta: float) -> void:
	if _game_over:
		return
	_distance_since_spawn += distance_delta
	var required_gap: float = _min_gap_px / maxf(0.35, _density)
	if _distance_since_spawn >= required_gap:
		_spawn_hurdle()
		_distance_since_spawn = 0.0
	for child: Node in _hurdles_root.get_children():
		if child.has_method("set_scroll_speed"):
			child.call("set_scroll_speed", _runner_speed)


func _spawn_hurdle() -> void:
	var hurdle: Area2D = HURDLE_SCENE.instantiate() as Area2D
	_hurdles_root.add_child(hurdle)
	hurdle.position = Vector2(680.0, 300.0)
	if hurdle.has_method("setup"):
		hurdle.call("setup", _runner_speed, _hurdle_texture)
	if hurdle.has_signal("player_hit"):
		hurdle.player_hit.connect(_on_hurdle_player_hit)


func _on_hurdle_player_hit() -> void:
	hurdle_hit_player.emit()
