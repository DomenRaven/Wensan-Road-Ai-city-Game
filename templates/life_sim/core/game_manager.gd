extends Node2D

const _InstantGrowSkill = preload("res://core/skills/instant_grow.gd")
const _SpeedCookSkill = preload("res://core/skills/speed_cook.gd")

var _game_over: bool = false
var _room: Node2D = null

@onready var _room_root: Node2D = $RoomRoot
@onready var _info_label: Label = $CanvasLayer/HUD/InfoLabel
@onready var _step_label: Label = $CanvasLayer/HUD/StepLabel
@onready var _inventory_label: Label = $CanvasLayer/HUD/InventoryLabel
@onready var _win_label: Label = $CanvasLayer/HUD/WinLabel
@onready var _grow_skill_btn: Button = $CanvasLayer/HUD/SkillPanel/GrowSkillBtn
@onready var _cook_skill_btn: Button = $CanvasLayer/HUD/SkillPanel/CookSkillBtn


func _ready() -> void:
	_win_label.visible = false
	_setup_skill_buttons()
	_load_room()


func _setup_skill_buttons() -> void:
	var grow_enabled: bool = _InstantGrowSkill.is_enabled()
	var cook_enabled: bool = _SpeedCookSkill.is_enabled()
	_grow_skill_btn.visible = grow_enabled
	_cook_skill_btn.visible = cook_enabled
	$CanvasLayer/HUD/SkillPanel.visible = grow_enabled or cook_enabled
	if grow_enabled:
		_grow_skill_btn.pressed.connect(_on_grow_skill_pressed)
	if cook_enabled:
		_cook_skill_btn.pressed.connect(_on_cook_skill_pressed)


func _load_room() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var level_cfg: Dictionary = tuning.get("level", {}) as Dictionary
	var scene_path: String = str(level_cfg.get("scene", "res://scenes/room.tscn"))
	if not ResourceLoader.exists(scene_path):
		push_error("GameManager: room scene missing: %s" % scene_path)
		return
	var packed: PackedScene = load(scene_path) as PackedScene
	_room = packed.instantiate() as Node2D
	_room_root.add_child(_room)
	if _room.has_signal("hud_changed"):
		_room.hud_changed.connect(_on_hud_changed)
	if _room.has_signal("order_completed"):
		_room.order_completed.connect(_on_order_completed)
	if _room.has_signal("game_won"):
		_room.game_won.connect(_on_game_won)


func _on_hud_changed(payload: Dictionary) -> void:
	var title: String = str(GameConfig.get_theme().get("title", GameConfig.get_display_name()))
	var orders_done: int = int(payload.get("orders_done", 0))
	var orders_total: int = int(payload.get("orders_total", 3))
	var coins: int = int(payload.get("coins", 0))
	_info_label.text = "%s  订单 %d/%d  金币 %d" % [title, orders_done, orders_total, coins]
	_step_label.text = str(payload.get("step", ""))
	_inventory_label.text = str(payload.get("inventory", ""))
	if _InstantGrowSkill.is_enabled():
		var grow_ready: bool = bool(payload.get("grow_skill_ready", false))
		var grow_cd: float = float(payload.get("grow_skill_cd", 0.0))
		_grow_skill_btn.disabled = not grow_ready
		_grow_skill_btn.text = "瞬间成熟" if grow_ready else "成熟 %ds" % int(ceil(grow_cd))
	if _SpeedCookSkill.is_enabled():
		var cook_ready: bool = bool(payload.get("cook_skill_ready", false))
		var cook_cd: float = float(payload.get("cook_skill_cd", 0.0))
		_cook_skill_btn.disabled = not cook_ready
		_cook_skill_btn.text = "快手烹饪" if cook_ready else "烹饪 %ds" % int(ceil(cook_cd))


func _on_order_completed(payout: int, total_orders: int) -> void:
	_step_label.text = "完成一单！+%d 金币（共 %d 单）" % [payout, total_orders]


func _on_game_won(coins: int) -> void:
	_game_over = true
	_win_label.text = "太棒了！完成 %d 单，共 %d 金币！点击重来" % [
		int(GameConfig.get_tuning().get("order", {}).get("count_to_win", 3)),
		coins
	]
	_win_label.visible = true


func _on_grow_skill_pressed() -> void:
	if _room != null and _room.has_method("trigger_instant_grow"):
		_room.call("trigger_instant_grow")


func _on_cook_skill_pressed() -> void:
	if _room != null and _room.has_method("trigger_speed_cook"):
		_room.call("trigger_speed_cook")


func _unhandled_input(event: InputEvent) -> void:
	if not _game_over:
		return
	if event is InputEventMouseButton:
		var mouse_event: InputEventMouseButton = event as InputEventMouseButton
		if mouse_event.pressed and mouse_event.button_index == MOUSE_BUTTON_LEFT:
			get_tree().reload_current_scene()
	elif event is InputEventKey:
		var key_event: InputEventKey = event as InputEventKey
		if key_event.pressed and key_event.keycode == KEY_R:
			get_tree().reload_current_scene()
