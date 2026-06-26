extends Node2D

const TILE_WIDTH: float = 70.0
const GROUND_Y: float = 300.0
const TILE_COUNT: int = 11

var _scroll_speed: float = 240.0

@onready var _tiles_root: Node2D = $Tiles


func setup(scroll_speed: float, track_texture: Texture2D) -> void:
	_scroll_speed = scroll_speed
	_build_tiles(track_texture)


func set_scroll_speed(speed: float) -> void:
	_scroll_speed = speed


func _build_tiles(texture: Texture2D) -> void:
	for child: Node in _tiles_root.get_children():
		child.queue_free()
	for i: int in range(TILE_COUNT):
		var tile: Sprite2D = Sprite2D.new()
		tile.position = Vector2(float(i) * TILE_WIDTH + TILE_WIDTH * 0.5, GROUND_Y - 8)
		if texture != null:
			tile.texture = texture
		_tiles_root.add_child(tile)


func _physics_process(delta: float) -> void:
	var shift: float = _scroll_speed * delta
	for i: int in range(_tiles_root.get_child_count()):
		var tile: Node2D = _tiles_root.get_child(i) as Node2D
		tile.position.x -= shift
		if tile.position.x <= -TILE_WIDTH * 0.5:
			var max_x: float = -INF
			for j: int in range(_tiles_root.get_child_count()):
				var other: Node2D = _tiles_root.get_child(j) as Node2D
				max_x = maxf(max_x, other.position.x)
			tile.position.x = max_x + TILE_WIDTH
