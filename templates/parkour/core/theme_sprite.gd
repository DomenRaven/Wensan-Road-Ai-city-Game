extends RefCounted


static func apply_to_sprite(sprite: Sprite2D, path: String, fallback_color: Color) -> void:
	sprite.texture = load_texture(path, fallback_color, Vector2i(32, 48))


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


static func _create_color_texture(fallback_color: Color, size: Vector2i) -> Texture2D:
	var img: Image = Image.create(size.x, size.y, false, Image.FORMAT_RGBA8)
	img.fill(fallback_color)
	return ImageTexture.create_from_image(img)
