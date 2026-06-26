extends RefCounted


static func apply_to_sprite(sprite: Sprite2D, path: String, fallback_color: Color, size: Vector2i) -> void:
	sprite.texture = load_texture(path, fallback_color, size)


static func load_texture(path: String, fallback_color: Color, size: Vector2i) -> Texture2D:
	if path != "":
		var abs_path: String = path
		if path.begins_with("res://"):
			abs_path = ProjectSettings.globalize_path(path)
		if FileAccess.file_exists(abs_path):
			var img: Image = Image.load_from_file(abs_path)
			if img != null and not img.is_empty():
				return ImageTexture.create_from_image(img)
	return _create_color_texture(fallback_color, size)


static func parse_color(hex_or_name: String, fallback: Color) -> Color:
	if hex_or_name.is_empty():
		return fallback
	return Color.from_string(hex_or_name, fallback)


static func _create_color_texture(fallback_color: Color, size: Vector2i) -> Texture2D:
	var img: Image = Image.create(size.x, size.y, false, Image.FORMAT_RGBA8)
	img.fill(fallback_color)
	return ImageTexture.create_from_image(img)
