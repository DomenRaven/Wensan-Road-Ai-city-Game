extends Node2D

const GROUND_Y: float = 300.0
const TILE_COUNT: int = 12

var _scroll_speed: float = 240.0
var _tile_width: float = 64.0
var _tile_height: float = 24.0

@onready var _tiles_root: Node2D = $Tiles


func setup(scroll_speed: float, platform_texture: Texture2D) -> void:
	_scroll_speed = scroll_speed
	_build_tiles(platform_texture)


func set_scroll_speed(speed: float) -> void:
	_scroll_speed = speed


func _read_tile_size(texture: Texture2D) -> void:
	if texture != null:
		_tile_width = texture.get_width()
		_tile_height = texture.get_height()


func _ground_tile_y() -> float:
	# 贴图顶边 = 奔跑平面 y=GROUND_Y
	return GROUND_Y + _tile_height * 0.5


func _build_tiles(texture: Texture2D) -> void:
	for child: Node in _tiles_root.get_children():
		child.queue_free()
	_read_tile_size(texture)
	var tile_y: float = _ground_tile_y()
	for i: int in range(TILE_COUNT):
		var tile: Sprite2D = Sprite2D.new()
		tile.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		tile.position = Vector2(float(i) * _tile_width + _tile_width * 0.5, tile_y)
		if texture != null:
			tile.texture = texture
		_tiles_root.add_child(tile)


func _physics_process(delta: float) -> void:
	var shift: float = _scroll_speed * delta
	for i: int in range(_tiles_root.get_child_count()):
		var tile: Node2D = _tiles_root.get_child(i) as Node2D
		tile.position.x -= shift
		if tile.position.x <= -_tile_width * 0.5:
			var max_x: float = -INF
			for j: int in range(_tiles_root.get_child_count()):
				var other: Node2D = _tiles_root.get_child(j) as Node2D
				max_x = maxf(max_x, other.position.x)
			tile.position.x = max_x + _tile_width
