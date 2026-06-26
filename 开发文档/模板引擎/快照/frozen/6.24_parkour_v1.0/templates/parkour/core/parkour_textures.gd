extends RefCounted
class_name ParkourTextures

static var _cache: Dictionary = {}


static func get_obstacle_texture(variant: int) -> Texture2D:
	var key: String = "obs_%d" % variant
	if _cache.has(key):
		return _cache[key] as Texture2D
	var tex: Texture2D = null
	match variant:
		0:
			tex = _make_rect_texture(Vector2i(32, 64), Color(1.0, 0.6, 0.0, 1.0), Color(0.2, 0.2, 0.2, 1.0))
		1:
			tex = _make_rect_texture(Vector2i(48, 48), Color(0.96, 0.26, 0.21, 1.0), Color(0.2, 0.2, 0.2, 1.0))
		2:
			tex = _make_rect_texture(Vector2i(32, 96), Color(1.0, 0.6, 0.0, 1.0), Color(0.2, 0.2, 0.2, 1.0))
		3:
			tex = _make_rect_texture(Vector2i(64, 64), Color(0.61, 0.15, 0.69, 1.0), Color(0.2, 0.2, 0.2, 1.0))
		_:
			tex = _make_rect_texture(Vector2i(32, 64), Color(1.0, 0.6, 0.0, 1.0), Color(0.2, 0.2, 0.2, 1.0))
	_cache[key] = tex
	return tex


static func get_collectible_texture(kind: int) -> Texture2D:
	var key: String = "col_%d" % kind
	if _cache.has(key):
		return _cache[key] as Texture2D
	var tex: Texture2D = null
	match kind:
		0:
			tex = _make_circle_texture(32, Color(1.0, 0.84, 0.0, 1.0), Color(0.72, 0.53, 0.04, 1.0))
		1:
			tex = _make_circle_texture(32, Color(0.0, 0.74, 0.83, 1.0), Color(1.0, 1.0, 1.0, 1.0))
		2:
			tex = _make_circle_texture(32, Color(0.91, 0.12, 0.39, 1.0), Color(1.0, 1.0, 1.0, 1.0))
		_:
			tex = _make_circle_texture(32, Color(1.0, 0.84, 0.0, 1.0), Color(0.72, 0.53, 0.04, 1.0))
	_cache[key] = tex
	return tex


static func get_cloud_texture() -> Texture2D:
	if _cache.has("cloud"):
		return _cache["cloud"] as Texture2D
	var img: Image = Image.create(110, 60, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	for y: int in range(60):
		for x: int in range(110):
			var dx: float = float(x) - 55.0
			var dy: float = float(y) - 35.0
			if dx * dx / 900.0 + dy * dy / 400.0 <= 1.0:
				img.set_pixel(x, y, Color(1, 1, 1, 0.8))
	var tex: ImageTexture = ImageTexture.create_from_image(img)
	_cache["cloud"] = tex
	return tex


static func get_ground_texture() -> Texture2D:
	if _cache.has("ground"):
		return _cache["ground"] as Texture2D
	var img: Image = Image.create(64, 24, false, Image.FORMAT_RGBA8)
	img.fill(Color(0.3, 0.69, 0.31, 1.0))
	for x: int in range(64):
		img.set_pixel(x, 0, Color(0.22, 0.56, 0.24, 1.0))
	var tex: ImageTexture = ImageTexture.create_from_image(img)
	_cache["ground"] = tex
	return tex


static func _make_rect_texture(size: Vector2i, fill: Color, border: Color) -> Texture2D:
	var img: Image = Image.create(size.x, size.y, false, Image.FORMAT_RGBA8)
	img.fill(fill)
	for x: int in range(size.x):
		img.set_pixel(x, 0, border)
		img.set_pixel(x, size.y - 1, border)
	for y: int in range(size.y):
		img.set_pixel(0, y, border)
		img.set_pixel(size.x - 1, y, border)
	return ImageTexture.create_from_image(img)


static func _make_circle_texture(diameter: int, fill: Color, border: Color) -> Texture2D:
	var img: Image = Image.create(diameter, diameter, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	var center: float = float(diameter) * 0.5
	var radius: float = center - 2.0
	for y: int in range(diameter):
		for x: int in range(diameter):
			var dx: float = float(x) - center + 0.5
			var dy: float = float(y) - center + 0.5
			var dist: float = sqrt(dx * dx + dy * dy)
			if dist <= radius - 1.5:
				img.set_pixel(x, y, fill)
			elif dist <= radius:
				img.set_pixel(x, y, border)
	return ImageTexture.create_from_image(img)
