extends Control

## 展厅触控 · P4-B pingpong 拖动控拍（workspace 专用）
## 全屏透明 drag · 球拍 Y 与触点/鼠标即时对齐（直接设 position，无速度上限）

var _hud: Control = null
var _drag_pad: Control = null
var _drag_touch_index: int = -2
var _mouse_dragging: bool = false
var _target_viewport_y: float = -1.0
var _paddle_input_was_enabled: bool = true


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	offset_right = 0.0
	offset_bottom = 0.0
	mouse_filter = Control.MOUSE_FILTER_PASS
	z_index = 100
	process_physics_priority = 100
	_hud = get_node_or_null("../HUD") as Control
	_build_drag_pad()
	visible = false


func _process(_delta: float) -> void:
	if _hud != null and is_instance_valid(_hud):
		visible = _hud.visible


func _physics_process(_delta: float) -> void:
	if not visible:
		_stop_drag_control()
		return
	var target_y: float = _get_drag_target_y()
	if target_y < 0.0:
		_stop_drag_control()
		return
	_apply_paddle_y(target_y)


func _build_drag_pad() -> void:
	_drag_pad = Control.new()
	_drag_pad.name = "DragPad"
	_drag_pad.set_anchors_preset(Control.PRESET_FULL_RECT)
	_drag_pad.mouse_filter = Control.MOUSE_FILTER_STOP
	_drag_pad.gui_input.connect(_on_drag_pad_input)
	add_child(_drag_pad)


func _on_drag_pad_input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		var touch: InputEventScreenTouch = event as InputEventScreenTouch
		if touch.pressed:
			if _drag_touch_index == -2:
				_begin_drag_control()
				_drag_touch_index = touch.index
				_update_drag_target(touch.position)
		elif touch.index == _drag_touch_index:
			_end_drag()
		accept_event()
	elif event is InputEventScreenDrag:
		var drag: InputEventScreenDrag = event as InputEventScreenDrag
		if drag.index == _drag_touch_index:
			_update_drag_target(drag.position)
			accept_event()
	elif event is InputEventMouseButton:
		var mouse: InputEventMouseButton = event as InputEventMouseButton
		if mouse.button_index != MOUSE_BUTTON_LEFT:
			return
		if mouse.pressed:
			_begin_drag_control()
			_mouse_dragging = true
			_update_drag_target(get_viewport().get_mouse_position())
		else:
			_end_drag()
		accept_event()
	elif event is InputEventMouseMotion:
		if not _mouse_dragging:
			return
		_update_drag_target(get_viewport().get_mouse_position())
		accept_event()


func _update_drag_target(viewport_pos: Vector2) -> void:
	_target_viewport_y = viewport_pos.y


func _get_drag_target_y() -> float:
	if _mouse_dragging:
		return get_viewport().get_mouse_position().y
	if _drag_touch_index >= 0 and _target_viewport_y >= 0.0:
		return _target_viewport_y
	return -1.0


func _viewport_y_to_world_y(viewport_y: float) -> float:
	var viewport_pos: Vector2 = Vector2(get_viewport().get_visible_rect().size.x * 0.5, viewport_y)
	var canvas_pos: Vector2 = get_viewport().get_canvas_transform().affine_inverse() * viewport_pos
	return canvas_pos.y


func _apply_paddle_y(viewport_y: float) -> void:
	var paddle: Area2D = _find_player_paddle()
	if paddle == null:
		return
	var world_y: float = _viewport_y_to_world_y(viewport_y)
	var half_len: float = _read_paddle_half_length(paddle)
	var table_top: float = float(paddle.get("table_top"))
	var table_bottom: float = float(paddle.get("table_bottom"))
	paddle.position.y = clampf(world_y, table_top + half_len, table_bottom - half_len)


func _read_paddle_half_length(paddle: Area2D) -> float:
	var paddle_length: float = float(paddle.get("paddle_length"))
	if paddle_length <= 0.0:
		paddle_length = 56.0
	return paddle_length * 0.5


func _begin_drag_control() -> void:
	var paddle: Area2D = _find_player_paddle()
	if paddle == null:
		return
	if paddle.has_method("set_input_enabled"):
		_paddle_input_was_enabled = true
		paddle.call("set_input_enabled", false)


func _stop_drag_control() -> void:
	_restore_paddle_input()


func _restore_paddle_input() -> void:
	var paddle: Area2D = _find_player_paddle()
	if paddle == null:
		return
	if paddle.has_method("set_input_enabled"):
		paddle.call("set_input_enabled", _paddle_input_was_enabled)


func _find_player_paddle() -> Area2D:
	return get_tree().root.find_child("PlayerPaddle", true, false) as Area2D


func _end_drag() -> void:
	_drag_touch_index = -2
	_mouse_dragging = false
	_target_viewport_y = -1.0
	_restore_paddle_input()


func _notification(what: int) -> void:
	if what != NOTIFICATION_WM_WINDOW_FOCUS_OUT:
		return
	_end_drag()
