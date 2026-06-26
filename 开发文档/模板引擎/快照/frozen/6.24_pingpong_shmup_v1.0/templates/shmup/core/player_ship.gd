extends Area2D

const ShmupSheetUtil := preload("res://core/shmup_sheet.gd")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")

signal hp_changed(current_hp: int, max_hp: int)
signal died

const INVINCIBLE_SEC: float = 0.8
const FOLLOW_LERP: float = 0.3

var _speed: float = 300.0
var _bullet_interval_ms: int = 200
var _bullet_speed: float = 500.0
var _max_hp: int = 3
var _hp: int = 3
var _fire_timer: float = 0.0
var _invincible_timer: float = 0.0
var _target_x: float = 320.0
var _fixed_y: float = 300.0

var _has_shield: bool = false
var _is_double_shot: bool = false
var _has_fire_rate_up: bool = false
var _powerup_duration: float = 15.0
var _double_shot_timer: float = 0.0
var _fire_rate_timer: float = 0.0
var _playing: bool = false

@onready var _sprite: Sprite2D = $Sprite2D
@onready var _shield_sprite: Sprite2D = $ShieldSprite

var _bullet_pool: Node2D = null


func _ready() -> void:
	_apply_tuning()
	_apply_theme()
	_target_x = position.x
	_fixed_y = position.y
	_shield_sprite.visible = false
	ShmupSheetUtil.apply_tile_sprite(_shield_sprite, 13, 2.0)
	hp_changed.emit(_hp, _max_hp)


func set_playing(active: bool) -> void:
	_playing = active


func _apply_tuning() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var player_cfg: Dictionary = tuning.get("player", {}) as Dictionary
	var power_cfg: Dictionary = tuning.get("powerup", {}) as Dictionary
	_speed = float(player_cfg.get("speed", _speed))
	_bullet_interval_ms = int(player_cfg.get("bullet_interval_ms", _bullet_interval_ms))
	_bullet_speed = float(player_cfg.get("bullet_speed", _bullet_speed))
	_max_hp = int(player_cfg.get("max_hp", _max_hp))
	_hp = _max_hp
	_powerup_duration = float(power_cfg.get("duration_sec", _powerup_duration))


func _apply_theme() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var types_cfg: Dictionary = tuning.get("enemy_types", {}) as Dictionary
	var player_data: Dictionary = types_cfg.get("player", {}) as Dictionary
	var frame_index: int = int(player_data.get("frame", 4))
	ShmupSheetUtil.apply_ship_sprite(_sprite, frame_index, 1.0)


func _physics_process(delta: float) -> void:
	if not _playing:
		return
	_update_powerup_timers(delta)
	_handle_movement(delta)
	_handle_auto_shoot(delta)
	_update_invincibility(delta)
	_sync_shield_position()


func _update_powerup_timers(delta: float) -> void:
	if _double_shot_timer > 0.0:
		_double_shot_timer = maxf(0.0, _double_shot_timer - delta)
		if _double_shot_timer <= 0.0:
			_is_double_shot = false
	if _fire_rate_timer > 0.0:
		_fire_rate_timer = maxf(0.0, _fire_rate_timer - delta)
		if _fire_rate_timer <= 0.0:
			_has_fire_rate_up = false


func _handle_movement(delta: float) -> void:
	if Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
		_target_x = get_global_mouse_position().x
	elif Input.is_action_pressed("move_left") or Input.is_action_pressed("move_right"):
		var dir: float = Input.get_action_strength("move_right") - Input.get_action_strength("move_left")
		_target_x += dir * _speed * delta
	_target_x = clampf(_target_x, 32.0, 608.0)
	position.x = lerpf(position.x, _target_x, FOLLOW_LERP)
	position.y = _fixed_y


func _handle_auto_shoot(delta: float) -> void:
	_fire_timer += delta
	var interval_ms: int = _bullet_interval_ms
	if _has_fire_rate_up:
		interval_ms = maxi(50, int(float(interval_ms) * 0.5))
	var interval_sec: float = float(interval_ms) / 1000.0
	if _fire_timer < interval_sec:
		return
	_fire_timer = 0.0
	if _is_double_shot:
		_fire_bullet(-15.0)
		_fire_bullet(15.0)
	else:
		_fire_bullet(0.0)


func _fire_bullet(x_offset: float) -> void:
	var pool: Node2D = _get_bullet_pool()
	if pool == null:
		return
	var muzzle: Vector2 = global_position + Vector2(x_offset, -20.0)
	if pool.has_method("spawn_player_bullet"):
		pool.call("spawn_player_bullet", muzzle, _bullet_speed, false)
	ThemeSoundUtil.play(self, "impact", "shoot")


func _get_bullet_pool() -> Node2D:
	if _bullet_pool != null:
		return _bullet_pool
	_bullet_pool = get_tree().get_first_node_in_group("bullet_pool") as Node2D
	return _bullet_pool


func _update_invincibility(delta: float) -> void:
	if _invincible_timer <= 0.0:
		_sprite.modulate = Color.WHITE
		return
	_invincible_timer = maxf(0.0, _invincible_timer - delta)
	var blink: bool = fmod(_invincible_timer, 0.16) < 0.08
	_sprite.modulate = Color(1.0, 1.0, 1.0, 0.45 if blink else 1.0)


func _sync_shield_position() -> void:
	if _has_shield:
		_shield_sprite.global_position = global_position


func apply_powerup(powerup_name: String) -> void:
	ThemeSoundUtil.play(self, "interface", "confirm")
	match powerup_name:
		"fireRate":
			_has_fire_rate_up = true
			_fire_rate_timer = _powerup_duration
		"doubleShot":
			_is_double_shot = true
			_double_shot_timer = _powerup_duration
		"shield":
			_has_shield = true
			_shield_sprite.visible = true


func _consume_shield() -> bool:
	if not _has_shield:
		return false
	_has_shield = false
	_shield_sprite.visible = false
	ThemeSoundUtil.play(self, "impact", "explode")
	return true


func take_hit() -> void:
	if _invincible_timer > 0.0:
		return
	if _consume_shield():
		return
	_hp -= 1
	_invincible_timer = INVINCIBLE_SEC
	hp_changed.emit(_hp, _max_hp)
	if _hp <= 0:
		died.emit()


func hit_by_enemy_body(enemy: Area2D) -> void:
	if _consume_shield():
		if enemy.has_method("take_damage") and not enemy.call("is_boss"):
			enemy.call("take_damage", 999)
		return
	take_hit()
	if enemy.has_method("is_boss") and bool(enemy.call("is_boss")):
		return
	if enemy.has_method("take_damage"):
		enemy.call("take_damage", 999)


func _on_area_entered(area: Area2D) -> void:
	if area.is_in_group("enemy"):
		hit_by_enemy_body(area)
