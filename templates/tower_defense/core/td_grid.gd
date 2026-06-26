extends RefCounted
class_name TdGrid

const PathValidatorScript: GDScript = preload("res://core/path_validator.gd")

## Core locked: cell_size=64, placement_rule=path_adjacent_only

const CELL_SIZE: int = 64
const PLACEMENT_RULE: String = "path_adjacent_only"
const GRID_COLS: int = 12
const GRID_ROWS: int = 8

var path_cells: Array[Vector2i] = []
var buildable_cells: Array[Vector2i] = []
var tower_cells: Dictionary = {}


func setup_path(cells: Array[Vector2i]) -> void:
	path_cells = cells
	buildable_cells.clear()
	tower_cells.clear()
	for cell: Vector2i in path_cells:
		for offset: Vector2i in _neighbor_offsets():
			if _is_inside_grid(offset) and not _is_path_cell(offset):
				if offset not in buildable_cells:
					buildable_cells.append(offset)
	if not PathValidatorScript.is_path_connected(path_cells):
		push_warning("TdGrid: path spawn→exit disconnected")


func can_place_tower(cell: Vector2i) -> bool:
	if PLACEMENT_RULE != "path_adjacent_only":
		return false
	if cell not in buildable_cells:
		return false
	return not tower_cells.has(cell)


func register_tower(cell: Vector2i, tower: Node2D) -> void:
	tower_cells[cell] = tower


func unregister_tower(cell: Vector2i) -> void:
	tower_cells.erase(cell)


func get_tower(cell: Vector2i) -> Node2D:
	if tower_cells.has(cell):
		return tower_cells[cell] as Node2D
	return null


func grid_to_world(cell: Vector2i) -> Vector2:
	var half: float = float(CELL_SIZE) * 0.5
	return Vector2(
		float(cell.x * CELL_SIZE) + half,
		float(cell.y * CELL_SIZE) + half
	)


func world_to_grid(world_pos: Vector2) -> Vector2i:
	return Vector2i(
		int(floor(world_pos.x / float(CELL_SIZE))),
		int(floor(world_pos.y / float(CELL_SIZE)))
	)


func is_path_cell(cell: Vector2i) -> bool:
	return _is_path_cell(cell)


func _is_path_cell(cell: Vector2i) -> bool:
	return cell in path_cells


func _is_inside_grid(cell: Vector2i) -> bool:
	return cell.x >= 0 and cell.x < GRID_COLS and cell.y >= 0 and cell.y < GRID_ROWS


func _neighbor_offsets() -> Array[Vector2i]:
	return [
		Vector2i(1, 0), Vector2i(-1, 0),
		Vector2i(0, 1), Vector2i(0, -1),
	]
