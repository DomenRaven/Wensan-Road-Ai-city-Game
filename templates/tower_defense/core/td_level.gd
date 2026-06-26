extends Node2D

const EmergencyRepairSkillRes: GDScript = preload("res://core/skills/emergency_repair.gd")
const GoldRushSkillRes: GDScript = preload("res://core/skills/gold_rush.gd")
const TdGridClass: GDScript = preload("res://core/td_grid.gd")
const TowerPlacerClass: GDScript = preload("res://core/tower_placer.gd")

signal gold_changed(amount: int)
signal lives_changed(amount: int)
signal wave_changed(wave_index: int, total: int)
signal game_won
signal game_lost(reason: String)
signal status_message(text: String)

const REFUND_RATIO: float = 0.5

const DEFAULT_PATH: Array[Vector2i] = [
	Vector2i(0, 3), Vector2i(1, 3), Vector2i(2, 3), Vector2i(3, 3),
	Vector2i(4, 3), Vector2i(5, 3), Vector2i(6, 3), Vector2i(6, 4),
	Vector2i(6, 5), Vector2i(7, 5), Vector2i(8, 5), Vector2i(9, 5),
	Vector2i(10, 5), Vector2i(11, 5),
]

var grid: RefCounted = null
var placer: RefCounted = null

var gold: int = 120
var lives: int = 5
var max_lives: int = 5
var _active_enemies: int = 0
var _all_waves_spawned: bool = false
var _game_over: bool = false
var _gold_rush_active: bool = false

var _map_texture: Texture2D = null
var _path_texture: Texture2D = null
var _bg_texture: Texture2D = null

@onready var _enemies_root: Node2D = $EnemiesRoot
@onready var _towers_root: Node2D = $TowersRoot
@onready var _wave_scheduler: Node = $WaveScheduler


func _ready() -> void:
	_load_theme_textures()
	_setup_grid()
	_setup_placer()
	_setup_wave_scheduler()
	_apply_economy()
	queue_redraw()
	call_deferred("_register_with_manager")


func _setup_grid() -> void:
	grid = TdGridClass.new()
	grid.setup_path(DEFAULT_PATH)


func _setup_placer() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var tower_cfg: Dictionary = tuning.get("tower", {}) as Dictionary
	var basic: Dictionary = tower_cfg.get("basic", {}) as Dictionary
	var cost: int = int(basic.get("cost", 50))
	var tower_scene: PackedScene = load("res://scenes/td_tower.tscn") as PackedScene
	placer = TowerPlacerClass.new()
	placer.call("setup", grid, _towers_root, tower_scene, cost)
	placer.tower_placed.connect(_on_tower_placed)
	placer.placement_failed.connect(_on_placement_failed)
	if placer.has_signal("tower_sold"):
		placer.tower_sold.connect(_on_tower_sold)


func _setup_wave_scheduler() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var wave_cfg: Dictionary = tuning.get("wave", {}) as Dictionary
	_wave_scheduler.configure(
		int(wave_cfg.get("count", 5)),
		int(wave_cfg.get("spawn_interval_ms", 800)),
		int(wave_cfg.get("enemies_per_wave_base", 3))
	)
	_wave_scheduler.enemy_spawn_requested.connect(_spawn_enemy)
	_wave_scheduler.wave_started.connect(_on_wave_started)
	_wave_scheduler.all_waves_complete.connect(_on_all_waves_spawned)
	_wave_scheduler.start(1.5)


func _apply_economy() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var economy: Dictionary = tuning.get("economy", {}) as Dictionary
	var lives_cfg: Dictionary = tuning.get("lives", {}) as Dictionary
	gold = int(economy.get("start_gold", 120))
	max_lives = int(lives_cfg.get("max_leaks", 5))
	lives = max_lives
	gold_changed.emit(gold)
	lives_changed.emit(lives)


func _load_theme_textures() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var map_path: String = str(theme.get("map_tileset", ""))
	var path_path: String = str(theme.get("path_tileset", ""))
	var bg_path: String = str(theme.get("background_sprite", ""))
	if map_path != "" and ResourceLoader.exists(map_path):
		_map_texture = load(map_path) as Texture2D
	if path_path != "" and ResourceLoader.exists(path_path):
		_path_texture = load(path_path) as Texture2D
	if bg_path != "" and ResourceLoader.exists(bg_path):
		_bg_texture = load(bg_path) as Texture2D


const GRID_COLS: int = 12
const GRID_ROWS: int = 8
const CELL_SIZE: int = 64

func _draw() -> void:
	if _bg_texture != null:
		draw_texture_rect(_bg_texture, Rect2(Vector2.ZERO, Vector2(800, 576)), false)
	for y: int in range(GRID_ROWS):
		for x: int in range(GRID_COLS):
			var cell: Vector2i = Vector2i(x, y)
			var rect: Rect2 = Rect2(
				Vector2(float(x * CELL_SIZE), float(y * CELL_SIZE)),
				Vector2(float(CELL_SIZE), float(CELL_SIZE))
			)
			if grid.is_path_cell(cell):
				if _path_texture != null:
					draw_texture_rect(_path_texture, rect, false)
				else:
					draw_rect(rect, Color(0.55, 0.45, 0.35, 1.0))
			elif cell in grid.buildable_cells:
				if _map_texture != null:
					draw_texture_rect(_map_texture, rect, false, Color(0.85, 1.0, 0.85, 1.0))
				else:
					draw_rect(rect, Color(0.35, 0.55, 0.35, 1.0))
			else:
				draw_rect(rect, Color(0.2, 0.28, 0.2, 1.0))
			draw_rect(rect, Color(0.0, 0.0, 0.0, 0.15), false, 1.0)


func _unhandled_input(event: InputEvent) -> void:
	if _game_over:
		return
	if event is InputEventMouseButton:
		var mouse: InputEventMouseButton = event as InputEventMouseButton
		if mouse.pressed and mouse.button_index == MOUSE_BUTTON_LEFT:
			_try_place_tower(mouse.position)
		elif mouse.pressed and mouse.button_index == MOUSE_BUTTON_RIGHT:
			_try_sell_tower(mouse.position)


func _try_place_tower(world_pos: Vector2) -> void:
	var tower: Node2D = placer.try_place_at_world(world_pos, gold)
	if tower == null:
		return
	var tuning: Dictionary = GameConfig.get_tuning()
	var tower_cfg: Dictionary = tuning.get("tower", {}) as Dictionary
	var basic: Dictionary = tower_cfg.get("basic", {}) as Dictionary
	var cost: int = int(basic.get("cost", 50))
	gold -= cost
	gold_changed.emit(gold)
	_configure_tower(tower)


func _try_sell_tower(world_pos: Vector2) -> void:
	var refund: int = int(placer.call("try_sell_at_world", world_pos, REFUND_RATIO))
	if refund <= 0:
		return
	gold += refund
	gold_changed.emit(gold)
	status_message.emit("卖掉守卫塔，返还 %d 金币" % refund)


func _configure_tower(tower: Node2D) -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var tower_cfg: Dictionary = tuning.get("tower", {}) as Dictionary
	var basic: Dictionary = tower_cfg.get("basic", {}) as Dictionary
	var theme: Dictionary = GameConfig.get_theme()
	if tower.has_method("configure"):
		tower.call(
			"configure",
			int(basic.get("damage", 15)),
			int(basic.get("range", 3)),
			int(basic.get("fire_interval_ms", 600)),
			str(theme.get("tower_sprite", "")),
			_enemies_root
		)


func _spawn_enemy(_wave_index: int, _spawn_index: int) -> void:
	var enemy_scene: PackedScene = load("res://scenes/td_enemy.tscn") as PackedScene
	var enemy: Node2D = enemy_scene.instantiate() as Node2D
	if enemy == null:
		return
	var waypoints: Array[Vector2] = _build_waypoints()
	var tuning: Dictionary = GameConfig.get_tuning()
	var enemy_cfg: Dictionary = tuning.get("enemy", {}) as Dictionary
	var basic: Dictionary = enemy_cfg.get("basic", {}) as Dictionary
	var theme: Dictionary = GameConfig.get_theme()
	if enemy.has_method("setup"):
		enemy.call(
			"setup",
			waypoints,
			int(basic.get("hp", 40)),
			float(basic.get("speed", 60)),
			int(basic.get("defense", 0)),
			str(theme.get("enemy_sprite", ""))
		)
	if enemy.has_signal("reached_exit"):
		enemy.reached_exit.connect(_on_enemy_reached_exit)
	if enemy.has_signal("defeated"):
		enemy.defeated.connect(_on_enemy_defeated)
	_enemies_root.add_child(enemy)
	if not waypoints.is_empty():
		enemy.position = waypoints[0]
	_active_enemies += 1


func _build_waypoints() -> Array[Vector2]:
	var points: Array[Vector2] = []
	for cell: Vector2i in grid.path_cells:
		points.append(grid.grid_to_world(cell))
	return points


func _on_enemy_reached_exit() -> void:
	_active_enemies = maxi(0, _active_enemies - 1)
	lives -= 1
	lives_changed.emit(lives)
	status_message.emit("有访客溜进花园了！")
	if lives <= 0:
		_end_game(false, "访客太多，花园失守了")
	else:
		_check_wave_clear()


func _on_enemy_defeated(reward: int) -> void:
	_active_enemies = maxi(0, _active_enemies - 1)
	var payout: int = reward
	if _gold_rush_active:
		payout *= 2
		_gold_rush_active = false
	gold += payout
	gold_changed.emit(gold)
	_check_wave_clear()


func _check_wave_clear() -> void:
	if _active_enemies > 0:
		return
	if _wave_scheduler.is_spawning_or_waiting() and not _wave_scheduler.has_finished_all_waves():
		_wave_scheduler.on_wave_cleared()
	if _all_waves_spawned and _active_enemies == 0 and lives > 0:
		_end_game(true, "")


func _on_wave_started(wave_index: int) -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var wave_cfg: Dictionary = tuning.get("wave", {}) as Dictionary
	var total: int = int(wave_cfg.get("count", 5))
	wave_changed.emit(wave_index, total)
	status_message.emit("第 %d 波访客来啦！" % wave_index)


func _on_all_waves_spawned() -> void:
	_all_waves_spawned = true
	status_message.emit("最后一波已出发，坚持住！")
	_check_wave_clear()


func _on_tower_placed(_cell: Vector2i, _tower: Node2D) -> void:
	status_message.emit("守卫塔就位！")


func _on_placement_failed(reason: String) -> void:
	if reason == "not_enough_gold":
		status_message.emit("金币不够哦")
	elif reason == "invalid_cell":
		status_message.emit("只能放在小路旁边")


func _on_tower_sold(_cell: Vector2i, _refund: int) -> void:
	pass


func activate_gold_rush() -> bool:
	if not GoldRushSkillRes.activate():
		return false
	_gold_rush_active = true
	status_message.emit("下一波击败奖励翻倍！")
	return true


func repair_all_towers() -> bool:
	return EmergencyRepairSkillRes.try_repair_towers(_towers_root)


func _end_game(won: bool, reason: String) -> void:
	if _game_over:
		return
	_game_over = true
	if won:
		game_won.emit()
	else:
		game_lost.emit(reason)


func _register_with_manager() -> void:
	var manager: Node = get_tree().get_first_node_in_group("game_manager")
	if manager != null and manager.has_method("register_level"):
		manager.call("register_level", self)
