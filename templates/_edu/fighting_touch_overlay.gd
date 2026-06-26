extends Control

## 展厅触控 · P1 虚拟格斗键（workspace 专用，映射 project.godot 的 p1_* 动作）

const BTN_SIZE: Vector2 = Vector2(56, 56)
const FONT_SIZE: int = 14

var _battle_hud: Control = null


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	offset_right = 0.0
	offset_bottom = 0.0
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	z_index = 100
	_battle_hud = get_node_or_null("../BattleHUD") as Control
	_build_touch_ui()
	visible = false


func _process(_delta: float) -> void:
	if _battle_hud != null and is_instance_valid(_battle_hud):
		visible = _battle_hud.visible


func _build_touch_ui() -> void:
	var pad: Control = Control.new()
	pad.name = "TouchPad"
	pad.set_anchors_preset(Control.PRESET_FULL_RECT)
	pad.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(pad)
	_add_hold_button(pad, Vector2(16, 292), "←", "p1_left")
	_add_hold_button(pad, Vector2(80, 292), "→", "p1_right")
	_add_tap_button(pad, Vector2(448, 292), "轻拳", "p1_light")
	_add_tap_button(pad, Vector2(512, 292), "重拳", "p1_heavy")
	_add_hold_button(pad, Vector2(448, 228), "格挡", "p1_block")
	_add_tap_button(pad, Vector2(512, 228), "大招", "p1_ultimate")


func _add_tap_button(parent: Control, pos: Vector2, label: String, action: String) -> void:
	var btn: Button = _make_button(label)
	btn.position = pos
	btn.size = BTN_SIZE
	btn.pressed.connect(func() -> void:
		_pulse_action(action)
	)
	parent.add_child(btn)


func _add_hold_button(parent: Control, pos: Vector2, label: String, action: String) -> void:
	var btn: Button = _make_button(label)
	btn.position = pos
	btn.size = BTN_SIZE
	btn.button_down.connect(func() -> void:
		Input.action_press(action)
	)
	btn.button_up.connect(func() -> void:
		Input.action_release(action)
	)
	parent.add_child(btn)


func _make_button(label: String) -> Button:
	var btn: Button = Button.new()
	btn.text = label
	btn.add_theme_font_size_override("font_size", FONT_SIZE)
	btn.mouse_filter = Control.MOUSE_FILTER_STOP
	var style: StyleBoxFlat = StyleBoxFlat.new()
	style.bg_color = Color(0.08, 0.1, 0.28, 0.82)
	style.border_color = Color(1.0, 0.34, 0.13, 0.95)
	style.set_border_width_all(2)
	style.set_corner_radius_all(8)
	btn.add_theme_stylebox_override("normal", style)
	var pressed: StyleBoxFlat = style.duplicate() as StyleBoxFlat
	pressed.bg_color = Color(0.2, 0.45, 1.0, 0.9)
	btn.add_theme_stylebox_override("pressed", pressed)
	return btn


func _pulse_action(action: String) -> void:
	Input.action_press(action)
	call_deferred("_release_action", action)


func _release_action(action: String) -> void:
	Input.action_release(action)
