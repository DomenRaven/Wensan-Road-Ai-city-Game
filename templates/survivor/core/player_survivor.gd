extends Area2D

const SurvivorSpriteUtil := preload("res://core/survivor_sprite_util.gd")
const SurvivorWorld := preload("res://core/survivor_world.gd")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")

signal hp_changed(current_hp: int, max_hp: int)
signal died
signal stats_changed

var _speed: float = 150.0
var _max_hp: int = 100
var _hp: int = 100
var _speed_multiplier: float = 1.0
var _attack_interval_ms: int = 500
var _attack_damage: int = 10
var _multishot_count: int = 1
var _hp_regen: int = 0
var _shoot_angle: float = PI / 2.0
var _invincible_timer: float = 0.0
var _regen_timer: float = 0.0
var _knockback: Vector2 = Vector2.ZERO
var _orb_hit_timer: float = 0.0
var _blink_timer: float = 0.0
var _hit_flash_timer: float = 0.0
var _base_scale: Vector2 = Vector2(1.2, 1.2)

@onready var _sprite: Sprite2D = $Sprite2D
@onready var _hit_particles: CPUParticles2D = $HitParticles


func _ready() -> void:
	add_to_group("player")
	z_index = 10
	monitorable = true
	_apply_tuning()
	_apply_theme()
	_base_scale = _sprite.scale
	hp_changed.emit(_hp, _max_hp)


func _apply_tuning() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var player_cfg: Dictionary = tuning.get("player", {}) as Dictionary
	var weapon_cfg: Dictionary = tuning.get("weapon", {}) as Dictionary
	_speed = float(player_cfg.get("speed", _speed))
	_max_hp = int(player_cfg.get("max_hp", _max_hp))
	_hp = _max_hp
	_attack_interval_ms = int(weapon_cfg.get("interval_ms", _attack_interval_ms))
	_attack_damage = int(weapon_cfg.get("base_damage", _attack_damage))
	_multishot_count = int(weapon_cfg.get("multishot_base", _multishot_count))


func _apply_theme() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var sprite_path: String = str(theme.get("player_sprite", ""))
	SurvivorSpriteUtil.apply_sprite(_sprite, sprite_path, Vector2(1.2, 1.2))
	_base_scale = _sprite.scale


func get_hp() -> int:
	return _hp


func get_max_hp() -> int:
	return _max_hp


func get_shoot_angle() -> float:
	return _shoot_angle


func get_attack_interval_ms() -> int:
	return maxi(200, _attack_interval_ms)


func get_attack_damage() -> int:
	return _attack_damage


func get_multishot_count() -> int:
	return _multishot_count


func get_speed_multiplier() -> float:
	return _speed_multiplier


func get_magnet_multiplier() -> float:
	return 1.0


func apply_level_choice(choice_id: String) -> void:
	match choice_id:
		"attack_speed":
			_attack_interval_ms = maxi(200, int(round(float(_attack_interval_ms) * 0.8)))
		"attack_damage":
			_attack_damage += 5
		"move_speed":
			_speed_multiplier *= 1.1
		"multi_shot":
			_multishot_count += 1
		"max_hp":
			_max_hp += 50
			_hp += 50
			hp_changed.emit(_hp, _max_hp)
		"hp_regen":
			_hp_regen += 1
	stats_changed.emit()


func take_orb_hit(amount: int, source_position: Vector2) -> void:
	if _blink_timer > 0.0 or _orb_hit_timer > 0.0:
		return
	_hp -= amount
	_orb_hit_timer = 0.35
	_invincible_timer = maxf(_invincible_timer, 0.35)
	hp_changed.emit(_hp, _max_hp)
	_play_normal_hit_fx(source_position)
	ThemeSoundUtil.play(self, "impact", "hit")
	if _hp <= 0:
		died.emit()


func take_hit(amount: int, source_position: Vector2 = Vector2.ZERO) -> void:
	if _invincible_timer > 0.0 or _blink_timer > 0.0:
		return
	_hp -= amount
	_invincible_timer = 0.5
	hp_changed.emit(_hp, _max_hp)
	_play_normal_hit_fx(source_position)
	ThemeSoundUtil.play(self, "impact", "hit")
	if _hp <= 0:
		died.emit()


func take_laser_hit(amount: int, source_position: Vector2, laser_direction: Vector2) -> void:
	if _blink_timer > 0.0:
		return
	_hp -= amount
	_invincible_timer = 1.2
	_blink_timer = 1.0
	hp_changed.emit(_hp, _max_hp)
	_play_laser_hit_fx(source_position, laser_direction)
	ThemeSoundUtil.play(self, "impact", "hit")
	if _hp <= 0:
		died.emit()


func _play_normal_hit_fx(source_position: Vector2) -> void:
	_hit_flash_timer = 0.18
	_sprite.modulate = Color(1.0, 0.35, 0.4, 1.0)
	_sprite.scale = _base_scale * 0.88
	_apply_knockback(source_position, 90.0)


func _play_laser_hit_fx(source_position: Vector2, laser_direction: Vector2) -> void:
	_sprite.modulate = Color(1.0, 0.2, 0.15, 1.0)
	var knock_dir: Vector2 = Vector2(-laser_direction.y, laser_direction.x)
	if knock_dir.dot(global_position - source_position) < 0.0:
		knock_dir = -knock_dir
	_apply_knockback(global_position + knock_dir, 220.0)
	_burst_hit_particles(Color(1.0, 0.45, 0.15, 1.0), 24)
	var manager: Node = get_tree().get_first_node_in_group("game_manager")
	if manager != null and manager.has_method("shake_screen"):
		manager.call("shake_screen", 0.55, 10.0)


func _apply_knockback(from_position: Vector2, strength: float) -> void:
	var direction: Vector2 = global_position - from_position
	if direction.length_squared() < 1.0:
		direction = Vector2.UP
	_knockback = direction.normalized() * strength


func _burst_hit_particles(color: Color, amount: int) -> void:
	_hit_particles.amount = amount
	_hit_particles.color = color
	_hit_particles.emitting = false
	_hit_particles.restart()
	_hit_particles.emitting = true


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mouse_event: InputEventMouseButton = event as InputEventMouseButton
		if mouse_event.pressed and mouse_event.button_index == MOUSE_BUTTON_LEFT:
			_update_aim_from_mouse()


func _update_aim_from_mouse() -> void:
	var mouse_pos: Vector2 = get_global_mouse_position()
	var direction: Vector2 = mouse_pos - global_position
	if direction.length_squared() > 4.0:
		_shoot_angle = direction.angle()


func _physics_process(delta: float) -> void:
	var input_dir: Vector2 = Vector2(
		Input.get_action_strength("move_right") - Input.get_action_strength("move_left"),
		Input.get_action_strength("move_down") - Input.get_action_strength("move_up")
	)
	var move_velocity: Vector2 = Vector2.ZERO
	if input_dir.length_squared() > 0.001:
		move_velocity = input_dir.normalized() * _speed * _speed_multiplier
		SurvivorSpriteUtil.apply_facing_flip(_sprite, move_velocity.normalized())
	var total_velocity: Vector2 = move_velocity + _knockback
	if total_velocity.length_squared() > 0.001:
		position += total_velocity * delta
		position = SurvivorWorld.clamp_point(position)
	if _knockback.length_squared() > 0.001:
		_knockback = _knockback.move_toward(Vector2.ZERO, 520.0 * delta)
	if _orb_hit_timer > 0.0:
		_orb_hit_timer = maxf(0.0, _orb_hit_timer - delta)
	_update_invincibility(delta)
	_update_hit_flash(delta)
	_tick_regen(delta)


func _update_hit_flash(delta: float) -> void:
	if _hit_flash_timer <= 0.0:
		if _blink_timer <= 0.0 and _invincible_timer <= 0.0:
			_sprite.scale = _base_scale
		return
	_hit_flash_timer = maxf(0.0, _hit_flash_timer - delta)
	if _hit_flash_timer <= 0.0 and _blink_timer <= 0.0:
		_sprite.modulate = Color(1.0, 1.0, 1.0, 1.0)
		_sprite.scale = _base_scale


func _tick_regen(delta: float) -> void:
	if _hp_regen <= 0:
		return
	_regen_timer += delta
	if _regen_timer < 1.0:
		return
	_regen_timer = 0.0
	_hp = mini(_max_hp, _hp + _hp_regen)
	hp_changed.emit(_hp, _max_hp)


func _update_invincibility(delta: float) -> void:
	if _blink_timer > 0.0:
		_blink_timer = maxf(0.0, _blink_timer - delta)
		var blink_on: bool = int(_blink_timer * 14.0) % 2 == 0
		_sprite.modulate = Color(1.0, 0.45, 0.4, 1.0 if blink_on else 0.25)
		_sprite.scale = _base_scale * (0.92 if blink_on else 1.04)
		if _blink_timer <= 0.0:
			_sprite.modulate = Color(1.0, 1.0, 1.0, 1.0)
			_sprite.scale = _base_scale
		return
	if _invincible_timer <= 0.0:
		if _hit_flash_timer <= 0.0:
			_sprite.modulate = Color(1.0, 1.0, 1.0, 1.0)
		return
	_invincible_timer = maxf(0.0, _invincible_timer - delta)
	if _invincible_timer <= 0.0 and _hit_flash_timer <= 0.0:
		_sprite.modulate = Color(1.0, 1.0, 1.0, 1.0)
