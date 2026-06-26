extends RefCounted

static var _texture_cache: Dictionary = {}


static func apply_to_sprite(sprite: Sprite2D, path: String, fallback_color: Color) -> void:
	sprite.texture = load_texture(path, fallback_color, Vector2i(40, 64))


static func load_texture(path: String, fallback_color: Color, size: Vector2i) -> Texture2D:
	if path != "" and _texture_cache.has(path):
		return _texture_cache[path] as Texture2D
	var tex: Texture2D = _load_texture_uncached(path, fallback_color, size)
	if path != "":
		_texture_cache[path] = tex
	return tex


static func warmup_paths(paths: PackedStringArray) -> void:
	for path: String in paths:
		if path != "":
			load_texture(path, Color(0.5, 0.5, 0.5, 1.0), Vector2i(64, 64))


static func _load_texture_uncached(path: String, fallback_color: Color, size: Vector2i) -> Texture2D:
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
