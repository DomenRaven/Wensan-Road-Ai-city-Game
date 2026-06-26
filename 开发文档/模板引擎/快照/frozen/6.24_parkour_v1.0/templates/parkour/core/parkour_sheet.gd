extends RefCounted
class_name ParkourSheet

const ParkourTexturesUtil := preload("res://core/parkour_textures.gd")

static var _texture_cache: Dictionary = {}


static func load_strip(path: String) -> Texture2D:
	if _texture_cache.has(path):
		return _texture_cache[path] as Texture2D
	var tex: Texture2D = _load_image_texture(path)
	if tex != null:
		_texture_cache[path] = tex
	return tex


static func warmup(theme: Dictionary) -> void:
	var keys: Array[String] = [
		"player_idle", "player_run", "player_jump", "player_fall", "player_hit"
	]
	for key: String in keys:
		var path: String = str(theme.get(key, ""))
		if path != "":
			load_strip(path)
	ParkourTexturesUtil.get_ground_texture()
	for i: int in range(4):
		ParkourTexturesUtil.get_obstacle_texture(i)
	for i: int in range(3):
		ParkourTexturesUtil.get_collectible_texture(i)


static func _load_image_texture(res_path: String) -> Texture2D:
	var disk_path: String = res_path
	if res_path.begins_with("res://"):
		disk_path = ProjectSettings.globalize_path(res_path)
	var img: Image = Image.new()
	if img.load(disk_path) != OK:
		push_error("ParkourSheet: cannot load %s" % res_path)
		return null
	return ImageTexture.create_from_image(img)
