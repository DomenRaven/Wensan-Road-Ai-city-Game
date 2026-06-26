extends Node2D

const ThemeSpriteUtil := preload("res://core/theme_sprite.gd")
const TimerHudUtil := preload("res://core/timer_hud.gd")
const SprintBurstSkill := preload("res://core/skills/sprint_burst.gd")
const FinishLineScript := preload("res://core/finish_line.gd")

var _manager: Node = null
var _base_speed: float = 240.0
var _boost_multiplier: float = 1.4
var _accel_rate: float = 4.0
var _current_speed: float = 240.0
var _track_length_px: float = 3000.0
var _round_duration: float = 60.0
var _elapsed: float = 0.0
var _distance_px: float = 0.0
var _game_over: bool = false

@onready var _player: CharacterBody2D = $Player
@onready var _scroll_track: Node2D = $ScrollTrack
@onready var _spawner: Node2D = $HurdleSpawner
@onready var _background: ColorRect = $Background


func setup(manager: Node) -> void:
	_manager = manager
	_apply_tuning()
	_apply_theme()
	_setup_world()
	if _spawner.has_signal("hurdle_hit_player"):
		_spawner.hurdle_hit_player.connect(_on_hurdle_hit_player)


func _apply_tuning() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var runner_cfg: Dictionary = tuning.get("runner", {}) as Dictionary
	var round_cfg: Dictionary = tuning.get("round", {}) as Dictionary
	var track_cfg: Dictionary = tuning.get("track", {}) as Dictionary
	_base_speed = clampf(float(runner_cfg.get("speed", _base_speed)), 160.0, 360.0)
	_boost_multiplier = clampf(float(runner_cfg.get("boost_multiplier", _boost_multiplier)), 1.2, 1.8)
	_accel_rate = clampf(float(runner_cfg.get("accel_rate", _accel_rate)), 2.0, 8.0)
	_current_speed = _base_speed
	_round_duration = clampf(float(round_cfg.get("duration_sec", _round_duration)), 45.0, 90.0)
	_track_length_px = clampf(float(track_cfg.get("length_px", _track_length_px)), 2000.0, 5000.0)


func _apply_theme() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var bg_color: String = str(theme.get("background_color", "#87CEEB"))
	_background.color = Color.from_string(bg_color, Color(0.53, 0.81, 0.92, 1.0))


func _load_texture(path: String, fallback_color: Color, size: Vector2i) -> Texture2D:
	return ThemeSpriteUtil.load_texture(path, fallback_color, size)


func _setup_world() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var track_path: String = str(theme.get("track_sprite", ""))
	var hurdle_path: String = str(theme.get("hurdle_sprite", ""))
	var track_tex: Texture2D = _load_texture(track_path, Color(0.35, 0.72, 0.35, 1.0), Vector2i(70, 24))
	var hurdle_tex: Texture2D = _load_texture(hurdle_path, Color(0.95, 0.55, 0.15, 1.0), Vector2i(40, 36))
	if _scroll_track.has_method("setup"):
		_scroll_track.call("setup", _current_speed, track_tex)
	var tuning: Dictionary = GameConfig.get_tuning()
	var obstacle_cfg: Dictionary = tuning.get("obstacle", {}) as Dictionary
	var density: float = clampf(float(obstacle_cfg.get("density", 0.4)), 0.3, 1.0)
	var min_gap: float = clampf(float(obstacle_cfg.get("min_gap_px", 200.0)), 120.0, 280.0)
	if _spawner.has_method("setup"):
		_spawner.call("setup", _current_speed, density, min_gap, hurdle_tex)


func _physics_process(delta: float) -> void:
	if _game_over or get_tree().paused:
		return
	SprintBurstSkill.tick(delta)
	if SprintBurstSkill.is_enabled() and Input.is_action_just_pressed("skill"):
		SprintBurstSkill.try_activate()
	_update_speed(delta)
	_elapsed += delta
	var distance_delta: float = _current_speed * delta
	_distance_px += distance_delta
	if _scroll_track.has_method("set_scroll_speed"):
		_scroll_track.call("set_scroll_speed", _current_speed)
	if _spawner.has_method("advance_distance"):
		_spawner.call("advance_distance", delta, distance_delta)
	_update_hud()
	if FinishLineScript.is_reached(_distance_px, _track_length_px):
		_finish_win(FinishLineScript.get_finish_message(_elapsed, get_distance_meters()))
		return
	if _elapsed >= _round_duration:
		_finish_win("时间到！跑了 %dm！" % get_distance_meters())


func _update_speed(delta: float) -> void:
	var target_speed: float = _base_speed
	if Input.is_action_pressed("run"):
		target_speed = _base_speed * _boost_multiplier
	if SprintBurstSkill.is_active():
		target_speed = _base_speed * _boost_multiplier * SprintBurstSkill.get_speed_multiplier()
	_current_speed = lerpf(_current_speed, target_speed, _accel_rate * delta)


func get_distance_meters() -> int:
	return int(_distance_px / 100.0)


func get_time_left() -> float:
	return maxf(0.0, _round_duration - _elapsed)


func get_current_speed() -> float:
	return _current_speed


func _on_hurdle_hit_player() -> void:
	_finish_lose()


func _finish_lose() -> void:
	if _game_over:
		return
	_game_over = true
	if _player.has_method("set_game_over"):
		_player.call("set_game_over", true)
	if _spawner.has_method("set_game_over"):
		_spawner.call("set_game_over", true)
	if _manager != null and _manager.has_method("on_run_lost"):
		_manager.call("on_run_lost", get_distance_meters())


func _finish_win(message: String) -> void:
	if _game_over:
		return
	_game_over = true
	if _player.has_method("set_game_over"):
		_player.call("set_game_over", true)
	if _spawner.has_method("set_game_over"):
		_spawner.call("set_game_over", true)
	if _manager != null and _manager.has_method("on_run_won"):
		_manager.call("on_run_won", message, get_distance_meters())


func _update_hud() -> void:
	if _manager == null or not _manager.has_method("update_run_hud"):
		return
	_manager.call(
		"update_run_hud",
		get_distance_meters(),
		get_time_left(),
		int(_elapsed),
		SprintBurstSkill.is_ready()
	)
