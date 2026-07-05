extends Control

## 展厅触控 · P4-B parkour 虚拟键（workspace 专用，映射 project.godot 的 jump / skill）
## 自动前进无方向键 · jump tap · skill（滑铲）hold

const BTN_SIZE: Vector2 = Vector2(84, 54)
const FONT_SIZE: int = 16
const MOUSE_TOUCH_INDEX: int = -1
const TAP_ACTIONS: Array[String] = ["jump"]
const BTN_SIDE_MARGIN: float = 14.0
const BTN_BOTTOM_MARGIN: float = 2.0

var _hud: Control = null
var _touch_action: Dictionary = {}
var _jump_release_pending: bool = false
var _zone_nodes: Dictionary = {}


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
	if _hud != null and is_instance_valid(_hud):
		visible = _hud.visible


func _physics_process(_delta: float) -> void:
	if _jump_release_pending:
		Input.action_release("jump")
		_jump_release_pending = false
		_set_zone_pressed("jump", false)


func _build_touch_ui() -> void:
	var pad: Control = Control.new()
	pad.name = "TouchPad"
	pad.set_anchors_preset(Control.PRESET_FULL_RECT)
	pad.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(pad)
	_add_zone(pad, "left", "跳", "jump")
	_add_zone(pad, "right", "滑铲", "skill")


func _add_zone(parent: Control, side: String, label: String, action: String) -> void:
	var zone: PanelContainer = PanelContainer.new()
	zone.name = "Zone_%s" % action
	zone.mouse_filter = Control.MOUSE_FILTER_STOP
	zone.add_theme_stylebox_override("panel", _make_btn_style(false))
	_configure_zone_layout(zone, side)
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


func _configure_zone_layout(zone: Control, side: String) -> void:
	zone.custom_minimum_size = BTN_SIZE
	if side == "left":
		zone.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
		zone.offset_left = BTN_SIDE_MARGIN
		zone.offset_top = -(BTN_SIZE.y + BTN_BOTTOM_MARGIN)
		zone.offset_right = BTN_SIDE_MARGIN + BTN_SIZE.x
		zone.offset_bottom = -BTN_BOTTOM_MARGIN
	else:
		zone.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
		zone.offset_left = -(BTN_SIDE_MARGIN + BTN_SIZE.x)
		zone.offset_top = -(BTN_SIZE.y + BTN_BOTTOM_MARGIN)
		zone.offset_right = -BTN_SIDE_MARGIN
		zone.offset_bottom = -BTN_BOTTOM_MARGIN


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
	style.shadow_offset = Vector2(0.0, 3.0)
	style.content_margin_left = 10.0
	style.content_margin_right = 10.0
	style.content_margin_top = 6.0
	style.content_margin_bottom = 6.0
	return style


func _set_zone_pressed(action: String, pressed: bool) -> void:
	var zone: Node = _zone_nodes.get(action)
	if zone is PanelContainer:
		(zone as PanelContainer).add_theme_stylebox_override("panel", _make_btn_style(pressed))


func _make_zone_handler(action: String) -> Callable:
	return func(event: InputEvent) -> void:
		if event is InputEventScreenTouch:
			var touch: InputEventScreenTouch = event as InputEventScreenTouch
			if touch.pressed:
				_on_zone_down(action, touch.index)
			else:
				_on_zone_up(action, touch.index)
			accept_event()
		elif event is InputEventMouseButton:
			var mouse: InputEventMouseButton = event as InputEventMouseButton
			if mouse.button_index != MOUSE_BUTTON_LEFT:
				return
			if mouse.pressed:
				_on_zone_down(action, MOUSE_TOUCH_INDEX)
			else:
				_on_zone_up(action, MOUSE_TOUCH_INDEX)
			accept_event()


func _is_tap_action(action: String) -> bool:
	return action in TAP_ACTIONS


func _on_zone_down(action: String, touch_index: int) -> void:
	_touch_action[touch_index] = action
	_set_zone_pressed(action, true)
	if _is_tap_action(action):
		Input.action_press(action)
		_jump_release_pending = true
	else:
		Input.action_press(action)


func _on_zone_up(action: String, touch_index: int) -> void:
	if _touch_action.get(touch_index, "") != action:
		return
	_touch_action.erase(touch_index)
	if not _is_tap_action(action):
		Input.action_release(action)
		_set_zone_pressed(action, false)


func _notification(what: int) -> void:
	if what != NOTIFICATION_WM_WINDOW_FOCUS_OUT:
		return
	_release_all_actions()


func _release_all_actions() -> void:
	for touch_index: int in _touch_action.keys():
		var action: String = str(_touch_action[touch_index])
		if not _is_tap_action(action):
			Input.action_release(action)
		_set_zone_pressed(action, false)
	_touch_action.clear()
	if Input.is_action_pressed("jump"):
		Input.action_release("jump")
	_jump_release_pending = false
	_set_zone_pressed("jump", false)
	if Input.is_action_pressed("skill"):
		Input.action_release("skill")
	_set_zone_pressed("skill", false)
