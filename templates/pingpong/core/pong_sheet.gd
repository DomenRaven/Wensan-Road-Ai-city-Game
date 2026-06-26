extends RefCounted

const ThemeSpriteUtil := preload("res://core/theme_sprite.gd")
const PNG_DIR: String = "res://assets/pong-football/pong-football/assets/png"
const BALL_FRAME_SIZE: Vector2i = Vector2i(48, 48)
const BALL_FRAME_COUNT: int = 6

static var _texture_cache: Dictionary = {}
static var _ball_frame_cache: Array[Texture2D] = []


static func warmup() -> void:
	load_png("court_01.png")
	load_png("pud_left.png")
	load_png("pud_right.png")
	load_png("ball_shadow.png")
	for i: int in range(BALL_FRAME_COUNT):
		ball_frame(i)


static func load_png(file_name: String) -> Texture2D:
	var cache_key: String = file_name
	if _texture_cache.has(cache_key):
		return _texture_cache[cache_key] as Texture2D
	var path: String = "%s/%s" % [PNG_DIR, file_name]
	var abs_path: String = ProjectSettings.globalize_path(path)
	if not FileAccess.file_exists(abs_path):
		return ThemeSpriteUtil.load_texture("", Color.WHITE, Vector2i(32, 32))
	var img: Image = Image.load_from_file(abs_path)
	if img == null or img.is_empty():
		return ThemeSpriteUtil.load_texture("", Color.WHITE, Vector2i(32, 32))
	var tex: Texture2D = ImageTexture.create_from_image(img)
	_texture_cache[cache_key] = tex
	return tex


static func ball_frame(index: int) -> Texture2D:
	var clamped: int = clampi(index, 0, BALL_FRAME_COUNT - 1)
	if _ball_frame_cache.size() == BALL_FRAME_COUNT:
		return _ball_frame_cache[clamped]
	_ball_frame_cache.resize(BALL_FRAME_COUNT)
	var sheet: Texture2D = load_png("ball_frames.png")
	if sheet == null:
		var fallback: Texture2D = ThemeSpriteUtil.load_texture("", Color.WHITE, Vector2i(12, 12))
		for i: int in range(BALL_FRAME_COUNT):
			_ball_frame_cache[i] = fallback
		return _ball_frame_cache[clamped]
	for i: int in range(BALL_FRAME_COUNT):
		var atlas: AtlasTexture = AtlasTexture.new()
		atlas.atlas = sheet
		atlas.region = Rect2(
			float(i * BALL_FRAME_SIZE.x),
			0.0,
			float(BALL_FRAME_SIZE.x),
			float(BALL_FRAME_SIZE.y)
		)
		_ball_frame_cache[i] = atlas
	return _ball_frame_cache[clamped]


static func theme_path(theme_key: String, fallback_file: String) -> String:
	var theme: Dictionary = GameConfig.get_theme()
	var configured: String = str(theme.get(theme_key, ""))
	if configured != "":
		return configured
	return "%s/%s" % [PNG_DIR, fallback_file]
