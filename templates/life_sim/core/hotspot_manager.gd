extends RefCounted
class_name HotspotManager


static func bind(area: Area2D, callback: Callable) -> void:
	area.input_pickable = true
	if not area.input_event.is_connected(callback):
		area.input_event.connect(callback)


static func set_highlight(area: Area2D, active: bool) -> void:
	var sprite: Sprite2D = area.get_node_or_null("Sprite") as Sprite2D
	if sprite == null:
		return
	sprite.modulate = Color(1.15, 1.15, 1.0, 1.0) if active else Color.WHITE
