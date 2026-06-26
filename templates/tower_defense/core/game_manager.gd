extends Node2D

const EmergencyRepairSkillRes: GDScript = preload("res://core/skills/emergency_repair.gd")
const GoldRushSkillRes: GDScript = preload("res://core/skills/gold_rush.gd")

var _gold: int = 0
var _lives: int = 0
var _wave: int = 0
var _wave_total: int = 5
var _game_over: bool = false

var _repair_cooldown: float = 0.0
var _gold_rush_cooldown: float = 0.0

@onready var _hud_label: Label = $CanvasLayer/HUD/InfoLabel
@onready var _status_label: Label = $CanvasLayer/HUD/StatusLabel
@onready var _result_label: Label = $CanvasLayer/HUD/ResultLabel
@onready var _level_root: Node2D = $LevelRoot


func _ready() -> void:
	_result_label.visible = false
	_load_level()
	_update_hud()


func _process(delta: float) -> void:
	if _repair_cooldown > 0.0:
		_repair_cooldown -= delta
	if _gold_rush_cooldown > 0.0:
		_gold_rush_cooldown -= delta


func _unhandled_input(event: InputEvent) -> void:
	if _game_over:
		return
	if event.is_action_pressed("skill_1"):
		_try_emergency_repair()
	if event.is_action_pressed("skill_2"):
		_try_gold_rush()


func _load_level() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var level_cfg: Dictionary = tuning.get("level", {}) as Dictionary
	var scene_path: String = str(level_cfg.get("scene", "res://scenes/td_level.tscn"))
	if not ResourceLoader.exists(scene_path):
		push_error("GameManager: level scene missing: %s" % scene_path)
		return
	var packed: PackedScene = load(scene_path) as PackedScene
	var level: Node = packed.instantiate()
	_level_root.add_child(level)


func register_level(level: Node2D) -> void:
	if level.has_signal("gold_changed"):
		level.gold_changed.connect(_on_gold_changed)
	if level.has_signal("lives_changed"):
		level.lives_changed.connect(_on_lives_changed)
	if level.has_signal("wave_changed"):
		level.wave_changed.connect(_on_wave_changed)
	if level.has_signal("game_won"):
		level.game_won.connect(_on_game_won)
	if level.has_signal("game_lost"):
		level.game_lost.connect(_on_game_lost)
	if level.has_signal("status_message"):
		level.status_message.connect(_on_status_message)


func _on_gold_changed(amount: int) -> void:
	_gold = amount
	_update_hud()


func _on_lives_changed(amount: int) -> void:
	_lives = amount
	_update_hud()


func _on_wave_changed(wave_index: int, total: int) -> void:
	_wave = wave_index
	_wave_total = total
	_update_hud()


func _on_status_message(text: String) -> void:
	_status_label.text = text


func _on_game_won() -> void:
	_game_over = true
	_result_label.text = "太棒了！花园守住了！"
	_result_label.visible = true


func _on_game_lost(reason: String) -> void:
	_game_over = true
	_result_label.text = reason if reason != "" else "再试一次吧！"
	_result_label.visible = true


func _try_emergency_repair() -> void:
	if not EmergencyRepairSkillRes.is_enabled():
		return
	if _repair_cooldown > 0.0:
		_on_status_message("维修还在准备中")
		return
	var level: Node2D = _level_root.get_child(0) as Node2D
	if level == null or not level.has_method("repair_all_towers"):
		return
	if level.call("repair_all_towers"):
		_repair_cooldown = EmergencyRepairSkillRes.get_cooldown_sec()
		_on_status_message("守卫塔修好啦！")


func _try_gold_rush() -> void:
	if not GoldRushSkillRes.is_enabled():
		return
	if _gold_rush_cooldown > 0.0:
		_on_status_message("金币加成还在准备中")
		return
	var level: Node2D = _level_root.get_child(0) as Node2D
	if level == null or not level.has_method("activate_gold_rush"):
		return
	if level.call("activate_gold_rush"):
		_gold_rush_cooldown = GoldRushSkillRes.get_cooldown_sec()
		_on_status_message("金币加成已激活！")


func _update_hud() -> void:
	var title: String = str(GameConfig.get_theme().get("title", GameConfig.get_display_name()))
	_hud_label.text = "%s  金币:%d  生命:%d  波次:%d/%d" % [
		title, _gold, _lives, _wave, _wave_total
	]
