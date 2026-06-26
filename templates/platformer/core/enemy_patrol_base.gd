extends CharacterBody2D

## 巡逻敌人基类：绿/紫/橙小怪共享移动、踩头与尺寸接口
const STUCK_MOVE_EPS: float = 0.35
const BODY_HALF_W: float = 14.0
const BODY_H: float = 24.0
const ThemeSpriteUtil := preload("res://core/theme_sprite.gd")

var _patrol_speed: float = 50.0
var _gravity: float = 800.0
var _direction: int = -1
var _alive: bool = true
var _floor_top_y: float = 328.0
var _movement_paused: bool = false

@onready var _sprite: Sprite2D = $Sprite2D


func _ready() -> void:
	add_to_group("enemy")
	_apply_tuning()
	_apply_enemy_theme()
	if randi() % 2 == 0:
		_direction = 1


func configure_spawn(floor_top_y: float, direction: int = 0) -> void:
	_floor_top_y = floor_top_y
	if direction != 0:
		_direction = direction


func get_half_width() -> float:
	return BODY_HALF_W


func get_body_height() -> float:
	return BODY_H


func is_stompable() -> bool:
	return _alive


func _get_enemy_color() -> Color:
	return Color(0.0, 0.667, 0.0, 1.0)


func _apply_tuning() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var enemy_cfg: Dictionary = tuning.get("enemy", {}) as Dictionary
	var physics_cfg: Dictionary = tuning.get("physics", {}) as Dictionary
	var level_cfg: Dictionary = tuning.get("level", {}) as Dictionary
	_patrol_speed = float(enemy_cfg.get("patrol_speed", _patrol_speed))
	_gravity = float(physics_cfg.get("gravity", _gravity))
	_floor_top_y = float(level_cfg.get("floor_y", _floor_top_y))


func _apply_enemy_theme() -> void:
	_sprite.texture = ThemeSpriteUtil.load_texture("", _get_enemy_color(), Vector2i(32, 32))
	_sprite.centered = true
	_sprite.position = Vector2(0.0, -16.0)


func snap_to_floor() -> void:
	velocity = Vector2.ZERO
	global_position.y = _floor_top_y
	for _attempt: int in range(20):
		move_and_slide()
		if is_on_floor():
			return
		global_position.y -= 1.0
	for _attempt: int in range(12):
		global_position.y += 1.0
		move_and_slide()
		if is_on_floor():
			return


func _physics_process(delta: float) -> void:
	if not _alive or _movement_paused:
		return
	_patrol_move(delta)


func _patrol_move(delta: float) -> void:
	var prev_x: float = global_position.x
	velocity.x = float(_direction) * _patrol_speed
	if not is_on_floor():
		velocity.y += _gravity * delta
	elif velocity.y > 0.0:
		velocity.y = 0.0
	move_and_slide()
	if is_on_wall():
		_bounce_from_wall()
	else:
		for i: int in range(get_slide_collision_count()):
			var collider: Object = get_slide_collision(i).get_collider()
			if collider is StaticBody2D:
				var n: Vector2 = get_slide_collision(i).get_normal()
				if absf(n.x) > 0.5:
					_bounce_from_wall()
					break
	var moved_x: float = absf(global_position.x - prev_x)
	if absf(velocity.x) > 8.0 and moved_x < STUCK_MOVE_EPS:
		_bounce_from_wall()
	_sprite.flip_h = _direction < 0


func _bounce_from_wall() -> void:
	_direction *= -1
	velocity.x = float(_direction) * _patrol_speed
	global_position.x += float(_direction) * 3.0


func on_stomped() -> bool:
	if not _alive:
		return false
	_kill_enemy()
	return true


func _kill_enemy() -> void:
	_alive = false
	collision_layer = 0
	collision_mask = 0
	velocity = Vector2.ZERO
	set_physics_process(false)
	var tween: Tween = create_tween()
	tween.tween_property(_sprite, "scale", Vector2(1.2, 0.4), 0.08)
	tween.tween_property(_sprite, "modulate:a", 0.0, 0.15)
	tween.tween_callback(queue_free)


func _pause_movement(duration_sec: float) -> void:
	_movement_paused = true
	velocity = Vector2.ZERO
	var timer: SceneTreeTimer = get_tree().create_timer(duration_sec)
	timer.timeout.connect(_on_movement_pause_done)


func _on_movement_pause_done() -> void:
	_movement_paused = false
	_sprite.modulate = Color.WHITE
