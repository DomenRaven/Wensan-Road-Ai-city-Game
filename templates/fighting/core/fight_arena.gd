extends Node2D

const FightConstants := preload("res://core/fight_constants.gd")
const WarriorSheet := preload("res://core/warrior_sheet.gd")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")
const FightInput := preload("res://core/fight_input.gd")

const PLAYER_SCENE: PackedScene = preload("res://scenes/player.tscn")

signal match_over(player_one_won: bool, is_draw: bool)

var _game_manager: Node = null
var _game_mode: String = "pve"
var _player_role: String = "Warrior_2"
var _enemy_role: String = "Warrior_3"
var _is_over: bool = false

var _player_hp: int = 100
var _enemy_hp: int = 100
var _player_mp: int = 0
var _enemy_mp: int = 0
var _max_hp: int = 100
var _max_mp: int = 100
var _ultimate_busy: bool = false
var _cutscene_active: bool = false

@onready var _player: CharacterBody2D = $Player
@onready var _enemy: CharacterBody2D = $Enemy
@onready var _background: ColorRect = $Background
@onready var _floor_line: ColorRect = $FloorLine
@onready var _fx_layer: Node2D = $FxLayer
@onready var _camera: Camera2D = $Camera2D


func setup(
	game_manager: Node,
	game_mode: String,
	player_role: String,
	enemy_role: String
) -> void:
	_game_manager = game_manager
	_game_mode = game_mode
	_player_role = player_role
	_enemy_role = enemy_role
	_resolve_fighters()
	_apply_theme()
	_load_combat_values()
	_configure_fighters()
	_reset_bars()
	if _camera != null:
		_camera.make_current()
	_player.call("set_round_active", true)
	_enemy.call("set_round_active", true)


func _resolve_fighters() -> void:
	_player = get_node_or_null("Player") as CharacterBody2D
	_enemy = get_node_or_null("Enemy") as CharacterBody2D
	_background = get_node_or_null("Background") as ColorRect
	_floor_line = get_node_or_null("FloorLine") as ColorRect
	_fx_layer = get_node_or_null("FxLayer") as Node2D
	_camera = get_node_or_null("Camera2D") as Camera2D


func _apply_theme() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var bottom: Color = Color.from_string(str(theme.get("bg_bottom", "#0D113A")), Color(0.05, 0.07, 0.23))
	var floor_surface: float = FightConstants.floor_surface_y()
	if _background != null:
		_background.color = bottom
	if _floor_line != null:
		_floor_line.color = Color.from_string(str(theme.get("floor_color", "#FF5722")), Color(1.0, 0.34, 0.13))
		_floor_line.position = Vector2(0.0, floor_surface)
		_floor_line.size = Vector2(640.0, 4.0)
	var floor_body: StaticBody2D = get_node_or_null("Floor") as StaticBody2D
	if floor_body != null:
		floor_body.position = Vector2(320.0, floor_surface + 12.0)


func _load_combat_values() -> void:
	var combat: Dictionary = FightConstants.combat_cfg()
	_max_hp = int(combat.get("max_hp", 100))
	_max_mp = int(combat.get("max_mp", 100))
	_player_hp = _max_hp
	_enemy_hp = _max_hp
	_player_mp = 0
	_enemy_mp = 0


func _configure_fighters() -> void:
	var arena_w: float = 640.0
	var floor_y: float = FightConstants.fighter_body_y()
	var spawn_left: float = arena_w * (200.0 / 960.0)
	var spawn_right: float = arena_w * (760.0 / 960.0)
	if _game_mode == "pvp":
		var old_enemy: Node = _enemy
		var parent: Node = old_enemy.get_parent()
		var spawn_pos: Vector2 = old_enemy.position
		parent.remove_child(old_enemy)
		old_enemy.queue_free()
		var p2_scene: PackedScene = PLAYER_SCENE
		_enemy = p2_scene.instantiate() as CharacterBody2D
		_enemy.name = "Enemy"
		_enemy.position = spawn_pos
		parent.add_child(_enemy)
	_player.call("configure", _player_role, true, spawn_left, 1, arena_w, floor_y)
	_enemy.call("configure", _enemy_role, false, spawn_right, -1, arena_w, floor_y)
	_player.call("set_opponent", _enemy)
	_enemy.call("set_opponent", _player)
	_player.call("set_arena", self)
	_enemy.call("set_arena", self)
	WarriorSheet.warmup(_player_role)
	WarriorSheet.warmup(_enemy_role)


func _reset_bars() -> void:
	_push_hud()


func _physics_process(_delta: float) -> void:
	if _is_over or _cutscene_active:
		return
	if _game_mode == "pvp":
		_handle_p2_input()
	else:
		pass
	_handle_p1_input()
	if _game_mode == "pvp":
		FightInput.end_physics_frame()


func _handle_p1_input() -> void:
	_player.call(
		"handle_input",
		Input.is_action_pressed("p1_left"),
		Input.is_action_pressed("p1_right"),
		Input.is_action_just_pressed("p1_left"),
		Input.is_action_just_pressed("p1_right"),
		Input.is_action_just_pressed("p1_light"),
		Input.is_action_just_pressed("p1_heavy"),
		Input.is_action_pressed("p1_block"),
		Input.is_action_just_pressed("p1_ultimate")
	)


func _handle_p2_input() -> void:
	var just_light: bool = Input.is_action_just_pressed("p2_light") or FightInput.numpad_just(KEY_KP_1)
	var just_heavy: bool = Input.is_action_just_pressed("p2_heavy") or FightInput.numpad_just(KEY_KP_2)
	var block_held: bool = Input.is_action_pressed("p2_block") or FightInput.numpad_held(KEY_KP_3)
	var just_ultimate: bool = Input.is_action_just_pressed("p2_ultimate") or FightInput.numpad_just(KEY_KP_4)
	_enemy.call(
		"handle_input",
		Input.is_action_pressed("p2_left"),
		Input.is_action_pressed("p2_right"),
		Input.is_action_just_pressed("p2_left"),
		Input.is_action_just_pressed("p2_right"),
		just_light,
		just_heavy,
		block_held,
		just_ultimate
	)


func can_spend_mp(for_player_one: bool) -> bool:
	if for_player_one:
		return _player_mp >= _max_mp
	return _enemy_mp >= _max_mp


func spend_mp(for_player_one: bool) -> bool:
	if not can_spend_mp(for_player_one):
		return false
	if for_player_one:
		_player_mp = 0
	else:
		_enemy_mp = 0
	_push_hud()
	return true


func request_ultimate(source: CharacterBody2D) -> bool:
	if _ultimate_busy or _is_over or _cutscene_active:
		return false
	var is_p1: bool = source == _player
	if not can_spend_mp(is_p1):
		return false
	if not spend_mp(is_p1):
		return false
	_run_ultimate_sequence(source)
	return true


func _set_fighters_frozen(frozen: bool) -> void:
	if _player.has_method("set_combat_frozen"):
		_player.call("set_combat_frozen", frozen)
	if _enemy.has_method("set_combat_frozen"):
		_enemy.call("set_combat_frozen", frozen)


func _run_ultimate_sequence(source: CharacterBody2D) -> void:
	_ultimate_busy = true
	_cutscene_active = true
	_set_fighters_frozen(true)
	await _ultimate_intro_camera(source)
	_set_fighters_frozen(false)
	if source.has_method("begin_ultimate_visual"):
		source.call("begin_ultimate_visual")
	_play_ultimate_impact_fx(source)
	await _wait_ultimate_anim(source)
	await _ultimate_outro_camera()
	_ultimate_busy = false
	_cutscene_active = false


func _ultimate_intro_camera(source: Node2D) -> void:
	if _camera == null:
		return
	var home_pos: Vector2 = _camera.position
	var home_zoom: Vector2 = _camera.zoom
	var focus_pos: Vector2 = source.global_position + Vector2(0.0, -40.0)
	var ui_layer: CanvasLayer = CanvasLayer.new()
	ui_layer.layer = 20
	add_child(ui_layer)
	var dim: ColorRect = ColorRect.new()
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	dim.set_offsets_preset(Control.PRESET_FULL_RECT)
	dim.color = Color(0.0, 0.0, 0.0, 0.0)
	dim.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ui_layer.add_child(dim)
	_player.z_index = 30
	_enemy.z_index = 30
	source.z_index = 45
	var intro: Tween = create_tween()
	intro.set_parallel(true)
	intro.tween_property(_camera, "zoom", Vector2(1.55, 1.55), 0.16) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	intro.tween_property(_camera, "position", focus_pos, 0.16) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	intro.parallel().tween_property(dim, "color:a", 0.78, 0.16)
	await intro.finished
	_camera.set_meta("home_pos", home_pos)
	_camera.set_meta("home_zoom", home_zoom)
	_camera.set_meta("dim_layer", ui_layer)


func _ultimate_outro_camera() -> void:
	if _camera == null:
		return
	var home_pos: Vector2 = _camera.get_meta("home_pos", Vector2(320.0, 180.0))
	var home_zoom: Vector2 = _camera.get_meta("home_zoom", Vector2.ONE)
	var dim_layer: Node = _camera.get_meta("dim_layer", null)
	var outro: Tween = create_tween()
	outro.set_parallel(true)
	outro.tween_property(_camera, "zoom", home_zoom, 0.2)
	outro.tween_property(_camera, "position", home_pos, 0.2)
	if dim_layer != null and is_instance_valid(dim_layer):
		var dim: ColorRect = dim_layer.get_child(0) as ColorRect
		if dim != null:
			outro.parallel().tween_property(dim, "color:a", 0.0, 0.2)
	await outro.finished
	if dim_layer != null and is_instance_valid(dim_layer):
		dim_layer.queue_free()
	_player.z_index = 0
	_enemy.z_index = 0


func _wait_ultimate_anim(source: Node) -> void:
	while is_instance_valid(source):
		if source.has_method("is_ultimate_active"):
			if not bool(source.call("is_ultimate_active")):
				break
		else:
			break
		await get_tree().process_frame
	await get_tree().create_timer(0.12).timeout


func resolve_hit(attacker: Node, defender: Node, move_id: String) -> void:
	if _is_over:
		return
	var attacker_is_p1: bool = attacker == _player
	var defender_blocking: bool = false
	if defender.has_method("is_blocking"):
		defender_blocking = bool(defender.call("is_blocking"))
	var combat: Dictionary = FightConstants.combat_cfg()
	var raw_damage: int = int(combat.get("light_damage", 5))
	if move_id == "heavy":
		raw_damage = int(combat.get("heavy_damage", 15))
	elif move_id == "ultimate":
		raw_damage = int(combat.get("ultimate_damage", 30))
	var final_damage: int = raw_damage
	if defender_blocking:
		ThemeSoundUtil.play(self, "impact", "block")
		var reduction: float = float(combat.get("block_reduction_normal", 0.3))
		if move_id == "ultimate":
			reduction = float(combat.get("block_reduction_ultimate", 0.5))
		final_damage = int(floor(float(raw_damage) * reduction))
	else:
		ThemeSoundUtil.play(self, "impact", "hit")
	if attacker_is_p1:
		if defender_blocking:
			_enemy_mp = mini(_max_mp, _enemy_mp + int(combat.get("mp_gain_on_block", 5)))
		else:
			_player_mp = mini(_max_mp, _player_mp + int(combat.get("mp_gain_on_hit", 15)))
		_enemy_hp = maxi(0, _enemy_hp - final_damage)
	else:
		if defender_blocking:
			_player_mp = mini(_max_mp, _player_mp + int(combat.get("mp_gain_on_block", 5)))
		else:
			_enemy_mp = mini(_max_mp, _enemy_mp + int(combat.get("mp_gain_on_hit", 15)))
		_player_hp = maxi(0, _player_hp - final_damage)
	var knock_key: String = "knockback_light"
	if move_id == "ultimate":
		knock_key = "knockback_ultimate"
	var knockback: float = FightConstants.scale_x(float(combat.get(knock_key, 30.0)), 640.0)
	var from_right: bool = attacker.global_position.x > defender.global_position.x
	if defender.has_method("interrupt_dash"):
		defender.call("interrupt_dash")
	if defender.has_method("apply_hurt"):
		defender.call("apply_hurt", knockback, from_right)
	if move_id == "ultimate":
		_spawn_ultimate_hit_blast(defender.global_position)
		_camera_shake(0.45, 18.0)
		_flash_screen()
		_start_hitstop(0.1)
	_push_hud()
	_check_game_over()


func _check_game_over() -> void:
	if _player_hp <= 0 and _enemy_hp <= 0:
		_finish_match(false, true)
	elif _enemy_hp <= 0:
		_finish_match(true, false)
	elif _player_hp <= 0:
		_finish_match(false, false)


func _finish_match(player_one_won: bool, is_draw: bool) -> void:
	if _is_over:
		return
	_is_over = true
	_player.call("set_round_active", false)
	_enemy.call("set_round_active", false)
	if is_draw:
		pass
	elif player_one_won:
		if _enemy.has_method("apply_death"):
			_enemy.call("apply_death")
	else:
		if _player.has_method("apply_death"):
			_player.call("apply_death")
	await get_tree().create_timer(1.5).timeout
	match_over.emit(player_one_won, is_draw)


func trigger_ultimate_fx(source: Node2D) -> void:
	_play_ultimate_impact_fx(source)


func _play_ultimate_impact_fx(source: Node2D) -> void:
	if _camera == null:
		return
	var floor_surface: float = FightConstants.floor_surface_y()
	_camera_shake(0.5, 14.0)
	_spawn_shockwave(source.global_position)
	_spawn_particles(source.global_position, Color(1.0, 0.45, 0.05), 40)
	_spawn_particles(source.global_position, Color(1.0, 0.95, 0.3), 24)
	var ray: ColorRect = ColorRect.new()
	ray.color = Color(1.0, 1.0, 1.0, 0.95)
	ray.size = Vector2(18.0, 280.0)
	ray.position = source.global_position + Vector2(-9.0, -230.0)
	ray.z_index = 35
	ray.pivot_offset = Vector2(9.0, 140.0)
	_fx_layer.add_child(ray)
	var ray_tween: Tween = create_tween()
	ray_tween.tween_property(ray, "scale", Vector2(12.0, 1.2), 0.35) \
		.set_trans(Tween.TRANS_EXPO).set_ease(Tween.EASE_OUT)
	ray_tween.parallel().tween_property(ray, "modulate:a", 0.0, 0.45)
	ray_tween.finished.connect(ray.queue_free)
	await get_tree().create_timer(0.35).timeout
	_spawn_particles(Vector2(source.global_position.x, floor_surface), Color(0.65, 0.55, 0.45), 32)
	_spawn_shockwave(Vector2(source.global_position.x, floor_surface + 2.0), Color(0.9, 0.7, 0.3, 0.7))
	var crater: ColorRect = ColorRect.new()
	crater.color = Color(0.12, 0.12, 0.12, 1.0)
	crater.size = Vector2(64.0, 14.0)
	crater.position = Vector2(source.global_position.x - 32.0, floor_surface - 6.0)
	crater.z_index = 2
	_fx_layer.add_child(crater)
	var crater_fade: Tween = create_tween()
	crater_fade.tween_interval(2.0)
	crater_fade.tween_property(crater, "modulate:a", 0.0, 1.0)
	crater_fade.finished.connect(crater.queue_free)


func _spawn_shockwave(pos: Vector2, tint: Color = Color(1.0, 0.85, 0.4, 0.85)) -> void:
	var ring: ColorRect = ColorRect.new()
	ring.color = tint
	ring.size = Vector2(24.0, 8.0)
	ring.position = pos + Vector2(-12.0, -4.0)
	ring.z_index = 34
	ring.pivot_offset = Vector2(12.0, 4.0)
	_fx_layer.add_child(ring)
	var tween: Tween = create_tween()
	tween.tween_property(ring, "scale", Vector2(8.0, 2.5), 0.4) \
		.set_trans(Tween.TRANS_EXPO).set_ease(Tween.EASE_OUT)
	tween.parallel().tween_property(ring, "modulate:a", 0.0, 0.4)
	tween.finished.connect(ring.queue_free)


func _spawn_ultimate_hit_blast(pos: Vector2) -> void:
	var blast: ColorRect = ColorRect.new()
	blast.color = Color(1.0, 1.0, 1.0, 0.95)
	blast.size = Vector2(72.0, 72.0)
	blast.position = pos + Vector2(-36.0, -80.0)
	blast.z_index = 40
	blast.pivot_offset = Vector2(36.0, 36.0)
	_fx_layer.add_child(blast)
	var tween: Tween = create_tween()
	tween.tween_property(blast, "scale", Vector2(2.2, 2.2), 0.18) \
		.set_trans(Tween.TRANS_EXPO).set_ease(Tween.EASE_OUT)
	tween.parallel().tween_property(blast, "modulate:a", 0.0, 0.22)
	tween.finished.connect(blast.queue_free)
	_spawn_shockwave(pos, Color(1.0, 0.9, 0.5, 0.9))


func _flash_screen() -> void:
	var flash: ColorRect = ColorRect.new()
	flash.set_anchors_preset(Control.PRESET_FULL_RECT)
	flash.set_offsets_preset(Control.PRESET_FULL_RECT)
	flash.color = Color(1.0, 1.0, 1.0, 0.55)
	flash.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var layer: CanvasLayer = CanvasLayer.new()
	layer.layer = 25
	add_child(layer)
	layer.add_child(flash)
	var tween: Tween = create_tween()
	tween.tween_property(flash, "color:a", 0.0, 0.14)
	tween.finished.connect(layer.queue_free)


func _start_hitstop(duration: float) -> void:
	_hitstop_async(duration)


func _hitstop_async(duration: float) -> void:
	Engine.time_scale = 0.06
	await get_tree().create_timer(duration, true, true, true).timeout
	Engine.time_scale = 1.0


func _apply_hitstop(duration: float) -> void:
	_start_hitstop(duration)


func _spawn_hit_blast(pos: Vector2) -> void:
	var blast: ColorRect = ColorRect.new()
	blast.color = Color(1.0, 0.92, 0.23, 0.8)
	blast.size = Vector2(40.0, 40.0)
	blast.position = pos + Vector2(-20.0, -60.0)
	blast.z_index = 12
	_fx_layer.add_child(blast)
	var tween: Tween = create_tween()
	tween.tween_property(blast, "modulate:a", 0.0, 0.3)
	tween.parallel().tween_property(blast, "scale", Vector2(1.5, 1.5), 0.3)
	tween.finished.connect(blast.queue_free)


func _spawn_particles(pos: Vector2, tint: Color, count: int) -> void:
	for i: int in range(count):
		var p: ColorRect = ColorRect.new()
		p.color = tint
		p.size = Vector2(6.0, 6.0)
		p.position = pos
		p.z_index = 12
		_fx_layer.add_child(p)
		var angle: float = randf() * TAU
		var dist: float = randf_range(30.0, 90.0)
		var tween: Tween = create_tween()
		tween.tween_property(p, "position", pos + Vector2(cos(angle), sin(angle)) * dist, 0.5)
		tween.parallel().tween_property(p, "modulate:a", 0.0, 0.5)
		tween.finished.connect(p.queue_free)


func _camera_shake(duration: float, strength: float) -> void:
	var tween: Tween = create_tween()
	var steps: int = int(duration * 20.0)
	for i: int in range(steps):
		var offset: Vector2 = Vector2(randf_range(-1.0, 1.0), randf_range(-1.0, 1.0)) * strength
		tween.tween_property(_camera, "offset", offset, duration / float(steps))
	tween.tween_property(_camera, "offset", Vector2.ZERO, 0.05)


func _push_hud() -> void:
	if _game_manager != null and _game_manager.has_method("update_battle_hud"):
		_game_manager.call(
			"update_battle_hud",
			_player_hp,
			_max_hp,
			_enemy_hp,
			_max_hp,
			_player_mp,
			_max_mp,
			_enemy_mp,
			_max_mp
		)
