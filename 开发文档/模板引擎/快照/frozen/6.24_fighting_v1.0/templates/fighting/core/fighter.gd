extends CharacterBody2D

const WarriorAnimUtil := preload("res://core/warrior_anim_util.gd")
const FightConstants := preload("res://core/fight_constants.gd")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")

enum ActionState {
	IDLE,
	WALK,
	DASH,
	ATTACK1,
	ATTACK2,
	ULTIMATE,
	BLOCK,
	HURT,
	DEAD,
}

signal state_finished
signal hit_connected(attacker: Node, defender: Node, move_id: String)

var warrior_id: String = "Warrior_2"
var is_player_one: bool = true
var action_state: ActionState = ActionState.IDLE
var facing: int = 1

var opponent: CharacterBody2D = null
var arena: Node = null
var round_active: bool = true
var combat_frozen: bool = false

var _arena_width: float = 640.0
var _floor_y: float = 300.0
var _has_hit_this_attack: bool = false
var _dash_direction: int = 0
var _dash_timer: float = 0.0
var _last_dash_time_ms: int = 0
var _last_left_press_ms: int = 0
var _last_right_press_ms: int = 0
var _knockback_tween: Tween = null

@onready var _sprite: AnimatedSprite2D = $AnimatedSprite2D


func _sprite_node() -> AnimatedSprite2D:
	if _sprite != null:
		return _sprite
	return get_node_or_null("AnimatedSprite2D") as AnimatedSprite2D


func _ready() -> void:
	var sprite: AnimatedSprite2D = _sprite_node()
	if sprite == null:
		return
	sprite.animation_finished.connect(_on_animation_finished)
	sprite.frame_changed.connect(_on_frame_changed)


func configure(
	p_warrior_id: String,
	p_is_player_one: bool,
	spawn_x: float,
	spawn_facing: int,
	p_arena_width: float,
	p_floor_y: float
) -> void:
	warrior_id = p_warrior_id
	is_player_one = p_is_player_one
	facing = spawn_facing
	_arena_width = p_arena_width
	_floor_y = p_floor_y
	global_position = Vector2(spawn_x, _floor_y)
	_apply_animations()
	_align_sprite_to_floor()
	_set_state(ActionState.IDLE)


func get_sprite_global_position() -> Vector2:
	var sprite: AnimatedSprite2D = _sprite_node()
	if sprite != null:
		return sprite.global_position
	return global_position


func _align_sprite_to_floor() -> void:
	var sprite: AnimatedSprite2D = _sprite_node()
	if sprite == null:
		return
	sprite.position = Vector2(0.0, FightConstants.sprite_offset_y())
	sprite.scale = Vector2(FightConstants.SPRITE_SCALE, FightConstants.SPRITE_SCALE)


func set_opponent(target: CharacterBody2D) -> void:
	opponent = target


func set_arena(target: Node) -> void:
	arena = target


func set_combat_frozen(frozen: bool) -> void:
	combat_frozen = frozen
	if frozen:
		velocity = Vector2.ZERO
		_pause_sprite(true)
	else:
		_resume_sprite_speed()


func is_combat_frozen() -> bool:
	return combat_frozen


func _pause_sprite(paused: bool) -> void:
	var sprite: AnimatedSprite2D = _sprite_node()
	if sprite == null:
		return
	if paused:
		sprite.speed_scale = 0.0
	else:
		_resume_sprite_speed()


func _resume_sprite_speed() -> void:
	var sprite: AnimatedSprite2D = _sprite_node()
	if sprite == null:
		return
	if action_state == ActionState.DASH:
		sprite.speed_scale = 2.0
	elif action_state == ActionState.ULTIMATE:
		sprite.speed_scale = 1.35
	else:
		sprite.speed_scale = 1.0


func begin_ultimate_visual() -> void:
	combat_frozen = false
	_has_hit_this_attack = false
	action_state = ActionState.ULTIMATE
	velocity = Vector2.ZERO
	var anim_name: String = "ultimate"
	var sprite: AnimatedSprite2D = _sprite_node()
	if sprite != null and sprite.sprite_frames != null and sprite.sprite_frames.has_animation(anim_name):
		sprite.speed_scale = 1.35
		sprite.play(anim_name)


func set_round_active(active: bool) -> void:
	round_active = active
	if not active:
		velocity = Vector2.ZERO


func get_action_state() -> ActionState:
	return action_state


func is_attack_locked() -> bool:
	return action_state in [
		ActionState.HURT,
		ActionState.DEAD,
		ActionState.ATTACK1,
		ActionState.ATTACK2,
		ActionState.ULTIMATE,
	]


func is_ultimate_active() -> bool:
	return action_state == ActionState.ULTIMATE


func is_blocking() -> bool:
	return action_state == ActionState.BLOCK


func release_block() -> void:
	if action_state == ActionState.BLOCK:
		_set_state(ActionState.IDLE)


func _apply_animations() -> void:
	var sprite: AnimatedSprite2D = _sprite_node()
	if sprite == null:
		return
	sprite.sprite_frames = WarriorAnimUtil.build_sprite_frames(warrior_id)


func _physics_process(delta: float) -> void:
	if not round_active:
		velocity = Vector2.ZERO
		move_and_slide()
		return
	if combat_frozen:
		velocity = Vector2.ZERO
		move_and_slide()
		return
	if action_state == ActionState.DASH:
		_process_dash(delta)
	elif action_state == ActionState.IDLE:
		velocity.x = move_toward(velocity.x, 0.0, FightConstants.float_val("player_speed", 200.0) * 4.0 * delta)
	_update_facing()
	_clamp_position()
	move_and_slide()


func _process_dash(delta: float) -> void:
	_dash_timer -= delta
	var dash_speed: float = FightConstants.scale_x(
		FightConstants.float_val("dash_speed", 600.0),
		_arena_width
	)
	velocity.x = float(_dash_direction) * dash_speed
	if _dash_timer <= 0.0:
		stop_dash()


func try_move(direction: float) -> void:
	if not round_active or is_attack_locked() or action_state == ActionState.BLOCK:
		return
	if absf(direction) < 0.01:
		if action_state == ActionState.WALK:
			_set_state(ActionState.IDLE)
		return
	facing = 1 if direction > 0.0 else -1
	var sprite: AnimatedSprite2D = _sprite_node()
	if sprite != null:
		sprite.flip_h = facing < 0
	var speed: float = FightConstants.scale_x(
		FightConstants.float_val("player_speed", 200.0),
		_arena_width
	)
	velocity.x = direction * speed
	_set_state(ActionState.WALK)


func try_double_tap_move(direction: int, now_ms: int) -> bool:
	if not round_active or is_attack_locked() or action_state == ActionState.BLOCK:
		return false
	var cooldown_ms: int = int(FightConstants.float_val("dash_cooldown_ms", 3000.0))
	if now_ms - _last_dash_time_ms <= cooldown_ms:
		return false
	var threshold_ms: int = int(FightConstants.float_val("double_click_ms", 300.0))
	if direction < 0:
		if now_ms - _last_left_press_ms < threshold_ms:
			start_dash(-1, now_ms)
			return true
		_last_left_press_ms = now_ms
	else:
		if now_ms - _last_right_press_ms < threshold_ms:
			start_dash(1, now_ms)
			return true
		_last_right_press_ms = now_ms
	return false


func start_dash(direction: int, now_ms: int) -> void:
	if not round_active or is_attack_locked():
		return
	_dash_direction = direction
	_last_dash_time_ms = now_ms
	_dash_timer = FightConstants.float_val("dash_duration_ms", 200.0) / 1000.0
	facing = direction
	var sprite_dash: AnimatedSprite2D = _sprite_node()
	if sprite_dash != null:
		sprite_dash.flip_h = facing < 0
	_set_state(ActionState.DASH)
	_spawn_dash_ghost()


func stop_dash() -> void:
	if action_state != ActionState.DASH:
		return
	_dash_timer = 0.0
	velocity.x = 0.0
	_set_state(ActionState.IDLE)


func interrupt_dash() -> void:
	if action_state == ActionState.DASH:
		stop_dash()


func try_block() -> void:
	if not round_active or is_attack_locked():
		return
	velocity.x = 0.0
	_set_state(ActionState.BLOCK)


func try_light_attack() -> bool:
	return _try_attack(ActionState.ATTACK1)


func try_heavy_attack() -> bool:
	return _try_attack(ActionState.ATTACK2)


func try_ultimate() -> bool:
	if not round_active or is_attack_locked() or combat_frozen:
		return false
	if arena == null or not arena.has_method("request_ultimate"):
		return false
	return bool(arena.call("request_ultimate", self))


func _try_attack(next_state: ActionState) -> bool:
	if not round_active or is_attack_locked() or action_state == ActionState.BLOCK:
		return false
	_set_state(next_state)
	velocity.x = 0.0
	return true


func apply_hurt(knockback_px: float, from_right: bool) -> void:
	if action_state == ActionState.DEAD:
		return
	interrupt_dash()
	_has_hit_this_attack = false
	_set_state(ActionState.HURT)
	var sprite_hurt: AnimatedSprite2D = _sprite_node()
	if sprite_hurt != null:
		sprite_hurt.modulate = Color.WHITE
	var dir: float = 1.0 if from_right else -1.0
	if _knockback_tween != null and _knockback_tween.is_valid():
		_knockback_tween.kill()
	_knockback_tween = create_tween()
	var duration: float = 0.2 if knockback_px >= 50.0 else 0.12
	_knockback_tween.tween_property(self, "global_position:x", global_position.x + dir * knockback_px, duration) \
		.set_trans(Tween.TRANS_EXPO).set_ease(Tween.EASE_OUT)


func apply_death() -> void:
	velocity = Vector2.ZERO
	_set_state(ActionState.DEAD)


func _set_state(next_state: ActionState) -> void:
	if action_state == next_state and next_state != ActionState.WALK:
		return
	action_state = next_state
	_has_hit_this_attack = false
	var anim_name: String = _state_to_anim(next_state)
	var sprite: AnimatedSprite2D = _sprite_node()
	if sprite != null and sprite.sprite_frames != null and sprite.sprite_frames.has_animation(anim_name):
		sprite.speed_scale = 2.0 if next_state == ActionState.DASH else 1.0
		sprite.play(anim_name)


func _state_to_anim(state: ActionState) -> String:
	match state:
		ActionState.WALK, ActionState.DASH:
			return "walk"
		ActionState.ATTACK1:
			return "attack1"
		ActionState.ATTACK2:
			return "attack2"
		ActionState.ULTIMATE:
			return "ultimate"
		ActionState.BLOCK:
			return "protect"
		ActionState.HURT:
			return "hurt"
		ActionState.DEAD:
			return "dead"
		_:
			return "idle"


func _on_animation_finished() -> void:
	var sprite: AnimatedSprite2D = _sprite_node()
	if sprite != null:
		sprite.modulate = Color.WHITE
	if action_state in [ActionState.ATTACK1, ActionState.ATTACK2, ActionState.ULTIMATE, ActionState.HURT]:
		if round_active and action_state != ActionState.DEAD:
			_set_state(ActionState.IDLE)
		state_finished.emit()


func _on_frame_changed() -> void:
	if opponent == null or arena == null:
		return
	if action_state not in [ActionState.ATTACK1, ActionState.ATTACK2, ActionState.ULTIMATE]:
		return
	var sprite: AnimatedSprite2D = _sprite_node()
	if sprite == null:
		return
	if sprite.frame < 1 or sprite.frame > 2:
		return
	if _has_hit_this_attack:
		return
	_try_hit_opponent()


func _try_hit_opponent() -> void:
	if opponent == null or not opponent.has_method("get_action_state"):
		return
	var move_id: String = "light"
	var range_px: int = FightConstants.int_scaled("hit_range_light", 80, _arena_width)
	if action_state == ActionState.ATTACK2:
		move_id = "heavy"
	elif action_state == ActionState.ULTIMATE:
		move_id = "ultimate"
		range_px = FightConstants.int_scaled("hit_range_ultimate", 120, _arena_width)
	if absf(global_position.x - opponent.global_position.x) > float(range_px):
		return
	_has_hit_this_attack = true
	if arena.has_method("resolve_hit"):
		arena.call("resolve_hit", self, opponent, move_id)
	hit_connected.emit(self, opponent, move_id)


func _update_facing() -> void:
	if opponent == null or action_state == ActionState.DEAD:
		return
	facing = -1 if global_position.x > opponent.global_position.x else 1
	var sprite: AnimatedSprite2D = _sprite_node()
	if sprite != null:
		sprite.flip_h = facing < 0


func _clamp_position() -> void:
	var margin: float = 40.0
	global_position.x = clampf(global_position.x, margin, _arena_width - margin)


func _spawn_dash_ghost() -> void:
	var sprite: AnimatedSprite2D = _sprite_node()
	if sprite == null or sprite.sprite_frames == null:
		return
	var ghost: AnimatedSprite2D = AnimatedSprite2D.new()
	ghost.sprite_frames = sprite.sprite_frames
	ghost.animation = sprite.animation
	ghost.frame = sprite.frame
	ghost.flip_h = sprite.flip_h
	ghost.scale = sprite.scale
	ghost.modulate = Color(0.0, 0.75, 1.0, 0.5)
	ghost.global_position = get_sprite_global_position()
	get_parent().add_child(ghost)
	var tween: Tween = ghost.create_tween()
	tween.tween_property(ghost, "modulate:a", 0.0, 0.3)
	tween.finished.connect(ghost.queue_free)
