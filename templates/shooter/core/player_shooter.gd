extends Area2D

const DashSkill = preload("res://core/skills/dash.gd")
const ShieldSkill = preload("res://core/skills/shield_burst.gd")
const SpreadSkill = preload("res://core/skills/spread_shot.gd")
const ScreenWrapUtil = preload("res://core/screen_wrap.gd")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")

signal hp_changed(current_hp: int, max_hp: int)
signal died

const SMOOTH_FACTOR: float = 0.15
const INVINCIBLE_MS: int = 800
const FIRE_DIRECTION: Vector2 = Vector2.UP

var _speed: float = 280.0
var _bullet_interval_ms: int = 180
var _bullet_speed: float = 520.0
var _max_hp: int = 3
var _hp: int = 3
var _velocity: Vector2 = Vector2.ZERO
var _fire_timer: float = 0.0
var _invincible_timer: float = 0.0
var _last_move_direction: Vector2 = Vector2.UP

@onready var _sprite: Sprite2D = $Sprite2D
@onready var _shield_ring: Sprite2D = $ShieldRing
@onready var _bullet_pool: Node2D = get_tree().get_first_node_in_group("bullet_pool")


func _ready() -> void:
	_apply_tuning()
	_apply_theme()
	_shield_ring.visible = false
	hp_changed.emit(_hp, _max_hp)


func _apply_tuning() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var player_cfg: Dictionary = tuning.get("player", {}) as Dictionary
	var bullet_cfg: Dictionary = tuning.get("bullet", {}) as Dictionary
	_speed = float(player_cfg.get("speed", _speed))
	_bullet_interval_ms = int(bullet_cfg.get("interval_ms", _bullet_interval_ms))
	_bullet_speed = float(bullet_cfg.get("speed", _bullet_speed))
	_max_hp = int(player_cfg.get("max_hp", _max_hp))
	_hp = _max_hp


func _apply_theme() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var sprite_path: String = str(theme.get("player_sprite", ""))
	if sprite_path != "" and ResourceLoader.exists(sprite_path):
		_sprite.texture = load(sprite_path) as Texture2D
	else:
		_sprite.modulate = Color(0.35, 0.75, 1.0, 1.0)
	_sprite.scale = Vector2(0.55, 0.55)


func _physics_process(delta: float) -> void:
	DashSkill.tick(delta)
	ShieldSkill.tick(delta)
	SpreadSkill.tick(delta)
	_handle_movement(delta)
	_handle_skills()
	_handle_shooting(delta)
	_update_invincibility(delta)
	_update_shield_visual()


func _handle_movement(delta: float) -> void:
	var direction: Vector2 = Vector2(
		Input.get_action_strength("move_right") - Input.get_action_strength("move_left"),
		Input.get_action_strength("move_down") - Input.get_action_strength("move_up")
	)
	if direction.length_squared() > 1.0:
		direction = direction.normalized()
	if direction.length_squared() > 0.01:
		_last_move_direction = direction
	var target_velocity: Vector2 = direction * _speed
	if DashSkill.is_active():
		target_velocity = DashSkill.get_dash_velocity(_speed)
	var blend: float = 1.0 - pow(1.0 - SMOOTH_FACTOR, delta * 60.0)
	_velocity = _velocity.lerp(target_velocity, blend)
	position += _velocity * delta
	position = ScreenWrapUtil.wrap(position)


func _handle_skills() -> void:
	if not Input.is_action_just_pressed("skill"):
		return
	if DashSkill.is_enabled() and DashSkill.try_activate(_last_move_direction):
		return
	if ShieldSkill.is_enabled():
		ShieldSkill.try_activate()


func _handle_shooting(delta: float) -> void:
	if not Input.is_action_pressed("shoot"):
		return
	_fire_timer += delta
	var interval_sec: float = float(_bullet_interval_ms) / 1000.0
	if _fire_timer < interval_sec:
		return
	_fire_timer = 0.0
	if SpreadSkill.can_fire_spread():
		SpreadSkill.consume_spread()
		for angle_deg: float in SpreadSkill.get_angles():
			_fire_bullet(angle_deg)
	else:
		_fire_bullet(0.0)


func _fire_bullet(angle_deg: float) -> void:
	if _bullet_pool == null:
		return
	var radians: float = deg_to_rad(angle_deg)
	var dir: Vector2 = FIRE_DIRECTION.rotated(radians)
	var muzzle: Vector2 = global_position + dir * 24.0
	if _bullet_pool.has_method("spawn_player_bullet"):
		_bullet_pool.call("spawn_player_bullet", muzzle, dir, _bullet_speed)
	ThemeSoundUtil.play(self, "impact", "shoot")


func _update_invincibility(delta: float) -> void:
	if ShieldSkill.is_active():
		_sprite.modulate = Color(0.6, 1.0, 1.0, 1.0)
		return
	if _invincible_timer <= 0.0:
		_sprite.modulate = Color(1.0, 1.0, 1.0, 1.0)
		return
	_invincible_timer = maxf(0.0, _invincible_timer - delta)
	var blink: bool = fmod(_invincible_timer, 0.16) < 0.08
	_sprite.modulate = Color(1.0, 1.0, 1.0, 0.45 if blink else 1.0)


func _update_shield_visual() -> void:
	_shield_ring.visible = ShieldSkill.is_active()


func take_hit() -> void:
	if _invincible_timer > 0.0 or ShieldSkill.is_active():
		return
	ThemeSoundUtil.play(self, "impact", "hurt")
	_hp -= 1
	_invincible_timer = float(INVINCIBLE_MS) / 1000.0
	hp_changed.emit(_hp, _max_hp)
	if _hp <= 0:
		died.emit()


func _on_area_entered(area: Area2D) -> void:
	if area.is_in_group("enemy"):
		take_hit()
