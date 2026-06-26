extends "res://core/fighter.gd"

var _ai_attack_timer: float = 0.0
var _ai_interval: float = 0.6
var _attack_range: float = 53.0
var _move_speed_scale: float = 0.8


func _apply_ai_tuning() -> void:
	var ai_cfg: Dictionary = GameConfig.get_tuning().get("ai", {}) as Dictionary
	_ai_interval = float(ai_cfg.get("tick_interval_sec", 0.6))
	_attack_range = FightConstants.scale_x(
		float(ai_cfg.get("attack_range_px", 80.0)),
		_arena_width
	)
	_move_speed_scale = float(ai_cfg.get("move_speed_scale", 0.8))


func configure(
	p_warrior_id: String,
	p_is_player_one: bool,
	spawn_x: float,
	spawn_facing: int,
	p_arena_width: float,
	p_floor_y: float
) -> void:
	super.configure(p_warrior_id, p_is_player_one, spawn_x, spawn_facing, p_arena_width, p_floor_y)
	_apply_ai_tuning()


func _physics_process(delta: float) -> void:
	if not round_active:
		super._physics_process(delta)
		return
	if not combat_frozen:
		_update_ai_movement()
		_ai_attack_timer += delta
		if _ai_attack_timer >= _ai_interval:
			_ai_attack_timer = 0.0
			_decide_ai_attack()
	super._physics_process(delta)


func _update_ai_movement() -> void:
	if opponent == null:
		return
	if action_state == ActionState.DASH or is_attack_locked() or action_state == ActionState.BLOCK:
		return
	var distance: float = absf(global_position.x - opponent.global_position.x)
	if distance > _attack_range:
		var direction: float = signf(opponent.global_position.x - global_position.x)
		if absf(direction) > 0.01:
			try_move(direction)
			velocity.x *= _move_speed_scale
	else:
		if action_state == ActionState.WALK:
			velocity.x = move_toward(
				velocity.x,
				0.0,
				FightConstants.scale_x(FightConstants.float_val("player_speed", 200.0), _arena_width) * 4.0 * get_physics_process_delta_time()
			)
			if absf(velocity.x) < 1.0:
				_set_state(ActionState.IDLE)


func _decide_ai_attack() -> void:
	if opponent == null or combat_frozen:
		return
	if action_state == ActionState.DASH or is_attack_locked():
		return
	var distance: float = absf(global_position.x - opponent.global_position.x)
	if distance > _attack_range:
		return
	velocity.x = 0.0
	var rand_val: float = randf()
	if action_state == ActionState.BLOCK:
		var player_attacking: bool = false
		if opponent.has_method("get_action_state"):
			var opp_state: int = int(opponent.call("get_action_state"))
			player_attacking = opp_state in [ActionState.ATTACK1, ActionState.ATTACK2, ActionState.ULTIMATE]
		if not player_attacking:
			release_block()
		return
	if opponent.has_method("get_action_state"):
		var opp_state: int = int(opponent.call("get_action_state"))
		if opp_state in [ActionState.ATTACK1, ActionState.ATTACK2, ActionState.ULTIMATE]:
			if rand_val < 0.7:
				try_block()
			else:
				_set_state(ActionState.IDLE)
			return
	if arena != null and arena.has_method("can_spend_mp"):
		if bool(arena.call("can_spend_mp", is_player_one)) and rand_val < 0.5:
			try_ultimate()
			return
	if rand_val < 0.3:
		try_heavy_attack()
	elif rand_val < 0.7:
		try_light_attack()
