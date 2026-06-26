extends RefCounted

static var _cache: Dictionary = {}
static var _bullet_tex: Texture2D = null


static func load_texture(path: String) -> Texture2D:
	if path == "":
		return null
	if _cache.has(path):
		return _cache[path] as Texture2D
	var tex: Texture2D = null
	if ResourceLoader.exists(path):
		tex = load(path) as Texture2D
	if tex == null:
		var disk_path: String = path
		if path.begins_with("res://"):
			disk_path = ProjectSettings.globalize_path(path)
		if FileAccess.file_exists(disk_path):
			var img: Image = Image.new()
			if img.load(disk_path) == OK:
				tex = ImageTexture.create_from_image(img)
	if tex != null:
		_cache[path] = tex
	else:
		push_warning("SurvivorSpriteUtil: cannot load %s" % path)
	return tex


static func bullet_texture() -> Texture2D:
	if _bullet_tex != null:
		return _bullet_tex
	var img: Image = Image.create(10, 10, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	for x: int in 10:
		for y: int in 10:
			var dx: float = float(x) - 4.5
			var dy: float = float(y) - 4.5
			if dx * dx + dy * dy <= 16.0:
				img.set_pixel(x, y, Color(1.0, 0.82, 0.15, 1.0))
	_bullet_tex = ImageTexture.create_from_image(img)
	return _bullet_tex


static func apply_sprite(sprite: Sprite2D, path: String, scale_factor: Vector2 = Vector2.ONE) -> void:
	if sprite == null:
		return
	var tex: Texture2D = load_texture(path)
	if tex != null:
		sprite.texture = tex
	sprite.scale = scale_factor


static func apply_bullet_sprite(sprite: Sprite2D, scale_factor: float = 1.0) -> void:
	if sprite == null:
		return
	sprite.texture = bullet_texture()
	sprite.scale = Vector2(scale_factor, scale_factor)
	sprite.modulate = Color(1.0, 0.95, 0.35, 1.0)


static func apply_facing_flip(sprite: Sprite2D, direction: Vector2) -> void:
	if sprite == null or direction.length_squared() < 0.0001:
		return
	if direction.x < -0.01:
		sprite.flip_h = true
	elif direction.x > 0.01:
		sprite.flip_h = false


static func pick_enemy_sprite_path() -> String:
	var theme: Dictionary = GameConfig.get_theme()
	if theme.has("enemy_sprites") and theme["enemy_sprites"] is Array:
		var sprites: Array = theme["enemy_sprites"] as Array
		if not sprites.is_empty():
			return str(sprites[randi() % sprites.size()])
	return str(theme.get("enemy_sprite", ""))
