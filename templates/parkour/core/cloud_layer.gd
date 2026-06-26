extends Node2D

const VIEW_W: float = 640.0
const CLOUD_COUNT: int = 5
const ParkourTexturesUtil := preload("res://core/parkour_textures.gd")

var _scroll_speed: float = 40.0

@onready var _root: Node2D = $Clouds


func setup() -> void:
	_build_clouds()


func set_scroll_speed(runner_speed: float) -> void:
	_scroll_speed = clampf(runner_speed * 0.15, 30.0, 80.0)


func _build_clouds() -> void:
	for child: Node in _root.get_children():
		child.queue_free()
	var tex: Texture2D = ParkourTexturesUtil.get_cloud_texture()
	for i: int in range(CLOUD_COUNT):
		var cloud: Sprite2D = Sprite2D.new()
		cloud.texture = tex
		cloud.modulate = Color(1, 1, 1, 0.6)
		cloud.position = Vector2(
			randf_range(0.0, VIEW_W),
			randf_range(40.0, 140.0)
		)
		_root.add_child(cloud)


func _process(delta: float) -> void:
	var shift: float = _scroll_speed * delta
	for child: Node in _root.get_children():
		var cloud: Sprite2D = child as Sprite2D
		if cloud == null:
			continue
		cloud.position.x -= shift
		if cloud.position.x < -120.0:
			cloud.position.x = VIEW_W + randf_range(40.0, 120.0)
			cloud.position.y = randf_range(40.0, 140.0)
