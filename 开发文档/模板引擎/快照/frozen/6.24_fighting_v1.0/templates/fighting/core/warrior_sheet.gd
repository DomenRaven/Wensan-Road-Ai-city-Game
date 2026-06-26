extends RefCounted

const FRAME_W: int = 96
const FRAME_H: int = 96

static var _cache: Dictionary = {}


static func theme_path(warrior_id: String, anim_key: String) -> String:
	return "res://assets/warrior/%s/%s.png" % [warrior_id, anim_key]


static func warmup(warrior_id: String) -> void:
	for key: String in ["idle", "walk", "attack1", "attack2", "ultimate", "protect", "hurt", "dead"]:
		load_strip(theme_path(warrior_id, key))


static func load_idle_preview(warrior_id: String) -> Texture2D:
	var strip: Texture2D = load_strip(theme_path(warrior_id, "idle"))
	if strip == null:
		return null
	var atlas: AtlasTexture = AtlasTexture.new()
	atlas.atlas = strip
	atlas.region = Rect2(0.0, 0.0, float(FRAME_W), float(FRAME_H))
	return atlas


static func load_strip(path: String) -> Texture2D:
	if _cache.has(path):
		return _cache[path] as Texture2D
	if path == "":
		return null
	var abs_path: String = path
	if path.begins_with("res://"):
		abs_path = ProjectSettings.globalize_path(path)
	if not FileAccess.file_exists(abs_path):
		return null
	var img: Image = Image.load_from_file(abs_path)
	if img == null or img.is_empty():
		return null
	var tex: ImageTexture = ImageTexture.create_from_image(img)
	_cache[path] = tex
	return tex
