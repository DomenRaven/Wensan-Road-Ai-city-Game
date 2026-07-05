extends Control

## 展厅触控 · P4-B platformer 虚拟键（workspace 专用，映射 project.godot 的 move_* / jump）
## 多点触控：每指独立追踪，方向 hold + 跳 tap 可同时进行（鼠标单键无法模拟）

const BTN_SIZE: Vector2 = Vector2(56, 56)
const FONT_SIZE: int = 14
const MOUSE_TOUCH_INDEX: int = -1

var _hud: Control = null
var _touch_action: Dictionary = {}
var _jump_release_pending: bool = false


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


func _build_touch_ui() -> void:
	var pad: Control = Control.new()
	pad.name = "TouchPad"
	pad.set_anchors_preset(Control.PRESET_FULL_RECT)
	pad.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(pad)
	_add_zone(pad, Vector2(16, 292), "←", "move_left")
	_add_zone(pad, Vector2(80, 292), "→", "move_right")
	_add_zone(pad, Vector2(512, 292), "跳", "jump")


func _add_zone(parent: Control, pos: Vector2, label: String, action: String) -> void:
	var zone: PanelContainer = PanelContainer.new()
	zone.position = pos
	zone.custom_minimum_size = BTN_SIZE
	zone.size = BTN_SIZE
	zone.mouse_filter = Control.MOUSE_FILTER_STOP
	zone.add_theme_stylebox_override("panel", _make_stylebox())
	var lbl: Label = Label.new()
	lbl.text = label
	lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	lbl.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	lbl.add_theme_font_size_override("font_size", FONT_SIZE)
	lbl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	zone.add_child(lbl)
	zone.gui_input.connect(_make_zone_handler(action))
	parent.add_child(zone)


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


func _make_stylebox() -> StyleBoxFlat:
	var style: StyleBoxFlat = StyleBoxFlat.new()
	style.bg_color = Color(0.08, 0.1, 0.28, 0.82)
	style.border_color = Color(1.0, 0.34, 0.13, 0.95)
	style.set_border_width_all(2)
	style.set_corner_radius_all(8)
	return style


func _on_zone_down(action: String, touch_index: int) -> void:
	_touch_action[touch_index] = action
	if action == "jump":
		Input.action_press("jump")
		_jump_release_pending = true
	else:
		Input.action_press(action)


func _on_zone_up(action: String, touch_index: int) -> void:
	if _touch_action.get(touch_index, "") != action:
		return
	_touch_action.erase(touch_index)
	if action != "jump":
		Input.action_release(action)


func _notification(what: int) -> void:
	if what != NOTIFICATION_WM_WINDOW_FOCUS_OUT:
		return
	_release_all_actions()


func _release_all_actions() -> void:
	for touch_index: int in _touch_action.keys():
		var action: String = str(_touch_action[touch_index])
		if action != "jump":
			Input.action_release(action)
	_touch_action.clear()
	if Input.is_action_pressed("jump"):
		Input.action_release("jump")
	_jump_release_pending = false
