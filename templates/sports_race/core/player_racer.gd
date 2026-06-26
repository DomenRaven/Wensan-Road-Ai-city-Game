extends CharacterBody2D

const ThemeSpriteUtil := preload("res://core/theme_sprite.gd")
const HighJumpSkill := preload("res://core/skills/high_jump.gd")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")
const COYOTE_TIME_SEC: float = 0.1
const JUMP_BUFFER_SEC: float = 0.12
const FALL_GRAVITY_MULT: float = 1.6
const LOW_JUMP_MULT: float = 0.55
const PLAYER_X: float = 120.0
const GROUND_Y: float = 300.0
const HURDLE_CLEAR_HEIGHT: float = 24.0

var _gravity: float = 980.0
var _jump_velocity: float = -420.0
var _max_fall_speed: float = 520.0
var _coyote_timer: float = 0.0
var _jump_buffer: float = 999.0
var _game_over: bool = false
var _was_in_air: bool = false

@onready var _sprite: Sprite2D = $Sprite2D


func _ready() -> void:
	_apply_tuning()
	_apply_theme()
	global_position = Vector2(PLAYER_X, GROUND_Y)


func _apply_tuning() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var jump_cfg: Dictionary = tuning.get("jump", {}) as Dictionary
	var physics_cfg: Dictionary = tuning.get("physics", {}) as Dictionary
	_jump_velocity = float(jump_cfg.get("velocity", _jump_velocity))
	_max_fall_speed = float(jump_cfg.get("max_fall_speed", _max_fall_speed))
	_gravity = float(physics_cfg.get("gravity", jump_cfg.get("gravity", _gravity)))


func _apply_theme() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var sprite_path: String = str(theme.get("player_sprite", ""))
	ThemeSpriteUtil.apply_to_sprite(_sprite, sprite_path, Color(0.2, 0.55, 0.95, 1.0))


func set_game_over(value: bool) -> void:
	_game_over = value
	if value:
		velocity = Vector2.ZERO


func is_clearing_hurdle() -> bool:
	return not is_on_floor() and global_position.y < GROUND_Y - HURDLE_CLEAR_HEIGHT


func _physics_process(delta: float) -> void:
	if _game_over:
		return
	global_position.x = PLAYER_X
	_update_timers(delta)
	_apply_gravity(delta)
	_handle_jump()
	move_and_slide()
	_clamp_fall_speed()
	_handle_land_sound()
	_snap_to_ground()


func _update_timers(delta: float) -> void:
	if is_on_floor():
		_coyote_timer = 0.0
	else:
		_coyote_timer += delta
	if _jump_buffer < JUMP_BUFFER_SEC:
		_jump_buffer += delta


func _apply_gravity(delta: float) -> void:
	if is_on_floor() and velocity.y > 0.0:
		velocity.y = 0.0
		return
	var gravity_scale: float = 1.0
	if velocity.y > 0.0:
		gravity_scale = FALL_GRAVITY_MULT
	elif velocity.y < 0.0 and not Input.is_action_pressed("jump"):
		gravity_scale = LOW_JUMP_MULT
	velocity.y += _gravity * gravity_scale * delta


func _handle_jump() -> void:
	if Input.is_action_just_pressed("jump"):
		_jump_buffer = 0.0
	var can_ground_jump: bool = is_on_floor() or _coyote_timer <= COYOTE_TIME_SEC
	var buffered: bool = _jump_buffer <= JUMP_BUFFER_SEC
	if can_ground_jump and buffered:
		velocity.y = HighJumpSkill.apply_velocity(_jump_velocity)
		_jump_buffer = 999.0
		_coyote_timer = COYOTE_TIME_SEC + 0.01
		ThemeSoundUtil.play(self, "impact", "jump")


func _handle_land_sound() -> void:
	if _was_in_air and is_on_floor():
		ThemeSoundUtil.play(self, "impact", "land")
	_was_in_air = not is_on_floor()


func _clamp_fall_speed() -> void:
	velocity.y = minf(velocity.y, _max_fall_speed)


func _snap_to_ground() -> void:
	if is_on_floor():
		global_position.y = GROUND_Y
