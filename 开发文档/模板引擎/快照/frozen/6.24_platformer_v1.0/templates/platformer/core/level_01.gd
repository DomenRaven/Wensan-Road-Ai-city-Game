extends Node2D

## 秒哒 MainGame 坐标系映射：800×600 → Godot 640×360，关卡宽 ×3
const TILE: float = 32.0
const MIAODA_VIEW_W: float = 800.0
const MIAODA_VIEW_H: float = 600.0
const MIAODA_LEVEL_MULT: float = 3.0
const GODOT_VIEW_H: float = 360.0

const GROUND_COLOR: Color = Color(0.545, 0.271, 0.075, 1.0)  # 秒哒 Boot #8B4513
const PIPE_COLOR: Color = Color(0.0, 0.8, 0.0, 1.0)  # 秒哒 Boot #00cc00
const PIPE_W: float = 48.0
const PIPE_H: float = 96.0

const ThemeSpriteUtil := preload("res://core/theme_sprite.gd")
const COLLECTIBLE_SCENE: PackedScene = preload("res://scenes/collectible.tscn")
const ENEMY_SCENE: PackedScene = preload("res://scenes/patrol_enemy.tscn")
const TOUGH_SCENE: PackedScene = preload("res://scenes/tough_enemy.tscn")
const JUMPER_SCENE: PackedScene = preload("res://scenes/jumper_enemy.tscn")
const TURRET_SCENE: PackedScene = preload("res://scenes/turret_enemy.tscn")
const BLOCK_SCENE: PackedScene = preload("res://scenes/question_block.tscn")
const GOAL_SCENE: PackedScene = preload("res://scenes/goal_flag.tscn")
const ENEMY_HALF_W: float = 14.0
const ENEMY_BODY_H: float = 24.0

const BG_TINTS: Array[Color] = [
	Color(1.0, 1.0, 1.0, 1.0),
	Color(0.92, 0.96, 1.0, 1.0),
	Color(0.96, 1.0, 0.92, 1.0),
	Color(1.0, 0.94, 0.96, 1.0),
	Color(0.94, 0.92, 1.0, 1.0),
]

var _floor_top_y: float = 328.0
var _ground_center_y: float = 344.0
var _spawn_blockers: Array[Rect2] = []
var _turret_anchors: Array[Vector2] = []
var _level_profile: Dictionary = {}
var _level_num: int = 1

@onready var _platforms_root: Node2D = $Platforms
@onready var _props_root: Node2D = $Props
@onready var _collectibles_root: Node2D = $Collectibles
@onready var _enemies_root: Node2D = $Enemies
@onready var _projectiles_root: Node2D = $Projectiles


func configure_level(level_num: int) -> void:
	_level_num = maxi(1, level_num)


func _ready() -> void:
	add_to_group("platformer_level")
	_spawn_blockers.clear()
	_turret_anchors.clear()
	_read_floor_from_config()
	_level_profile = _build_level_profile()
	var level_width: float = _get_level_width()
	_build_background(level_width)
	_build_ground(level_width)
	_build_pipes()
	_build_procedural_content(level_width)
	_spawn_turret_enemies()
	_build_goal(level_width)
	call_deferred("_register_with_manager")


func _get_current_level_num() -> int:
	if _level_num > 0:
		return _level_num
	var manager: Node = get_tree().get_first_node_in_group("game_manager")
	if manager != null and manager.has_method("get_level_num"):
		return int(manager.get_level_num())
	return 1


func _build_level_profile() -> Dictionary:
	var lv: int = _get_current_level_num()
	var pipe_sets: Array = [
		[400.0, 800.0],
		[280.0, 620.0, 1050.0],
		[520.0, 980.0],
		[360.0, 720.0, 1280.0],
		[450.0, 900.0, 1550.0],
	]
	var pipe_idx: int = (lv - 1) % pipe_sets.size()
	var step_cycle: float = 120.0 + float((lv - 1) % 4) * 35.0
	return {
		"pipe_miaoda_x": pipe_sets[pipe_idx],
		"miaoda_step": step_cycle,
		"miaoda_start": 480.0 + float(lv % 4) * 60.0,
		"miaoda_end_offset": 240.0 + float(lv % 3) * 80.0,
		"block_chance": minf(0.88, 0.50 + float(lv) * 0.06),
		"coin_chance": minf(0.78, 0.38 + float(lv) * 0.05),
		"enemy_chance": minf(0.82, 0.35 + float(lv) * 0.07),
		"high_coin_chance": 0.12 + float(lv % 4) * 0.08,
		"elevated_block_rows": mini(2, 1 + (lv - 1) / 2),
		"bg_tint": BG_TINTS[(lv - 1) % BG_TINTS.size()],
	}


func _read_floor_from_config() -> void:
	var level_cfg: Dictionary = GameConfig.get_tuning().get("level", {}) as Dictionary
	_floor_top_y = float(level_cfg.get("floor_y", GODOT_VIEW_H - TILE))
	_ground_center_y = _floor_top_y + TILE * 0.5


func _get_level_width() -> float:
	var tuning: Dictionary = GameConfig.get_tuning()
	var level_cfg: Dictionary = tuning.get("level", {}) as Dictionary
	var mult: float = float(level_cfg.get("width_multiplier", 3.0))
	return get_viewport().get_visible_rect().size.x * mult


func _miaoda_x_to_godot(miaoda_x: float, level_width: float) -> float:
	var miaoda_level_w: float = MIAODA_VIEW_W * MIAODA_LEVEL_MULT
	return miaoda_x * level_width / miaoda_level_w


func _miaoda_y_to_godot(miaoda_y: float) -> float:
	return miaoda_y / MIAODA_VIEW_H * GODOT_VIEW_H


func _build_background(level_width: float) -> void:
	var bg: Sprite2D = $Background as Sprite2D
	var theme: Dictionary = GameConfig.get_theme()
	var path: String = str(theme.get("background_sprite", ""))
	bg.texture = ThemeSpriteUtil.load_texture(path, Color(0.36, 0.58, 0.99, 1.0), Vector2i(64, 64))
	bg.centered = false
	bg.position = Vector2.ZERO
	bg.scale = Vector2(level_width / 64.0, GODOT_VIEW_H / 64.0)
	bg.modulate = _level_profile.get("bg_tint", Color.WHITE) as Color


func _build_ground(level_width: float) -> void:
	var tile_tex: Texture2D = ThemeSpriteUtil.load_texture("", GROUND_COLOR, Vector2i(32, 32))
	var visuals: Node2D = Node2D.new()
	visuals.name = "GroundVisuals"
	var x: float = 0.0
	while x < level_width:
		var sprite: Sprite2D = Sprite2D.new()
		sprite.texture = tile_tex
		sprite.centered = true
		sprite.position = Vector2(x + TILE * 0.5, _ground_center_y)
		visuals.add_child(sprite)
		x += TILE
	_platforms_root.add_child(visuals)

	var body: StaticBody2D = StaticBody2D.new()
	body.name = "GroundCollider"
	body.position = Vector2(level_width * 0.5, _ground_center_y)
	_configure_world_body(body)
	var shape: CollisionShape2D = CollisionShape2D.new()
	var rect: RectangleShape2D = RectangleShape2D.new()
	rect.size = Vector2(level_width, TILE)
	shape.shape = rect
	body.add_child(shape)
	_platforms_root.add_child(body)


func _configure_world_body(body: StaticBody2D) -> void:
	body.collision_layer = 2
	body.collision_mask = 0


func _build_pipes() -> void:
	var level_width: float = _get_level_width()
	var pipe_x_list: Array = _level_profile.get("pipe_miaoda_x", [400.0, 800.0]) as Array
	for miaoda_x_variant: Variant in pipe_x_list:
		var miaoda_x: float = float(miaoda_x_variant)
		var gx: float = _miaoda_x_to_godot(miaoda_x, level_width)
		var center_y: float = _floor_top_y - PIPE_H * 0.5
		_add_pipe(Vector2(gx, center_y))


func _add_pipe(pos: Vector2) -> void:
	var body: StaticBody2D = StaticBody2D.new()
	body.position = pos
	_configure_world_body(body)
	var shape: CollisionShape2D = CollisionShape2D.new()
	var rect: RectangleShape2D = RectangleShape2D.new()
	rect.size = Vector2(PIPE_W, PIPE_H)
	shape.shape = rect
	body.add_child(shape)
	var sprite: Sprite2D = Sprite2D.new()
	sprite.texture = ThemeSpriteUtil.load_texture("", PIPE_COLOR, Vector2i(int(PIPE_W), int(PIPE_H)))
	sprite.centered = true
	body.add_child(sprite)
	_props_root.add_child(body)
	_register_spawn_blocker(Rect2(pos.x - PIPE_W * 0.5, pos.y - PIPE_H * 0.5, PIPE_W, PIPE_H))
	_register_turret_anchor(Vector2(pos.x, pos.y - PIPE_H * 0.5))


func _build_procedural_content(level_width: float) -> void:
	var rng: RandomNumberGenerator = RandomNumberGenerator.new()
	rng.seed = _get_level_seed()
	var miaoda_start: float = float(_level_profile.get("miaoda_start", 600.0))
	var miaoda_end: float = (
		MIAODA_VIEW_W * MIAODA_LEVEL_MULT
		- float(_level_profile.get("miaoda_end_offset", 300.0))
	)
	var miaoda_step: float = float(_level_profile.get("miaoda_step", 150.0))
	var block_chance: float = float(_level_profile.get("block_chance", 0.7))
	var coin_chance: float = float(_level_profile.get("coin_chance", 0.6))
	var enemy_chance: float = float(_level_profile.get("enemy_chance", 0.5))
	var high_coin_chance: float = float(_level_profile.get("high_coin_chance", 0.2))
	var elevated_rows: int = int(_level_profile.get("elevated_block_rows", 1))
	var x_m: float = miaoda_start
	while x_m < miaoda_end:
		var gx: float = _miaoda_x_to_godot(x_m, level_width)
		if rng.randf() < block_chance:
			_add_block(Vector2(gx, _miaoda_y_to_godot(MIAODA_VIEW_H - 150.0)))
			for row: int in range(1, elevated_rows):
				if rng.randf() < 0.45:
					var extra_y: float = MIAODA_VIEW_H - 150.0 - float(row) * 64.0
					_add_block(Vector2(gx + float(row) * 20.0, _miaoda_y_to_godot(extra_y)))
		if rng.randf() < coin_chance:
			_add_coin(Vector2(
				_miaoda_x_to_godot(x_m + 30.0, level_width),
				_miaoda_y_to_godot(MIAODA_VIEW_H - 100.0)
			))
		elif rng.randf() < high_coin_chance:
			_add_coin(Vector2(gx, _miaoda_y_to_godot(MIAODA_VIEW_H - 200.0)))
		if rng.randf() < enemy_chance:
			_try_add_enemy(_miaoda_x_to_godot(x_m + 50.0, level_width), rng)
		x_m += miaoda_step
	_spawn_guaranteed_new_enemies(rng, level_width)


func _spawn_guaranteed_new_enemies(rng: RandomNumberGenerator, level_width: float) -> void:
	var lv: int = _get_current_level_num()
	if lv < 4:
		return
	var kinds: Array[StringName] = []
	if lv >= 4:
		kinds.append_array([&"tough", &"tough"])
	if lv >= 5:
		kinds.append_array([&"jumper", &"jumper"])
	if lv >= 6:
		kinds.append(&"tough")
	for kind: StringName in kinds:
		for _attempt: int in range(16):
			var x: float = rng.randf_range(360.0, level_width - 100.0)
			if not _is_safe_enemy_spawn(x):
				continue
			_add_enemy_by_kind(kind, Vector2(x, _floor_top_y))
			break


func _register_turret_anchor(anchor: Vector2) -> void:
	_turret_anchors.append(anchor)


func _pick_enemy_kind(rng: RandomNumberGenerator) -> StringName:
	var lv: int = _get_current_level_num()
	if lv <= 3:
		return &"patrol"
	var tough_w: float = clampf(0.28 + float(lv - 4) * 0.06, 0.0, 0.40)
	var jumper_w: float = 0.0
	if lv >= 5:
		jumper_w = clampf(0.22 + float(lv - 5) * 0.05, 0.0, 0.35)
	elif lv >= 4:
		tough_w = maxf(tough_w, 0.35)
	var patrol_w: float = maxf(0.25, 1.0 - tough_w - jumper_w)
	var total: float = patrol_w + tough_w + jumper_w
	var roll: float = rng.randf() * total
	if roll < tough_w:
		return &"tough"
	roll -= tough_w
	if roll < jumper_w:
		return &"jumper"
	return &"patrol"


func _spawn_turret_enemies() -> void:
	var lv: int = _get_current_level_num()
	if lv < 5 or _turret_anchors.is_empty():
		return
	var rng: RandomNumberGenerator = RandomNumberGenerator.new()
	rng.seed = _get_level_seed() + 9001
	var count: int = mini(3, 1 + (lv - 5))
	var anchors: Array[Vector2] = _turret_anchors.duplicate()
	for i: int in range(anchors.size() - 1, 0, -1):
		var j: int = rng.randi_range(0, i)
		var tmp: Vector2 = anchors[i]
		anchors[i] = anchors[j]
		anchors[j] = tmp
	for i: int in range(mini(count, anchors.size())):
		_add_turret(anchors[i])


func _register_spawn_blocker(rect: Rect2) -> void:
	_spawn_blockers.append(rect)


func _enemy_spawn_rect(x: float) -> Rect2:
	var top_y: float = _floor_top_y - ENEMY_BODY_H
	return Rect2(x - ENEMY_HALF_W, top_y, ENEMY_HALF_W * 2.0, ENEMY_BODY_H)


func _is_safe_enemy_spawn(x: float) -> bool:
	var spawn_rect: Rect2 = _enemy_spawn_rect(x)
	for blocker: Rect2 in _spawn_blockers:
		if spawn_rect.intersects(blocker):
			return false
	return true


func _try_add_enemy(x: float, rng: RandomNumberGenerator) -> void:
	if not _is_safe_enemy_spawn(x):
		return
	var kind: StringName = _pick_enemy_kind(rng)
	_add_enemy_by_kind(kind, Vector2(x, _floor_top_y))


func _add_enemy_by_kind(kind: StringName, pos: Vector2) -> void:
	var scene: PackedScene = ENEMY_SCENE
	match kind:
		&"tough":
			scene = TOUGH_SCENE
		&"jumper":
			scene = JUMPER_SCENE
		_:
			scene = ENEMY_SCENE
	var enemy: CharacterBody2D = scene.instantiate() as CharacterBody2D
	enemy.position = pos
	_enemies_root.add_child(enemy)
	if enemy.has_method("configure_spawn"):
		enemy.configure_spawn(_floor_top_y, -1 if pos.x > 400.0 else 1)
	enemy.call_deferred("snap_to_floor")


func _add_turret(anchor: Vector2) -> void:
	var spawn_rect: Rect2 = _enemy_spawn_rect(anchor.x)
	for blocker: Rect2 in _spawn_blockers:
		if spawn_rect.intersects(blocker):
			return
	var enemy: CharacterBody2D = TURRET_SCENE.instantiate() as CharacterBody2D
	enemy.position = anchor
	_enemies_root.add_child(enemy)
	if enemy.has_method("configure_anchor"):
		enemy.configure_anchor(anchor)
	enemy.call_deferred("snap_to_floor")
	_register_spawn_blocker(Rect2(anchor.x - ENEMY_HALF_W, anchor.y - ENEMY_BODY_H, ENEMY_HALF_W * 2.0, ENEMY_BODY_H))


func _get_level_seed() -> int:
	var base_seed: int = 20260623
	var lv: int = _get_current_level_num()
	return base_seed + lv * 10007


func _add_block(pos: Vector2) -> void:
	var block: StaticBody2D = BLOCK_SCENE.instantiate() as StaticBody2D
	block.position = pos
	if block.has_signal("coin_spawned"):
		block.coin_spawned.connect(_on_block_coin_spawned)
	_props_root.add_child(block)
	_register_spawn_blocker(Rect2(pos.x - 14.0, pos.y - 12.0, 28.0, 24.0))
	_register_turret_anchor(Vector2(pos.x, pos.y - 12.0))


func _on_block_coin_spawned(world_pos: Vector2) -> void:
	_add_coin(world_pos)


func _add_coin(pos: Vector2) -> void:
	var coin: Area2D = COLLECTIBLE_SCENE.instantiate() as Area2D
	coin.position = pos
	_collectibles_root.add_child(coin)
	_register_collectible_with_manager(coin)


func _register_collectible_with_manager(collectible: Area2D) -> void:
	var manager: Node = get_tree().get_first_node_in_group("game_manager")
	if manager != null and manager.has_method("register_collectible"):
		manager.register_collectible(collectible)


func _add_enemy(pos: Vector2) -> void:
	_add_enemy_by_kind(&"patrol", pos)


func _build_goal(level_width: float) -> void:
	var goal: Area2D = GOAL_SCENE.instantiate() as Area2D
	var gx: float = _miaoda_x_to_godot(MIAODA_VIEW_W * MIAODA_LEVEL_MULT - 100.0, level_width)
	var gy: float = _miaoda_y_to_godot(MIAODA_VIEW_H - 64.0)
	goal.position = Vector2(gx, gy)
	_props_root.add_child(goal)


func _register_with_manager() -> void:
	var manager: Node = get_tree().get_first_node_in_group("game_manager")
	var player: CharacterBody2D = $Player as CharacterBody2D
	if manager == null:
		return
	if player != null and manager.has_method("register_player"):
		manager.register_player(player)
	var spawn: Marker2D = $SpawnPoint as Marker2D
	if spawn != null and player != null:
		player.global_position = spawn.global_position
		player.velocity = Vector2.ZERO
		if player.has_method("set_spawn_position"):
			player.set_spawn_position(spawn.global_position)
		if player.has_method("snap_to_floor"):
			player.snap_to_floor()
	for child: Node in _collectibles_root.get_children():
		if child is Area2D:
			_register_collectible_with_manager(child as Area2D)
	for child: Node in _enemies_root.get_children():
		if child is CharacterBody2D and manager.has_method("register_enemy"):
			manager.register_enemy(child as CharacterBody2D)
	for child: Node in _props_root.get_children():
		if child is Area2D and child.has_signal("reached") and manager.has_method("register_goal"):
			manager.register_goal(child as Area2D)
