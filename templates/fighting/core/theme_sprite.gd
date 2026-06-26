extends RefCounted


static func apply_to_sprite(sprite: Sprite2D, path: String, fallback_color: Color) -> void:
	if path != "":
		var abs_path: String = path
		if path.begins_with("res://"):
			abs_path = ProjectSettings.globalize_path(path)
		if FileAccess.file_exists(abs_path):
			var img: Image = Image.load_from_file(abs_path)
			if img != null and not img.is_empty():
				sprite.texture = ImageTexture.create_from_image(img)
				return
	_apply_color_fallback(sprite, fallback_color)


static func _apply_color_fallback(sprite: Sprite2D, fallback_color: Color) -> void:
	var img: Image = Image.create(32, 48, false, Image.FORMAT_RGBA8)
	img.fill(fallback_color)
	sprite.texture = ImageTexture.create_from_image(img)
