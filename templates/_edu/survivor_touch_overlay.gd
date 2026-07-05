extends Control

## 展厅触控 · P4-B survivor 虚拟摇杆（workspace 专用）
## 左下摇杆 → move_* · 无右侧 UI，游戏区原生点击定朝向

const JOY_SIZE: float = 68.0
const JOY_RADIUS: float = 34.0
const KNOB_RADIUS: float = 14.0
const JOY_MARGIN_LEFT: float = 14.0
const JOY_MARGIN_BOTTOM: float = 2.0
const JOY_DEADZONE: float = 0.15
const MOUSE_TOUCH_INDEX: int = -1
const MOVE_ACTIONS: Array[String] = ["move_left", "move_right", "move_up", "move_down"]

var _hud: Control = null
var _joy_base: Control = null
var _joy_knob: Control = null
var _joy_touch_index: int = -2
var _joy_vector: Vector2 = Vector2.ZERO


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	offset_right = 0.0
	offset_bottom = 0.0
	mouse_filter = Control.MOUSE_FILTER_PASS
	z_index = 100
	_hud = get_node_or_null("../HUD") as Control
	_build_touch_ui()
	visible = false


func _process(_delta: float) -> void:
	var show_touch: bool = _hud.visible if _hud != null and is_instance_valid(_hud) else false
	var level_ui: CanvasLayer = _find_level_up_ui()
	if level_ui != null and level_ui.visible:
		show_touch = false
		if visible:
			_reset_joystick()
	visible = show_touch
	if visible and _joy_touch_index >= -1:
		_apply_move_vector(_joy_vector)


func _exit_tree() -> void:
	_clear_move_actions()


func _build_touch_ui() -> void:
	var pad: Control = Control.new()
	pad.name = "TouchPad"
	pad.set_anchors_preset(Control.PRESET_FULL_RECT)
	pad.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(pad)
	_build_joystick(pad)


func _build_joystick(parent: Control) -> void:
	_joy_base = PanelContainer.new()
	_joy_base.name = "JoystickBase"
	_joy_base.mouse_filter = Control.MOUSE_FILTER_STOP
	_joy_base.custom_minimum_size = Vector2(JOY_SIZE, JOY_SIZE)
	_joy_base.add_theme_stylebox_override("panel", _make_joy_base_style())
	_joy_base.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	_joy_base.offset_left = JOY_MARGIN_LEFT
	_joy_base.offset_top = -(JOY_SIZE + JOY_MARGIN_BOTTOM)
	_joy_base.offset_right = JOY_MARGIN_LEFT + JOY_SIZE
	_joy_base.offset_bottom = -JOY_MARGIN_BOTTOM
	_joy_base.gui_input.connect(_on_joystick_input)
	parent.add_child(_joy_base)

	_joy_knob = PanelContainer.new()
	_joy_knob.name = "JoystickKnob"
	_joy_knob.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_joy_knob.custom_minimum_size = Vector2(KNOB_RADIUS * 2.0, KNOB_RADIUS * 2.0)
	_joy_knob.add_theme_stylebox_override("panel", _make_joy_knob_style(false))
	_joy_base.add_child(_joy_knob)
	_center_knob()


func _find_level_up_ui() -> CanvasLayer:
	return get_tree().root.find_child("LevelUpUI", true, false) as CanvasLayer


func _on_joystick_input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		var touch: InputEventScreenTouch = event as InputEventScreenTouch
		if touch.pressed:
			if _joy_touch_index == -2:
				_joy_touch_index = touch.index
				_update_joystick_from_screen(touch.position)
		elif touch.index == _joy_touch_index:
			_reset_joystick()
		accept_event()
	elif event is InputEventScreenDrag:
		var drag: InputEventScreenDrag = event as InputEventScreenDrag
		if drag.index == _joy_touch_index:
			_update_joystick_from_screen(drag.position)
			accept_event()
	elif event is InputEventMouseButton:
		var mouse: InputEventMouseButton = event as InputEventMouseButton
		if mouse.button_index != MOUSE_BUTTON_LEFT:
			return
		if mouse.pressed and _joy_touch_index == -2:
			_joy_touch_index = MOUSE_TOUCH_INDEX
			_update_joystick_from_screen(_viewport_pos_from_local(_joy_base, mouse.position))
		elif not mouse.pressed and _joy_touch_index == MOUSE_TOUCH_INDEX:
			_reset_joystick()
		accept_event()
	elif event is InputEventMouseMotion:
		if _joy_touch_index == MOUSE_TOUCH_INDEX:
			var motion: InputEventMouseMotion = event as InputEventMouseMotion
			_update_joystick_from_screen(_viewport_pos_from_local(_joy_base, motion.position))
			accept_event()


func _update_joystick_from_screen(viewport_pos: Vector2) -> void:
	var center: Vector2 = _joy_base.get_global_transform_with_canvas().origin + Vector2(JOY_RADIUS, JOY_RADIUS)
	var offset: Vector2 = viewport_pos - center
	if offset.length() > JOY_RADIUS:
		offset = offset.normalized() * JOY_RADIUS
	_joy_vector = offset / JOY_RADIUS
	_move_knob(offset)
	_set_knob_pressed(true)


func _reset_joystick() -> void:
	_joy_touch_index = -2
	_joy_vector = Vector2.ZERO
	_center_knob()
	_set_knob_pressed(false)
	_clear_move_actions()


func _apply_move_vector(dir: Vector2) -> void:
	var mag: float = minf(dir.length(), 1.0)
	if mag < JOY_DEADZONE:
		_clear_move_actions()
		return
	var scaled: Vector2 = dir.normalized() * mag
	_set_action_strength("move_right", clampf(scaled.x, 0.0, 1.0))
	_set_action_strength("move_left", clampf(-scaled.x, 0.0, 1.0))
	_set_action_strength("move_down", clampf(scaled.y, 0.0, 1.0))
	_set_action_strength("move_up", clampf(-scaled.y, 0.0, 1.0))


func _set_action_strength(action: String, strength: float) -> void:
	if strength > 0.001:
		Input.action_press(action, strength)
	else:
		Input.action_release(action)


func _clear_move_actions() -> void:
	for action: String in MOVE_ACTIONS:
		Input.action_release(action)


func _viewport_pos_from_local(control: Control, local_pos: Vector2) -> Vector2:
	return control.get_global_transform_with_canvas().origin + local_pos


func _center_knob() -> void:
	_joy_knob.position = Vector2(JOY_RADIUS - KNOB_RADIUS, JOY_RADIUS - KNOB_RADIUS)


func _move_knob(offset: Vector2) -> void:
	_joy_knob.position = Vector2(JOY_RADIUS - KNOB_RADIUS, JOY_RADIUS - KNOB_RADIUS) + offset


func _set_knob_pressed(pressed: bool) -> void:
	_joy_knob.add_theme_stylebox_override("panel", _make_joy_knob_style(pressed))


func _make_joy_base_style() -> StyleBoxFlat:
	var style: StyleBoxFlat = StyleBoxFlat.new()
	style.bg_color = Color(0.05, 0.07, 0.2, 0.72)
	style.border_color = Color(1.0, 0.4, 0.12, 0.88)
	style.set_border_width_all(2)
	style.set_corner_radius_all(int(JOY_RADIUS))
	style.shadow_color = Color(0.0, 0.0, 0.0, 0.35)
	style.shadow_size = 5
	return style


func _make_joy_knob_style(pressed: bool) -> StyleBoxFlat:
	var style: StyleBoxFlat = StyleBoxFlat.new()
	if pressed:
		style.bg_color = Color(0.18, 0.42, 0.95, 0.82)
		style.border_color = Color(1.0, 0.55, 0.2, 0.9)
	else:
		style.bg_color = Color(0.12, 0.2, 0.45, 0.78)
		style.border_color = Color(0.85, 0.9, 1.0, 0.75)
	style.set_border_width_all(2)
	style.set_corner_radius_all(int(KNOB_RADIUS))
	return style
