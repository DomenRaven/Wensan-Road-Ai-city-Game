extends Area2D

const RacingViewportScript := preload("res://core/racing_viewport.gd")

var _scroll_speed: float = 0.0
var _hit_severity: float = 0.1

@onready var _sprite: Sprite2D = $Sprite2D


func _ready() -> void:
	add_to_group("road_obstacle")
	monitoring = true
	monitorable = true
	collision_mask = 1
	area_entered.connect(_on_area_entered)
	_build_cone_texture()


func _build_cone_texture() -> void:
	var img: Image = Image.create(40, 40, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	for y: int in range(40):
		for x: int in range(40):
			var nx: float = float(x) / 39.0
			var ny: float = float(y) / 39.0
			if ny >= 0.35:
				var half_width: float = ny * 0.5
				if nx >= 0.5 - half_width and nx <= 0.5 + half_width:
					img.set_pixel(x, y, Color(1.0, 0.27, 0.0, 1.0))
			if y >= 15 and y <= 24 and x >= 8 and x <= 31:
				img.set_pixel(x, y, Color(1.0, 1.0, 1.0, 1.0))
	_sprite.texture = ImageTexture.create_from_image(img)


func setup_scroll(player_speed: float) -> void:
	_scroll_speed = player_speed


func update_motion(delta: float, player_speed: float) -> void:
	position.y += player_speed * delta
	if position.y > RacingViewportScript.HEIGHT + 200.0:
		queue_free()


func _on_area_entered(area: Area2D) -> void:
	var player: Node = area.get_parent()
	if player == null or not player.is_in_group("player"):
		return
	if player.has_method("trigger_hit"):
		player.call("trigger_hit", _hit_severity)
	queue_free()
