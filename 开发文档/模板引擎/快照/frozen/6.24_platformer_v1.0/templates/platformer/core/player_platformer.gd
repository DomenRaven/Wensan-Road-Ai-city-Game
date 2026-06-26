extends CharacterBody2D

signal died(cause: String)

const COYOTE_TIME_SEC: float = 0.12
const JUMP_BUFFER_SEC: float = 0.15
const FALL_GRAVITY_MULT: float = 1.6
const GROUND_POUND_SPEED: float = 520.0
const GROUND_POUND_BASE_COOLDOWN: float = 1.5
const SpriteFramesUtil := preload("res://core/sprite_frames_util.gd")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")

const PLAYER_HALF_W: float = 10.0
const PLAYER_BODY_H: float = 28.0
const ENEMY_HALF_W: float = 14.0
const ENEMY_BODY_H: float = 24.0
const CONTACT_H_MARGIN: float = 10.0

var _gravity: float = 800.0
var _move_speed: float = 200.0
var _jump_velocity: float = -400.0
var _max_fall_speed: float = 650.0
var _acceleration: float = 1200.0
var _friction: float = 800.0
var _air_control: float = 0.85
var _bounce_on_enemy: float = -300.0
var _invincible_sec: float = 1.5
var _death_y: float = 420.0

var _is_dead: bool = false
var _is_frozen: bool = false
var _is_invincible: bool = false
var _coyote_timer: float = 0.0
var _jump_buffer: float = 999.0
var _facing: int = 1
var _double_jump_used: bool = false
var _ground_pound_cooldown: float = 0.0
var _spawn_position: Vector2 = Vector2.ZERO
var _invincible_tween: Tween = null
var _was_falling_before_move: bool = false
var _stomp_cooldown: float = 0.0

@onready var _sprite: AnimatedSprite2D = $AnimatedSprite2D
@onready var _camera: Camera2D = $Camera2D
@onready var _stomp_area: Area2D = $StompArea
@onready var _hurt_area: Area2D = $HurtArea


func _ready() -> void:
	_spawn_position = global_position
	_apply_tuning()
	_apply_theme()
	_apply_camera_limits()


func configure_from_manager(bounce: float, invincible_sec: float) -> void:
	_bounce_on_enemy = bounce
	_invincible_sec = invincible_sec


func _apply_tuning() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var player_cfg: Dictionary = tuning.get("player", {}) as Dictionary
	var physics_cfg: Dictionary = tuning.get("physics", {}) as Dictionary
	var level_cfg: Dictionary = tuning.get("level", {}) as Dictionary
	var enemy_cfg: Dictionary = tuning.get("enemy", {}) as Dictionary
	_move_speed = float(player_cfg.get("move_speed", _move_speed))
	_jump_velocity = float(player_cfg.get("jump_velocity", _jump_velocity))
	_max_fall_speed = float(player_cfg.get("max_fall_speed", _max_fall_speed))
	_gravity = float(physics_cfg.get("gravity", _gravity))
	_bounce_on_enemy = float(enemy_cfg.get("bounce_on_stomp", _bounce_on_enemy))
	var mult: float = float(level_cfg.get("width_multiplier", 3.0))
	var viewport_w: float = float(get_viewport().get_visible_rect().size.x)
	_death_y = float(level_cfg.get("death_y", 420.0))
	_camera.limit_right = int(viewport_w * mult)


func _apply_theme() -> void:
	SpriteFramesUtil.apply_player_frames(_sprite, GameConfig.get_theme())
	_sprite.centered = true
	_sprite.position = Vector2(0.0, -16.0)


func _apply_camera_limits() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var level_cfg: Dictionary = tuning.get("level", {}) as Dictionary
	var mult: float = float(level_cfg.get("width_multiplier", 3.0))
	var viewport_size: Vector2 = get_viewport().get_visible_rect().size
	_camera.limit_left = 0
	_camera.limit_top = 0
	_camera.limit_right = int(viewport_size.x * mult)
	_camera.limit_bottom = int(viewport_size.y)
	_camera.position = Vector2(120.0, -40.0)
	_camera.position_smoothing_enabled = true
	_camera.position_smoothing_speed = 10.0


func _physics_process(delta: float) -> void:
	if _is_dead or _is_frozen:
		velocity = Vector2.ZERO
		return
	_update_timers(delta)
	_handle_horizontal_move(delta)
	_handle_jump()
	_handle_ground_pound()
	_apply_gravity(delta)
	_was_falling_before_move = velocity.y > 12.0 or not is_on_floor()
	move_and_slide()
	_check_block_hits()
	_check_enemy_contacts()
	_clamp_fall_speed()
	if _stomp_cooldown > 0.0:
		_stomp_cooldown = maxf(0.0, _stomp_cooldown - delta)
	_update_facing()
	_update_animation()
	if global_position.y > _death_y:
		trigger_death("fall")


func _update_timers(delta: float) -> void:
	if is_on_floor():
		_coyote_timer = 0.0
		_double_jump_used = false
	else:
		_coyote_timer += delta
	if _jump_buffer < JUMP_BUFFER_SEC:
		_jump_buffer += delta
	if _ground_pound_cooldown > 0.0:
		_ground_pound_cooldown = maxf(0.0, _ground_pound_cooldown - delta)


func _apply_gravity(delta: float) -> void:
	if is_on_floor() and velocity.y > 0.0:
		velocity.y = 0.0
		return
	var gravity_scale: float = 1.0
	if velocity.y > 0.0:
		gravity_scale = FALL_GRAVITY_MULT
	velocity.y += _gravity * gravity_scale * delta


func _handle_horizontal_move(delta: float) -> void:
	var direction: float = Input.get_action_strength("move_right") - Input.get_action_strength("move_left")
	var target_speed: float = direction * _move_speed
	if is_on_floor():
		if absf(direction) > 0.01:
			velocity.x = move_toward(velocity.x, target_speed, _acceleration * delta)
		else:
			velocity.x = move_toward(velocity.x, 0.0, _friction * delta)
	elif absf(direction) > 0.01:
		velocity.x = move_toward(velocity.x, target_speed, _acceleration * _air_control * delta)


func _handle_jump() -> void:
	if Input.is_action_just_pressed("jump"):
		_jump_buffer = 0.0
	var can_ground_jump: bool = is_on_floor() or _coyote_timer <= COYOTE_TIME_SEC
	var buffered: bool = _jump_buffer <= JUMP_BUFFER_SEC
	if can_ground_jump and buffered:
		velocity.y = _jump_velocity
		_jump_buffer = 999.0
		_coyote_timer = COYOTE_TIME_SEC + 0.01
		ThemeSoundUtil.play(self, "impact", "jump")
		return
	if (
		GameConfig.has_skill("double_jump")
		and not is_on_floor()
		and not _double_jump_used
		and buffered
		and velocity.y <= 0.0
	):
		velocity.y = _jump_velocity
		_double_jump_used = true
		_jump_buffer = 999.0


func _handle_ground_pound() -> void:
	if not GameConfig.has_skill("ground_pound"):
		return
	if _ground_pound_cooldown > 0.0 or is_on_floor():
		return
	if not Input.is_action_just_pressed("jump"):
		return
	if velocity.y <= 0.0:
		return
	velocity.y = GROUND_POUND_SPEED
	var cooldown_scale: float = GameConfig.get_skill_cooldown_scale("ground_pound")
	_ground_pound_cooldown = GROUND_POUND_BASE_COOLDOWN * cooldown_scale


func _check_block_hits() -> void:
	for i: int in range(get_slide_collision_count()):
		var collider: Object = get_slide_collision(i).get_collider()
		if collider != null and collider.has_method("try_hit_from_below"):
			collider.call("try_hit_from_below", self)


func _check_enemy_contacts() -> void:
	if _is_invincible:
		return
	var player_bottom: float = global_position.y
	var enemies: Array[CharacterBody2D] = _gather_touching_enemies()
	for enemy: CharacterBody2D in enemies:
		if _stomp_cooldown <= 0.0 and _try_stomp_enemy(enemy, player_bottom):
			return
		if _is_side_contact(enemy, player_bottom):
			_resolve_enemy_hurt(enemy)
			return


func _gather_touching_enemies() -> Array[CharacterBody2D]:
	var found: Dictionary = {}
	for i: int in range(get_slide_collision_count()):
		var collider: Object = get_slide_collision(i).get_collider()
		if collider is CharacterBody2D and (collider as CharacterBody2D).is_in_group("enemy"):
			found[collider.get_instance_id()] = collider
	for body: Node2D in _stomp_area.get_overlapping_bodies():
		if body is CharacterBody2D and body.is_in_group("enemy"):
			found[body.get_instance_id()] = body
	for body: Node2D in _hurt_area.get_overlapping_bodies():
		if body is CharacterBody2D and body.is_in_group("enemy"):
			found[body.get_instance_id()] = body
	var player_aabb: Rect2 = _get_player_aabb()
	for node: Node in get_tree().get_nodes_in_group("enemy"):
		if not node is CharacterBody2D:
			continue
		var enemy: CharacterBody2D = node as CharacterBody2D
		if _get_enemy_aabb(enemy).intersects(player_aabb):
			found[enemy.get_instance_id()] = enemy
		elif _is_enemy_in_contact_range(enemy):
			found[enemy.get_instance_id()] = enemy
	var result: Array[CharacterBody2D] = []
	for key: int in found.keys():
		result.append(found[key] as CharacterBody2D)
	return result


func _is_enemy_in_contact_range(enemy: CharacterBody2D) -> bool:
	if not enemy.has_method("is_stompable") or not enemy.is_stompable():
		return false
	var half_w: float = _get_enemy_half_w(enemy)
	var body_h: float = _get_enemy_body_h(enemy)
	var dx: float = absf(global_position.x - enemy.global_position.x)
	var max_dx: float = PLAYER_HALF_W + half_w + CONTACT_H_MARGIN
	if dx > max_dx:
		return false
	var player_top: float = global_position.y - PLAYER_BODY_H
	var player_bottom: float = global_position.y
	var enemy_top: float = enemy.global_position.y - body_h
	var enemy_bottom: float = enemy.global_position.y
	return player_top < enemy_bottom + 4.0 and player_bottom > enemy_top - 4.0


func _is_side_contact(enemy: CharacterBody2D, player_bottom: float) -> bool:
	if enemy == null or not enemy.is_in_group("enemy"):
		return false
	if not enemy.has_method("is_stompable") or not enemy.is_stompable():
		return false
	var body_h: float = _get_enemy_body_h(enemy)
	var enemy_stomp_line: float = enemy.global_position.y - body_h * 0.45
	return player_bottom > enemy_stomp_line + 1.0


func _try_stomp_enemy(enemy: CharacterBody2D, player_bottom: float) -> bool:
	if enemy == null or not enemy.is_in_group("enemy"):
		return false
	if not enemy.has_method("is_stompable") or not enemy.is_stompable():
		return false
	var body_h: float = _get_enemy_body_h(enemy)
	var enemy_mid_y: float = enemy.global_position.y - body_h * 0.5
	var feet_in_upper_half: bool = player_bottom <= enemy_mid_y + 2.0
	var is_stomp: bool = feet_in_upper_half and (
		_was_falling_before_move or player_bottom < enemy.global_position.y - 8.0
	)
	if not is_stomp:
		return false
	velocity.y = _bounce_on_enemy
	global_position.y = minf(global_position.y, enemy.global_position.y - body_h - 2.0)
	var killed: bool = false
	if enemy.has_method("on_stomped"):
		killed = enemy.on_stomped()
	if killed:
		var manager: Node = get_tree().get_first_node_in_group("game_manager")
		if manager != null and manager.has_method("on_enemy_stomped"):
			manager.on_enemy_stomped()
	_stomp_cooldown = 0.12
	return true


func _get_enemy_half_w(enemy: CharacterBody2D) -> float:
	if enemy.has_method("get_half_width"):
		return float(enemy.get_half_width())
	return ENEMY_HALF_W


func _get_enemy_body_h(enemy: CharacterBody2D) -> float:
	if enemy.has_method("get_body_height"):
		return float(enemy.get_body_height())
	return ENEMY_BODY_H


func _resolve_enemy_hurt(_enemy: CharacterBody2D) -> void:
	notify_hazard("enemy")


func _get_player_aabb() -> Rect2:
	return Rect2(
		global_position.x - PLAYER_HALF_W,
		global_position.y - PLAYER_BODY_H,
		PLAYER_HALF_W * 2.0,
		PLAYER_BODY_H
	)


func _get_enemy_aabb(enemy: CharacterBody2D) -> Rect2:
	var half_w: float = _get_enemy_half_w(enemy)
	var body_h: float = _get_enemy_body_h(enemy)
	return Rect2(
		enemy.global_position.x - half_w,
		enemy.global_position.y - body_h,
		half_w * 2.0,
		body_h
	)


func _clamp_fall_speed() -> void:
	if velocity.y > 0.0:
		velocity.y = minf(velocity.y, _max_fall_speed)


func _update_facing() -> void:
	if absf(velocity.x) > 5.0:
		_facing = 1 if velocity.x > 0.0 else -1
	_sprite.flip_h = _facing < 0


func _update_animation() -> void:
	if _is_invincible and _sprite.animation == "hit":
		return
	if not is_on_floor():
		_sprite.play("jump" if velocity.y < 0.0 else "fall")
	elif absf(velocity.x) > 10.0:
		_sprite.play("run")
	else:
		_sprite.play("idle")


func trigger_death(cause: String) -> void:
	if _is_dead or _is_invincible:
		return
	_is_dead = true
	velocity = Vector2.ZERO
	_sprite.play("hit")
	set_physics_process(false)
	died.emit(cause)


func notify_hazard(cause: String) -> void:
	if _is_invincible:
		return
	trigger_death(cause)


func respawn_with_invincibility(cause: String) -> void:
	_is_dead = false
	set_physics_process(true)
	if cause == "fall":
		global_position = _spawn_position
	velocity = Vector2.ZERO
	snap_to_floor()
	_coyote_timer = 0.0
	_jump_buffer = 999.0
	_double_jump_used = false
	_start_invincibility()


func _start_invincibility() -> void:
	_is_invincible = true
	if _invincible_tween != null and _invincible_tween.is_valid():
		_invincible_tween.kill()
	_invincible_tween = create_tween()
	_invincible_tween.set_loops(int(_invincible_sec / 0.1))
	_invincible_tween.tween_property(_sprite, "modulate:a", 0.25, 0.05)
	_invincible_tween.tween_property(_sprite, "modulate:a", 1.0, 0.05)
	var timer: SceneTreeTimer = get_tree().create_timer(_invincible_sec)
	timer.timeout.connect(_on_invincibility_done)


func _on_invincibility_done() -> void:
	_is_invincible = false
	_sprite.modulate.a = 1.0


func freeze() -> void:
	_is_frozen = true
	velocity = Vector2.ZERO


func set_spawn_position(pos: Vector2) -> void:
	_spawn_position = pos
	global_position = pos


func snap_to_floor() -> void:
	velocity = Vector2.ZERO
	for _attempt: int in range(24):
		move_and_slide()
		if is_on_floor():
			return
		global_position.y += 1.0
