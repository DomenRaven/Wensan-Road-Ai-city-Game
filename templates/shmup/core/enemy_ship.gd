extends Area2D

signal destroyed(enemy: Area2D, score_value: int, drop_rate: float, is_boss: bool)
signal request_fan_shot(origin: Vector2)
signal boss_hp_changed(current_hp: int, max_hp: int)

const ShmupSheetUtil := preload("res://core/shmup_sheet.gd")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")

var _speed: float = 150.0
var _bullet_speed: float = 300.0
var _hp: int = 1
var _max_hp: int = 1
var _shoot_timer: float = 0.0
var _shoot_interval: float = 2.0
var _score_value: int = 10
var _drop_rate: float = 0.3
var _scale_factor: float = 1.0
var _type_id: String = "normal"
var _is_boss: bool = false
var _boss_active: bool = false
var _boss_enter_done: bool = false

@onready var _sprite: Sprite2D = $Sprite2D

var _bullet_pool: Node2D = null
var _boss_tween: Tween = null


func configure(type_id: String, is_boss_spawn: bool = false) -> void:
	_type_id = type_id
	_is_boss = type_id == "boss" or is_boss_spawn
	_apply_type_config(type_id)
	_apply_sprite()
	if _is_boss:
		rotation_degrees = 180.0
		_start_boss_entrance()
		boss_hp_changed.emit(_hp, _max_hp)
	else:
		rotation_degrees = 180.0


func _apply_type_config(type_id: String) -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var types_cfg: Dictionary = tuning.get("enemy_types", {}) as Dictionary
	var data: Dictionary = types_cfg.get(type_id, {}) as Dictionary
	var enemy_cfg: Dictionary = tuning.get("enemy", {}) as Dictionary
	_speed = float(data.get("speed", enemy_cfg.get("speed", _speed)))
	_bullet_speed = float(enemy_cfg.get("bullet_speed", _bullet_speed))
	_hp = int(data.get("hp", 1))
	_max_hp = _hp
	_score_value = int(data.get("score", _score_value))
	_drop_rate = float(data.get("drop_rate", _drop_rate))
	_scale_factor = float(data.get("scale", 1.0))
	var fire_ms: int = int(data.get("fire_rate_ms", 0))
	_shoot_interval = float(fire_ms) / 1000.0 if fire_ms > 0 else 0.0


func _apply_sprite() -> void:
	var sprite: Sprite2D = _get_sprite()
	if sprite == null:
		return
	var tuning: Dictionary = GameConfig.get_tuning()
	var types_cfg: Dictionary = tuning.get("enemy_types", {}) as Dictionary
	var data: Dictionary = types_cfg.get(_type_id, {}) as Dictionary
	var frame_index: int = int(data.get("frame", 9))
	ShmupSheetUtil.apply_ship_sprite(sprite, frame_index, _scale_factor)


func _get_sprite() -> Sprite2D:
	if _sprite != null:
		return _sprite
	return get_node_or_null("Sprite2D") as Sprite2D


func _start_boss_entrance() -> void:
	_boss_active = true
	_boss_enter_done = false
	if _boss_tween != null and _boss_tween.is_valid():
		_boss_tween.kill()
	_boss_tween = create_tween()
	_boss_tween.tween_property(self, "position:y", 150.0, 2.0).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_boss_tween.tween_callback(_start_boss_patrol)


func _start_boss_patrol() -> void:
	if not is_inside_tree():
		return
	_boss_enter_done = true
	if _boss_tween != null and _boss_tween.is_valid():
		_boss_tween.kill()
	_boss_tween = create_tween().set_loops()
	_boss_tween.tween_property(self, "position:x", 100.0, 3.0).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_boss_tween.tween_property(self, "position:x", 540.0, 3.0).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)


func _physics_process(delta: float) -> void:
	if _is_boss:
		if _boss_enter_done:
			_handle_boss_shooting(delta)
		return
	position.y += _speed * delta
	_shoot_timer += delta
	if _shoot_interval > 0.0 and _shoot_timer >= _shoot_interval:
		_shoot_timer = 0.0
		_fire_at_player()
	if global_position.y > 400.0:
		queue_free()


func _handle_boss_shooting(delta: float) -> void:
	_shoot_timer += delta
	if _shoot_timer < _shoot_interval:
		return
	_shoot_timer = 0.0
	request_fan_shot.emit(global_position)


func take_damage(amount: int) -> void:
	_hp -= amount
	if _is_boss:
		boss_hp_changed.emit(maxi(0, _hp), _max_hp)
	var sprite: Sprite2D = _get_sprite()
	if sprite != null:
		sprite.modulate = Color(1.5, 1.5, 1.5, 1.0)
		var tween: Tween = create_tween()
		tween.tween_property(sprite, "modulate", Color.WHITE, 0.05)
	if _hp > 0:
		return
	ThemeSoundUtil.play(self, "impact", "explode")
	destroyed.emit(self, _score_value, _drop_rate, _is_boss)
	if _boss_tween != null and _boss_tween.is_valid():
		_boss_tween.kill()
	queue_free()


func is_boss() -> bool:
	return _is_boss


func _fire_at_player() -> void:
	var pool: Node2D = _get_bullet_pool()
	if pool == null:
		return
	var muzzle: Vector2 = global_position + Vector2(0.0, 20.0)
	var direction: Vector2 = _compute_launch_direction(muzzle)
	if pool.has_method("spawn_enemy_bullet"):
		pool.call("spawn_enemy_bullet", muzzle, direction, _bullet_speed)


func _compute_launch_direction(muzzle: Vector2) -> Vector2:
	var tuning: Dictionary = GameConfig.get_tuning()
	var enemy_cfg: Dictionary = tuning.get("enemy", {}) as Dictionary
	var cone_deg: float = float(enemy_cfg.get("aim_cone_deg", 120.0))
	var half_cone: float = deg_to_rad(cone_deg * 0.5)
	var player: Node2D = get_tree().get_first_node_in_group("player") as Node2D
	if player == null:
		return Vector2.DOWN
	var to_player: Vector2 = player.global_position - muzzle
	if to_player.length_squared() < 1.0:
		return Vector2.DOWN
	var desired: Vector2 = to_player.normalized()
	var angle_diff: float = Vector2.DOWN.angle_to(desired)
	angle_diff = clampf(angle_diff, -half_cone, half_cone)
	return Vector2.DOWN.rotated(angle_diff)


func _get_bullet_pool() -> Node2D:
	if _bullet_pool == null:
		_bullet_pool = get_tree().get_first_node_in_group("bullet_pool") as Node2D
	return _bullet_pool


func _on_area_entered(area: Area2D) -> void:
	if area.is_in_group("player"):
		if area.has_method("hit_by_enemy_body"):
			area.call("hit_by_enemy_body", self)
