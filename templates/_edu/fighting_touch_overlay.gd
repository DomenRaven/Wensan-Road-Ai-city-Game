extends Control

## 展厅触控 · P4-B7 fighting 虚拟键（workspace 专用）
## PvE：六键贴底（左方向 · 右拳/格挡/大招）· PvP：屏下左右各一套紧凑六键

const BTN_SIZE_PVE: Vector2 = Vector2(72, 54)
const BTN_SIZE_PVP: Vector2 = Vector2(52, 48)
const FONT_SIZE_ARROW_PVE: int = 20
const FONT_SIZE_ARROW_PVP: int = 16
const FONT_SIZE_LABEL_PVE: int = 14
const FONT_SIZE_LABEL_PVP: int = 12
const MOUSE_TOUCH_INDEX: int = -1
const TAP_ACTIONS: Array[String] = [
	"p1_light", "p1_heavy", "p1_ultimate",
	"p2_light", "p2_heavy", "p2_ultimate",
]
const HOLD_ACTIONS: Array[String] = [
	"p1_left", "p1_right", "p1_block",
	"p2_left", "p2_right", "p2_block",
]
const BTN_SIDE_MARGIN_PVE: float = 14.0
const BTN_BOTTOM_MARGIN_PVE: float = 2.0
const BTN_GAP_PVE: float = 8.0
const BTN_ROW_GAP_PVE: float = 6.0
const BTN_SIDE_MARGIN_PVP: float = 8.0
const BTN_BOTTOM_MARGIN_PVP: float = 2.0
const BTN_GAP_PVP: float = 4.0
const BTN_ROW_GAP_PVP: float = 4.0
const BTN_BG_ALPHA: float = 0.34
const BTN_BG_ALPHA_PRESSED: float = 0.52
const BTN_BORDER_ALPHA: float = 0.48
const BTN_BORDER_ALPHA_PRESSED: float = 0.68
const BTN_SHADOW_ALPHA: float = 0.1

var _battle_hud: Control = null
var _pve_pad: Control = null
var _pvp_pad: Control = null
var _touch_action: Dictionary = {}
var _tap_release_pending: Array[String] = []
var _zone_nodes: Dictionary = {}
var _pvp_active: bool = false


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	offset_right = 0.0
	offset_bottom = 0.0
	mouse_filter = Control.MOUSE_FILTER_PASS
	z_index = 100
	_battle_hud = get_node_or_null("../BattleHUD") as Control
	_build_touch_ui()
	visible = false


func _process(_delta: float) -> void:
	if _battle_hud != null and is_instance_valid(_battle_hud):
		visible = _battle_hud.visible
	var pvp_now: bool = _is_pvp_mode()
	if pvp_now != _pvp_active:
		_pvp_active = pvp_now
		_sync_layout_visibility()


func _physics_process(_delta: float) -> void:
	if _tap_release_pending.is_empty():
		return
	for action: String in _tap_release_pending:
		Input.action_release(action)
		_set_zone_pressed(action, false)
	_tap_release_pending.clear()


func _build_touch_ui() -> void:
	_pve_pad = Control.new()
	_pve_pad.name = "PvePad"
	_pve_pad.set_anchors_preset(Control.PRESET_FULL_RECT)
	_pve_pad.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_pve_pad)
	_build_pve_zones(_pve_pad)

	_pvp_pad = Control.new()
	_pvp_pad.name = "PvpPad"
	_pvp_pad.set_anchors_preset(Control.PRESET_FULL_RECT)
	_pvp_pad.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_pvp_pad.visible = false
	add_child(_pvp_pad)
	_build_pvp_zones(_pvp_pad, "p1", "left")
	_build_pvp_zones(_pvp_pad, "p2", "right")
	_pvp_active = _is_pvp_mode()
	_sync_layout_visibility()


func _sync_layout_visibility() -> void:
	if _pve_pad != null:
		_pve_pad.visible = not _pvp_active
	if _pvp_pad != null:
		_pvp_pad.visible = _pvp_active


func _is_pvp_mode() -> bool:
	var player_count: int = 0
	for node: Node in get_tree().get_nodes_in_group("player"):
		if is_instance_valid(node) and not node.is_queued_for_deletion():
			player_count += 1
	return player_count >= 2


func _build_pve_zones(parent: Control) -> void:
	_add_zone(parent, "left", "←", "p1_left", FONT_SIZE_ARROW_PVE, BTN_SIZE_PVE, _configure_pve_zone_layout)
	_add_zone(parent, "left_inner", "→", "p1_right", FONT_SIZE_ARROW_PVE, BTN_SIZE_PVE, _configure_pve_zone_layout)
	_add_zone(parent, "light", "轻拳", "p1_light", FONT_SIZE_LABEL_PVE, BTN_SIZE_PVE, _configure_pve_zone_layout)
	_add_zone(parent, "heavy", "重拳", "p1_heavy", FONT_SIZE_LABEL_PVE, BTN_SIZE_PVE, _configure_pve_zone_layout)
	_add_zone(parent, "block", "格挡", "p1_block", FONT_SIZE_LABEL_PVE, BTN_SIZE_PVE, _configure_pve_zone_layout)
	_add_zone(parent, "ultimate", "大招", "p1_ultimate", FONT_SIZE_LABEL_PVE, BTN_SIZE_PVE, _configure_pve_zone_layout)


func _build_pvp_zones(parent: Control, player_prefix: String, side: String) -> void:
	var specs: Array[Dictionary] = [
		{"row": 1, "col": 0, "label": "←", "suffix": "left", "font": FONT_SIZE_ARROW_PVP},
		{"row": 1, "col": 1, "label": "→", "suffix": "right", "font": FONT_SIZE_ARROW_PVP},
		{"row": 1, "col": 2, "label": "轻", "suffix": "light", "font": FONT_SIZE_LABEL_PVP},
		{"row": 0, "col": 0, "label": "格", "suffix": "block", "font": FONT_SIZE_LABEL_PVP},
		{"row": 0, "col": 1, "label": "重", "suffix": "heavy", "font": FONT_SIZE_LABEL_PVP},
		{"row": 0, "col": 2, "label": "必", "suffix": "ultimate", "font": FONT_SIZE_LABEL_PVP},
	]
	for spec: Dictionary in specs:
		var row: int = int(spec["row"])
		var col: int = int(spec["col"])
		var action: String = "%s_%s" % [player_prefix, str(spec["suffix"])]
		var slot: String = "%s_%d_%d" % [side, row, col]
		_add_pvp_zone(
			parent,
			side,
			row,
			col,
			slot,
			str(spec["label"]),
			action,
			int(spec["font"]),
		)


func _add_pvp_zone(
	parent: Control,
	side: String,
	row: int,
	col: int,
	slot: String,
	label: String,
	action: String,
	font_size: int,
) -> void:
	var zone: PanelContainer = PanelContainer.new()
	zone.name = "Zone_%s" % action
	zone.mouse_filter = Control.MOUSE_FILTER_STOP
	zone.add_theme_stylebox_override("panel", _make_btn_style(false, BTN_SIZE_PVP))
	_configure_pvp_zone_layout(zone, side, row, col)
	var lbl: Label = Label.new()
	lbl.text = label
	lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	lbl.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	lbl.add_theme_font_size_override("font_size", font_size)
	lbl.add_theme_color_override("font_color", Color(0.98, 0.98, 1.0, 1.0))
	lbl.add_theme_color_override("font_outline_color", Color(0.05, 0.08, 0.2, 0.9))
	lbl.add_theme_constant_override("outline_size", 3)
	lbl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	zone.add_child(lbl)
	zone.gui_input.connect(_make_zone_handler(action))
	parent.add_child(zone)
	_zone_nodes[action] = {"node": zone, "size": BTN_SIZE_PVP}


func _add_zone(
	parent: Control,
	slot: String,
	label: String,
	action: String,
	font_size: int,
	btn_size: Vector2,
	layout_fn: Callable,
) -> void:
	var zone: PanelContainer = PanelContainer.new()
	zone.name = "Zone_%s" % action
	zone.mouse_filter = Control.MOUSE_FILTER_STOP
	zone.add_theme_stylebox_override("panel", _make_btn_style(false, btn_size))
	layout_fn.call(zone, slot)
	var lbl: Label = Label.new()
	lbl.text = label
	lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	lbl.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	lbl.add_theme_font_size_override("font_size", font_size)
	lbl.add_theme_color_override("font_color", Color(0.98, 0.98, 1.0, 1.0))
	lbl.add_theme_color_override("font_outline_color", Color(0.05, 0.08, 0.2, 0.9))
	lbl.add_theme_constant_override("outline_size", 3)
	lbl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	zone.add_child(lbl)
	zone.gui_input.connect(_make_zone_handler(action))
	parent.add_child(zone)
	_zone_nodes[action] = {"node": zone, "size": btn_size}


func _configure_pve_zone_layout(zone: Control, slot: String) -> void:
	zone.custom_minimum_size = BTN_SIZE_PVE
	var bottom_top: float = -(BTN_SIZE_PVE.y + BTN_BOTTOM_MARGIN_PVE)
	var bottom_bottom: float = -BTN_BOTTOM_MARGIN_PVE
	var upper_top: float = -(BTN_SIZE_PVE.y * 2.0 + BTN_ROW_GAP_PVE + BTN_BOTTOM_MARGIN_PVE)
	var upper_bottom: float = -(BTN_SIZE_PVE.y + BTN_ROW_GAP_PVE + BTN_BOTTOM_MARGIN_PVE)
	if slot == "left":
		zone.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
		zone.offset_left = BTN_SIDE_MARGIN_PVE
		zone.offset_top = bottom_top
		zone.offset_right = BTN_SIDE_MARGIN_PVE + BTN_SIZE_PVE.x
		zone.offset_bottom = bottom_bottom
	elif slot == "left_inner":
		var left_x: float = BTN_SIDE_MARGIN_PVE + BTN_SIZE_PVE.x + BTN_GAP_PVE
		zone.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
		zone.offset_left = left_x
		zone.offset_top = bottom_top
		zone.offset_right = left_x + BTN_SIZE_PVE.x
		zone.offset_bottom = bottom_bottom
	elif slot == "heavy":
		zone.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
		zone.offset_left = -(BTN_SIDE_MARGIN_PVE + BTN_SIZE_PVE.x)
		zone.offset_top = bottom_top
		zone.offset_right = -BTN_SIDE_MARGIN_PVE
		zone.offset_bottom = bottom_bottom
	elif slot == "light":
		var light_left: float = BTN_SIDE_MARGIN_PVE + BTN_SIZE_PVE.x * 2.0 + BTN_GAP_PVE
		zone.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
		zone.offset_left = -light_left
		zone.offset_top = bottom_top
		zone.offset_right = -(BTN_SIDE_MARGIN_PVE + BTN_SIZE_PVE.x + BTN_GAP_PVE)
		zone.offset_bottom = bottom_bottom
	elif slot == "ultimate":
		zone.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
		zone.offset_left = -(BTN_SIDE_MARGIN_PVE + BTN_SIZE_PVE.x)
		zone.offset_top = upper_top
		zone.offset_right = -BTN_SIDE_MARGIN_PVE
		zone.offset_bottom = upper_bottom
	else:
		var block_left: float = BTN_SIDE_MARGIN_PVE + BTN_SIZE_PVE.x * 2.0 + BTN_GAP_PVE
		zone.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
		zone.offset_left = -block_left
		zone.offset_top = upper_top
		zone.offset_right = -(BTN_SIDE_MARGIN_PVE + BTN_SIZE_PVE.x + BTN_GAP_PVE)
		zone.offset_bottom = upper_bottom


func _configure_pvp_zone_layout(zone: Control, side: String, row: int, col: int) -> void:
	zone.custom_minimum_size = BTN_SIZE_PVP
	var btn_w: float = BTN_SIZE_PVP.x
	var btn_h: float = BTN_SIZE_PVP.y
	var gap: float = BTN_GAP_PVP
	var margin: float = BTN_SIDE_MARGIN_PVP
	var row_gap: float = BTN_ROW_GAP_PVP
	var bottom_row_bottom: float = -BTN_BOTTOM_MARGIN_PVP
	var bottom_row_top: float = -(btn_h + BTN_BOTTOM_MARGIN_PVP)
	var upper_row_bottom: float = -(btn_h + row_gap + BTN_BOTTOM_MARGIN_PVP)
	var upper_row_top: float = -(btn_h * 2.0 + row_gap + BTN_BOTTOM_MARGIN_PVP)
	var top: float = bottom_row_top if row == 1 else upper_row_top
	var bottom: float = bottom_row_bottom if row == 1 else upper_row_bottom
	if side == "left":
		var left_x: float = margin + float(col) * (btn_w + gap)
		zone.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
		zone.offset_left = left_x
		zone.offset_top = top
		zone.offset_right = left_x + btn_w
		zone.offset_bottom = bottom
	else:
		var right_x: float = margin + float(2 - col) * (btn_w + gap)
		zone.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
		zone.offset_left = -(right_x + btn_w)
		zone.offset_top = top
		zone.offset_right = -right_x
		zone.offset_bottom = bottom


func _make_btn_style(pressed: bool, btn_size: Vector2) -> StyleBoxFlat:
	var style: StyleBoxFlat = StyleBoxFlat.new()
	if pressed:
		style.bg_color = Color(0.18, 0.42, 0.95, BTN_BG_ALPHA_PRESSED)
		style.border_color = Color(1.0, 0.55, 0.2, BTN_BORDER_ALPHA_PRESSED)
	else:
		style.bg_color = Color(0.05, 0.07, 0.2, BTN_BG_ALPHA)
		style.border_color = Color(1.0, 0.4, 0.12, BTN_BORDER_ALPHA)
	style.set_border_width_all(2)
	var radius: int = 18 if btn_size.x >= 64.0 else 14
	style.set_corner_radius_all(radius)
	style.shadow_color = Color(0.0, 0.0, 0.0, BTN_SHADOW_ALPHA)
	style.shadow_size = 3 if btn_size.x < 64.0 else 4
	style.shadow_offset = Vector2(0.0, 2.0)
	style.content_margin_left = 6.0 if btn_size.x < 64.0 else 8.0
	style.content_margin_right = 6.0 if btn_size.x < 64.0 else 8.0
	style.content_margin_top = 4.0 if btn_size.x < 64.0 else 6.0
	style.content_margin_bottom = 4.0 if btn_size.x < 64.0 else 6.0
	return style


func _set_zone_pressed(action: String, pressed: bool) -> void:
	var entry: Variant = _zone_nodes.get(action)
	if entry is Dictionary:
		var zone: PanelContainer = entry["node"] as PanelContainer
		var btn_size: Vector2 = entry["size"] as Vector2
		zone.add_theme_stylebox_override("panel", _make_btn_style(pressed, btn_size))


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
	Input.action_press(action)
	if _is_tap_action(action) and action not in _tap_release_pending:
		_tap_release_pending.append(action)


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
	for action: String in TAP_ACTIONS:
		if Input.is_action_pressed(action):
			Input.action_release(action)
		_set_zone_pressed(action, false)
	for action: String in HOLD_ACTIONS:
		if Input.is_action_pressed(action):
			Input.action_release(action)
		_set_zone_pressed(action, false)
	_tap_release_pending.clear()
