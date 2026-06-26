extends "res://core/paddle.gd"

var ai_speed: float = 105.0
var ai_deadzone: float = 14.0
var aim_error_px: float = 22.0
var react_line_x: float = 380.0
var far_chase_scale: float = 0.5
var aim_refresh_sec: float = 0.18

var _ball: Area2D = null
var _velocity_y: float = 0.0
var _ai_enabled: bool = true
var _aim_offset: float = 0.0
var _aim_timer: float = 0.0


func setup_ai(ball: Area2D) -> void:
	is_player = false
	is_left_side = false
	_ball = ball
	var tuning: Dictionary = GameConfig.get_tuning()
	var ai_cfg: Dictionary = tuning.get("ai", {}) as Dictionary
	ai_speed = float(ai_cfg.get("speed", ai_speed))
	ai_deadzone = float(ai_cfg.get("deadzone", ai_deadzone))
	aim_error_px = float(ai_cfg.get("aim_error", aim_error_px))
	react_line_x = float(ai_cfg.get("react_line_x", react_line_x))
	far_chase_scale = float(ai_cfg.get("far_chase_scale", far_chase_scale))
	aim_refresh_sec = float(ai_cfg.get("aim_refresh_sec", aim_refresh_sec))
	_aim_offset = randf_range(-aim_error_px, aim_error_px)
	_apply_theme()


func set_ai_enabled(enabled: bool) -> void:
	_ai_enabled = enabled
	_velocity_y = 0.0


func set_velocity_y(value: float) -> void:
	_velocity_y = value


func _physics_process(delta: float) -> void:
	if not _ai_enabled or _ball == null or not _ball.has_method("get_velocity"):
		return
	var ball_vel: Vector2 = _ball.call("get_velocity") as Vector2
	var ball_pos: Vector2 = _ball.global_position
	var center_y: float = (table_top + table_bottom) * 0.5
	var chase_speed: float = ai_speed
	var target_y: float = center_y

	if ball_vel.x > 0.0:
		_aim_timer -= delta
		if _aim_timer <= 0.0:
			_aim_timer = aim_refresh_sec
			_aim_offset = randf_range(-aim_error_px, aim_error_px)
		target_y = ball_pos.y + _aim_offset
		if ball_pos.x < react_line_x:
			chase_speed *= far_chase_scale
			target_y = lerpf(target_y, center_y, 0.4)
	else:
		if position.y < center_y - ai_deadzone:
			_velocity_y = ai_speed * 0.35
		elif position.y > center_y + ai_deadzone:
			_velocity_y = -ai_speed * 0.35
		else:
			_velocity_y = 0.0
		position.y += _velocity_y * delta
		var idle_half: float = paddle_length * 0.5
		position.y = clampf(position.y, table_top + idle_half, table_bottom - idle_half)
		return

	if position.y < target_y - ai_deadzone:
		_velocity_y = chase_speed
	elif position.y > target_y + ai_deadzone:
		_velocity_y = -chase_speed
	else:
		_velocity_y = 0.0
	position.y += _velocity_y * delta
	var half_len: float = paddle_length * 0.5
	position.y = clampf(position.y, table_top + half_len, table_bottom - half_len)
