extends RefCounted
class_name TowerPlacer

const PathValidatorClass: GDScript = preload("res://core/path_validator.gd")

signal tower_placed(cell: Vector2i, tower: Node2D)
signal tower_sold(cell: Vector2i, refund: int)
signal placement_failed(reason: String)

var grid: RefCounted = null
var towers_root: Node2D = null
var tower_scene: PackedScene = null
var tower_cost: int = 50


func setup(
	p_grid: RefCounted,
	p_towers_root: Node2D,
	p_tower_scene: PackedScene,
	p_cost: int
) -> void:
	grid = p_grid
	towers_root = p_towers_root
	tower_scene = p_tower_scene
	tower_cost = p_cost


func try_place_at_world(world_pos: Vector2, gold_available: int) -> Node2D:
	if grid == null or towers_root == null or tower_scene == null:
		placement_failed.emit("missing_setup")
		return null
	var cell: Vector2i = grid.world_to_grid(world_pos)
	if not grid.can_place_tower(cell):
		placement_failed.emit("invalid_cell")
		return null
	if gold_available < tower_cost:
		placement_failed.emit("not_enough_gold")
		return null
	var tower: Node2D = tower_scene.instantiate() as Node2D
	if tower == null:
		placement_failed.emit("spawn_failed")
		return null
	tower.position = grid.grid_to_world(cell)
	if tower.has_method("set_grid_cell"):
		tower.call("set_grid_cell", cell)
	towers_root.add_child(tower)
	grid.register_tower(cell, tower)
	tower_placed.emit(cell, tower)
	return tower


func try_sell_at_world(world_pos: Vector2, refund_ratio: float) -> int:
	if grid == null:
		return 0
	var cell: Vector2i = grid.world_to_grid(world_pos)
	var tower: Node2D = grid.get_tower(cell)
	if tower == null:
		return 0
	grid.unregister_tower(cell)
	tower.queue_free()
	var refund: int = int(round(float(tower_cost) * clampf(refund_ratio, 0.0, 1.0)))
	tower_sold.emit(cell, refund)
	return refund
