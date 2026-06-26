extends Node2D

const TdCombatClass: GDScript = preload("res://core/td_combat.gd")
const TdGridClass: GDScript = preload("res://core/td_grid.gd")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")

var grid_cell: Vector2i = Vector2i.ZERO
var attack: int = 15
var range_tiles: int = 3
var max_hp: int = 100
var hp: int = 100
var fire_interval_sec: float = 0.6

var _fire_timer: float = 0.0
var _enemies_root: Node2D = null


func set_grid_cell(cell: Vector2i) -> void:
	grid_cell = cell


func configure(
	p_attack: int,
	p_range: int,
	p_fire_interval_ms: int,
	sprite_path: String,
	p_enemies_root: Node2D
) -> void:
	attack = p_attack
	range_tiles = p_range
	fire_interval_sec = float(p_fire_interval_ms) / 1000.0
	_enemies_root = p_enemies_root
	max_hp = 100
	hp = max_hp
	_apply_sprite(sprite_path)


func _apply_sprite(sprite_path: String) -> void:
	var sprite: Sprite2D = $Sprite as Sprite2D
	if sprite == null:
		return
	if sprite_path != "" and ResourceLoader.exists(sprite_path):
		sprite.texture = load(sprite_path) as Texture2D


func _process(delta: float) -> void:
	if _enemies_root == null:
		return
	_fire_timer -= delta
	if _fire_timer > 0.0:
		return
	var target: Node2D = _find_target()
	if target == null:
		return
	_fire_timer = fire_interval_sec
	ThemeSoundUtil.play(self, "impact", "shoot")
	if target.has_method("take_damage"):
		target.call("take_damage", attack)


func repair_full() -> void:
	hp = max_hp


func _find_target() -> Node2D:
	var best: Node2D = null
	var best_progress: float = -1.0
	for child: Node in _enemies_root.get_children():
		if not child is Node2D:
			continue
		var enemy: Node2D = child as Node2D
		if not enemy.has_method("take_damage"):
			continue
		var enemy_cell: Vector2i = Vector2i.ZERO
		if enemy.has_method("_estimate_grid_cell"):
			enemy_cell = enemy.call("_estimate_grid_cell") as Vector2i
		else:
			enemy_cell = Vector2i(
				int(floor(enemy.position.x / float(TdGridClass.CELL_SIZE))),
				int(floor(enemy.position.y / float(TdGridClass.CELL_SIZE)))
			)
		if not TdCombatClass.is_in_tile_range(grid_cell, enemy_cell, range_tiles):
			continue
		var progress: float = 0.0
		if enemy.has_method("get_progress"):
			progress = float(enemy.call("get_progress"))
		if progress > best_progress:
			best_progress = progress
			best = enemy
	return best
