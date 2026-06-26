extends RefCounted
class_name TdPathValidator

## BFS: spawn → exit 沿 path_cells 四邻连通


static func is_path_connected(path_cells: Array[Vector2i]) -> bool:
	if path_cells.is_empty():
		return false
	var start: Vector2i = path_cells[0]
	var goal: Vector2i = path_cells[path_cells.size() - 1]
	var path_set: Dictionary = {}
	for cell: Vector2i in path_cells:
		path_set[cell] = true
	var visited: Dictionary = {}
	var queue: Array[Vector2i] = [start]
	visited[start] = true
	while not queue.is_empty():
		var current: Vector2i = queue.pop_front() as Vector2i
		if current == goal:
			return true
		for offset: Vector2i in _neighbor_offsets():
			var next: Vector2i = current + offset
			if not path_set.has(next) or visited.has(next):
				continue
			visited[next] = true
			queue.append(next)
	return false


static func _neighbor_offsets() -> Array[Vector2i]:
	return [
		Vector2i(1, 0), Vector2i(-1, 0),
		Vector2i(0, 1), Vector2i(0, -1),
	]
