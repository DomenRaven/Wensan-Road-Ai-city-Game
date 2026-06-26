extends Node2D

const ThemeSpriteUtil := preload("res://core/theme_sprite.gd")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")
const RacingViewportScript := preload("res://core/racing_viewport.gd")

var _max_speed: float = 800.0
var _acceleration: float = 300.0
var _friction: float = 200.0
var _turn_speed: float = 300.0
var _track_left: float = 50.0
var _track_right: float = 490.0
var _sprite_scale: float = 0.14
var _hit_cooldown_ms: int = 500
var _npc_hit_severity: float = 0.4
var _obstacle_hit_severity: float = 0.1
var _off_track_severity: float = 0.7
var _current_speed: float = 0.0
var _game_over: bool = false
var _is_playing: bool = false
var _last_hit_ms: int = 0
var _base_x: float = 270.0

@onready var _sprite: Sprite2D = $Sprite2D
@onready var _hit_area: Area2D = $HitArea


func _ready() -> void:
	add_to_group("player")
	_apply_tuning()
	_apply_theme()
	reset_run()
	_hit_area.area_entered.connect(_on_area_entered)


func _apply_tuning() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var car_cfg: Dictionary = tuning.get("car", {}) as Dictionary
	var track_cfg: Dictionary = tuning.get("track", {}) as Dictionary
	_max_speed = clampf(float(car_cfg.get("max_speed", _max_speed)), 560.0, 1040.0)
	_acceleration = clampf(float(car_cfg.get("acceleration", _acceleration)), 210.0, 390.0)
	_friction = clampf(float(car_cfg.get("friction", _friction)), 140.0, 260.0)
	_turn_speed = clampf(float(car_cfg.get("turn_speed", _turn_speed)), 210.0, 390.0)
	_sprite_scale = clampf(float(car_cfg.get("sprite_scale", _sprite_scale)), 0.1, 0.2)
	_hit_cooldown_ms = int(car_cfg.get("hit_cooldown_ms", _hit_cooldown_ms))
	_npc_hit_severity = clampf(float(car_cfg.get("npc_hit_severity", _npc_hit_severity)), 0.2, 0.6)
	_obstacle_hit_severity = clampf(float(car_cfg.get("obstacle_hit_severity", _obstacle_hit_severity)), 0.05, 0.2)
	_off_track_severity = clampf(float(car_cfg.get("off_track_severity", _off_track_severity)), 0.5, 0.85)
	var margin: float = float(track_cfg.get("margin_px", 50.0))
	_track_left = margin
	_track_right = RacingViewportScript.track_right(margin)
	_base_x = RacingViewportScript.center_x()


func _apply_theme() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var sprite_path: String = str(theme.get("player_sprite", ""))
	ThemeSpriteUtil.apply_to_sprite(_sprite, sprite_path, Color(0.9, 0.2, 0.2, 1.0))
	_sprite.scale = Vector2(_sprite_scale, _sprite_scale)


func setup_playing(active: bool) -> void:
	_is_playing = active
	if active:
		reset_run()
	else:
		_current_speed = 0.0


func reset_run() -> void:
	_current_speed = 0.0
	_game_over = false
	_last_hit_ms = 0
	global_position = Vector2(_base_x, RacingViewportScript.player_y())
	_sprite.rotation_degrees = 0.0
	_sprite.scale = Vector2(_sprite_scale, _sprite_scale)


func set_game_over(value: bool) -> void:
	_game_over = value
	_is_playing = not value
	if value:
		_current_speed = 0.0


func get_forward_speed() -> float:
	if not _is_playing or _game_over:
		return 0.0
	return _current_speed


func get_track_bounds() -> Vector2:
	return Vector2(_track_left, _track_right)


func trigger_hit(severity: float) -> void:
	if not _is_playing or _game_over:
		return
	var now_ms: int = Time.get_ticks_msec()
	if now_ms - _last_hit_ms < _hit_cooldown_ms:
		return
	_last_hit_ms = now_ms
	_current_speed *= severity
	ThemeSoundUtil.play(self, "impact", "crash")
	var shrink: float = _sprite_scale * 0.85
	var tween: Tween = create_tween()
	tween.tween_property(_sprite, "scale", Vector2(shrink, shrink), 0.1)
	tween.tween_property(_sprite, "scale", Vector2(_sprite_scale, _sprite_scale), 0.1)
	var shake: Tween = create_tween()
	var origin_x: float = position.x
	for _i: int in 3:
		shake.tween_property(self, "position:x", origin_x + randf_range(-15.0, 15.0), 0.05)
		shake.tween_property(self, "position:x", origin_x, 0.05)


func _process(delta: float) -> void:
	if not _is_playing or _game_over:
		return
	if Input.is_action_pressed("skill"):
		_current_speed += _acceleration * delta
	else:
		_current_speed -= _friction * delta
	_current_speed = clampf(_current_speed, 0.0, _max_speed)
	var vx: float = 0.0
	if _current_speed > 0.0:
		if Input.is_action_pressed("steer_left"):
			vx = -_turn_speed
			_sprite.rotation_degrees = -5.0
		elif Input.is_action_pressed("steer_right"):
			vx = _turn_speed
			_sprite.rotation_degrees = 5.0
		else:
			_sprite.rotation_degrees = 0.0
	else:
		_sprite.rotation_degrees = 0.0
	position.x += vx * delta
	var half_width: float = 22.0
	if position.x < _track_left + half_width:
		position.x = _track_left + half_width
		trigger_hit(_off_track_severity)
	elif position.x > _track_right - half_width:
		position.x = _track_right - half_width
		trigger_hit(_off_track_severity)


func _on_area_entered(area: Area2D) -> void:
	if not _is_playing or _game_over:
		return
	if area.is_in_group("npc_car"):
		trigger_hit(_npc_hit_severity)
	elif area.is_in_group("road_obstacle"):
		trigger_hit(_obstacle_hit_severity)
		if is_instance_valid(area):
			area.queue_free()
