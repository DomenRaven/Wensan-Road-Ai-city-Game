extends "res://core/fighter.gd"


func handle_input(
	left_pressed: bool,
	right_pressed: bool,
	just_left: bool,
	just_right: bool,
	just_light: bool,
	just_heavy: bool,
	block_held: bool,
	just_ultimate: bool
) -> void:
	if not round_active or combat_frozen:
		return
	var now_ms: int = Time.get_ticks_msec()
	if action_state == ActionState.DASH:
		if just_light or just_heavy or just_ultimate or block_held:
			interrupt_dash()
		else:
			return
	if is_attack_locked():
		velocity.x = 0.0
		return
	if block_held:
		try_block()
		return
	if action_state == ActionState.BLOCK:
		release_block()
	if just_ultimate:
		if try_ultimate():
			return
	if just_heavy:
		if try_heavy_attack():
			return
	if just_light:
		if try_light_attack():
			return
	if just_left:
		if try_double_tap_move(-1, now_ms):
			return
	if just_right:
		if try_double_tap_move(1, now_ms):
			return
	var direction: float = 0.0
	if left_pressed:
		direction -= 1.0
	if right_pressed:
		direction += 1.0
	try_move(direction)
