extends Control

## 展厅触控 · shmup 虚拟键（workspace 专用）
## 仅左/右移动；炸弹/激光等技能键统一走 AiSandboxBridge.ensure_touch_action
## 不改 templates/shmup/core；由 edu_workspace 注入

const BTN_SIZE: Vector2 = Vector2(88, 56)
const FONT_SIZE: int = 16
const MOUSE_TOUCH_INDEX: int = -1
const BTN_SIDE_MARGIN: float = 14.0
const BTN_BOTTOM_MARGIN: float = 4.0

var _hud: Control = null
var _touch_action: Dictionary = {}
var _zone_nodes: Dictionary = {}


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	offset_right = 0.0
	offset_bottom = 0.0
	mouse_filter = Control.MOUSE_FILTER_PASS
	z_index = 100
	_hud = get_node_or_null("../HUD") as Control
	_ensure_input_actions()
	_build_touch_ui()
	visible = false


func _process(_delta: float) -> void:
	if _hud != null and is_instance_valid(_hud):
		visible = _hud.visible


func _ensure_input_actions() -> void:
	_ensure_action("move_left", KEY_A)
	_ensure_action("move_right", KEY_D)


func _ensure_action(action: String, keycode: Key) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action)
	var ev := InputEventKey.new()
	ev.physical_keycode = keycode
	for existing in InputMap.action_get_events(action):
		if existing is InputEventKey and (existing as InputEventKey).physical_keycode == keycode:
			return
	InputMap.action_add_event(action, ev)


func _build_touch_ui() -> void:
	var pad: Control = Control.new()
	pad.name = "TouchPad"
	pad.set_anchors_preset(Control.PRESET_FULL_RECT)
	pad.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(pad)
	_add_zone(pad, "bl", "←", "move_left")
	_add_zone(pad, "br_move", "→", "move_right")


func _add_zone(parent: Control, slot: String, label: String, action: String) -> void:
	var zone: PanelContainer = PanelContainer.new()
	zone.name = "Zone_%s" % action
	zone.mouse_filter = Control.MOUSE_FILTER_STOP
	zone.add_theme_stylebox_override("panel", _make_btn_style(false))
	_configure_zone_layout(zone, slot)
	var lbl: Label = Label.new()
	lbl.text = label
	lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	lbl.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	lbl.add_theme_font_size_override("font_size", FONT_SIZE)
	lbl.add_theme_color_override("font_color", Color(0.98, 0.98, 1.0, 1.0))
	lbl.add_theme_color_override("font_outline_color", Color(0.05, 0.08, 0.2, 0.9))
	lbl.add_theme_constant_override("outline_size", 3)
	lbl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	zone.add_child(lbl)
	zone.gui_input.connect(_make_zone_handler(action))
	parent.add_child(zone)
	_zone_nodes[action] = zone


func _configure_zone_layout(zone: Control, slot: String) -> void:
	zone.custom_minimum_size = BTN_SIZE
	match slot:
		"bl":
			zone.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
			zone.offset_left = BTN_SIDE_MARGIN
			zone.offset_top = -(BTN_SIZE.y + BTN_BOTTOM_MARGIN)
			zone.offset_right = BTN_SIDE_MARGIN + BTN_SIZE.x
			zone.offset_bottom = -BTN_BOTTOM_MARGIN
		"br_move":
			zone.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
			zone.offset_left = BTN_SIDE_MARGIN + BTN_SIZE.x + 10.0
			zone.offset_top = -(BTN_SIZE.y + BTN_BOTTOM_MARGIN)
			zone.offset_right = BTN_SIDE_MARGIN + BTN_SIZE.x * 2.0 + 10.0
			zone.offset_bottom = -BTN_BOTTOM_MARGIN
		_:
			zone.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)


func _make_btn_style(pressed: bool) -> StyleBoxFlat:
	var style: StyleBoxFlat = StyleBoxFlat.new()
	if pressed:
		style.bg_color = Color(0.18, 0.42, 0.95, 0.94)
		style.border_color = Color(1.0, 0.55, 0.2, 1.0)
	else:
		style.bg_color = Color(0.05, 0.07, 0.2, 0.9)
		style.border_color = Color(1.0, 0.4, 0.12, 0.92)
	style.set_border_width_all(2)
	style.set_corner_radius_all(18)
	style.shadow_color = Color(0.0, 0.0, 0.0, 0.38)
	style.shadow_size = 5
	return style


func _make_zone_handler(action: String) -> Callable:
	return func(event: InputEvent) -> void:
		if event is InputEventScreenTouch:
			var touch: InputEventScreenTouch = event as InputEventScreenTouch
			if touch.pressed:
				_on_zone_down(action, touch.index)
			else:
				_on_zone_up(action, touch.index)
		elif event is InputEventMouseButton:
			var mouse: InputEventMouseButton = event as InputEventMouseButton
			if mouse.button_index != MOUSE_BUTTON_LEFT:
				return
			if mouse.pressed:
				_on_zone_down(action, MOUSE_TOUCH_INDEX)
			else:
				_on_zone_up(action, MOUSE_TOUCH_INDEX)


func _on_zone_down(action: String, touch_index: int) -> void:
	_touch_action[touch_index] = action
	Input.action_press(action)
	_set_zone_pressed(action, true)


func _on_zone_up(action: String, touch_index: int) -> void:
	if _touch_action.get(touch_index, "") != action:
		return
	_touch_action.erase(touch_index)
	Input.action_release(action)
	_set_zone_pressed(action, false)


func _set_zone_pressed(action: String, pressed: bool) -> void:
	if not _zone_nodes.has(action):
		return
	var zone: PanelContainer = _zone_nodes[action] as PanelContainer
	if zone != null:
		zone.add_theme_stylebox_override("panel", _make_btn_style(pressed))


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_WINDOW_FOCUS_OUT:
		for touch_index: int in _touch_action.keys():
			var action: String = str(_touch_action[touch_index])
			Input.action_release(action)
			_set_zone_pressed(action, false)
		_touch_action.clear()
