extends CharacterBody2D

signal run_hit_finished

const ObstacleScript := preload("res://core/obstacle.gd")
const SpriteFramesUtil := preload("res://core/sprite_frames_util.gd")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")

const PLAYER_X: float = 100.0
const GROUND_Y: float = 300.0
const DISPLAY_SCALE: float = 2.0
const SLIDE_HEIGHT_RATIO: float = 0.42

var _gravity: float = 1500.0
var _jump_velocity: float = -800.0
var _max_fall_speed: float = 900.0
var _is_sliding: bool = false
var _game_over: bool = false
var _playing: bool = false
var _invincible: bool = false
var _stand_shape_size: Vector2 = Vector2(16, 24)
var _stand_shape_offset: Vector2 = Vector2(0, -12)

var _stand_sprite_offset: Vector2 = Vector2(0, -32)

@onready var _sprite: AnimatedSprite2D = $AnimatedSprite2D
@onready var _collision: CollisionShape2D = $CollisionShape2D
@onready var _stand_shape: RectangleShape2D = $CollisionShape2D.shape as RectangleShape2D


func _ready() -> void:
	_apply_tuning()
	_apply_theme()
	global_position = Vector2(PLAYER_X, GROUND_Y)
	_stand_shape_size = Vector2(16, 24)
	if _stand_shape != null:
		_stand_shape.size = _stand_shape_size


func _apply_tuning() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var jump_cfg: Dictionary = tuning.get("jump", {}) as Dictionary
	var physics_cfg: Dictionary = tuning.get("physics", {}) as Dictionary
	_jump_velocity = float(jump_cfg.get("velocity", _jump_velocity))
	_max_fall_speed = float(jump_cfg.get("max_fall_speed", _max_fall_speed))
	_gravity = float(physics_cfg.get("gravity", _gravity))


func _apply_theme() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	SpriteFramesUtil.apply_player_frames(_sprite, theme)
	_sprite.scale = Vector2(DISPLAY_SCALE, DISPLAY_SCALE)


func set_playing(value: bool) -> void:
	_playing = value
	if value:
		_game_over = false
		_end_slide()
		velocity = Vector2.ZERO
		global_position = Vector2(PLAYER_X, GROUND_Y)
		if _sprite.sprite_frames != null:
			_sprite.play("run")


func set_game_over(value: bool) -> void:
	_game_over = value
	_playing = false
	if value:
		velocity = Vector2.ZERO
		_end_slide()
		_sprite.play("hit")
		if _sprite.sprite_frames == null or not _sprite.sprite_frames.has_animation("hit"):
			run_hit_finished.emit()
		elif not _sprite.animation_finished.is_connected(_on_hit_animation_finished):
			_sprite.animation_finished.connect(_on_hit_animation_finished)
	else:
		_sprite.play("idle")


func set_invincible(active: bool) -> void:
	_invincible = active
	_sprite.modulate.a = 0.5 if active else 1.0


func is_invincible() -> bool:
	return _invincible


func is_sliding() -> bool:
	return _is_sliding


func can_pass_obstacle(kind: int) -> bool:
	if kind == ObstacleScript.ObstacleKind.TALL:
		return not is_on_floor()
	if kind == ObstacleScript.ObstacleKind.LOW:
		return _is_sliding
	return false


func _physics_process(delta: float) -> void:
	if _game_over or not _playing:
		return
	global_position.x = PLAYER_X
	_apply_gravity(delta)
	_handle_input()
	move_and_slide()
	_clamp_fall_speed()
	_snap_to_ground()
	_update_animation()


func _apply_gravity(delta: float) -> void:
	if _is_sliding:
		velocity.y = 0.0
		return
	if is_on_floor() and velocity.y > 0.0:
		velocity.y = 0.0
		return
	velocity.y += _gravity * delta


func _handle_input() -> void:
	if not is_on_floor():
		if _is_sliding:
			_end_slide()
		return
	if _is_sliding:
		if not Input.is_action_pressed("skill"):
			_end_slide()
		return
	if Input.is_action_just_pressed("jump"):
		velocity.y = _jump_velocity
		ThemeSoundUtil.play(self, "impact", "jump")
		return
	if Input.is_action_pressed("skill"):
		_start_slide()


func _start_slide() -> void:
	if _is_sliding:
		return
	_is_sliding = true
	velocity = Vector2.ZERO
	var rect: RectangleShape2D = _collision.shape as RectangleShape2D
	if rect != null:
		var slide_h: float = _stand_shape_size.y * SLIDE_HEIGHT_RATIO
		rect.size = Vector2(_stand_shape_size.x, slide_h)
		_collision.position = Vector2(0, -slide_h * 0.5)
	var slide_scale_y: float = DISPLAY_SCALE * SLIDE_HEIGHT_RATIO
	_sprite.scale = Vector2(DISPLAY_SCALE, slide_scale_y)
	_sprite.position = Vector2(_stand_sprite_offset.x, -16.0 * slide_scale_y)


func _end_slide() -> void:
	if not _is_sliding:
		return
	_is_sliding = false
	var rect: RectangleShape2D = _collision.shape as RectangleShape2D
	if rect != null:
		rect.size = _stand_shape_size
		_collision.position = _stand_shape_offset
	_sprite.scale = Vector2(DISPLAY_SCALE, DISPLAY_SCALE)
	_sprite.position = _stand_sprite_offset


func _clamp_fall_speed() -> void:
	velocity.y = minf(velocity.y, _max_fall_speed)


func _snap_to_ground() -> void:
	if is_on_floor():
		global_position.y = GROUND_Y


func _update_animation() -> void:
	if _game_over:
		return
	if _is_sliding:
		_sprite.play("fall")
	elif not is_on_floor():
		if velocity.y < 0.0:
			_sprite.play("jump")
		else:
			_sprite.play("fall")
	elif _sprite.sprite_frames != null:
		_sprite.play("run")


func _on_hit_animation_finished() -> void:
	if not _game_over:
		return
	if _sprite.animation != "hit":
		return
	run_hit_finished.emit()
