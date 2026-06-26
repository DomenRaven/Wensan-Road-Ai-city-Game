extends RefCounted
class_name ShmupSheet

const SHIPS_PATH: String = "res://assets/pixel-plane-shmup/Tilemap/ships_packed.png"
const TILES_PATH: String = "res://assets/pixel-plane-shmup/Tilemap/tiles_packed.png"
const BG_PATH: String = "res://assets/pixel-plane-shmup/Tilemap/background.png"

const SHIP_TILE: int = 32
const TILE_TILE: int = 16
const SHIP_COLS: int = 4
const TILE_COLS: int = 12
const SPACING: int = 1

static var _ships_tex: Texture2D = null
static var _tiles_tex: Texture2D = null
static var _bg_tex: Texture2D = null
static var _ship_frames: Dictionary = {}
static var _tile_frames: Dictionary = {}


static func ships_frame(frame_index: int) -> AtlasTexture:
	if _ship_frames.has(frame_index):
		return _ship_frames[frame_index] as AtlasTexture
	var sheet: Texture2D = _get_ships_tex()
	var atlas: AtlasTexture = _make_atlas(
		sheet, frame_index, SHIP_TILE, SHIP_TILE, SHIP_COLS, SPACING
	)
	_ship_frames[frame_index] = atlas
	return atlas


static func tiles_frame(frame_index: int) -> AtlasTexture:
	if _tile_frames.has(frame_index):
		return _tile_frames[frame_index] as AtlasTexture
	var sheet: Texture2D = _get_tiles_tex()
	var atlas: AtlasTexture = _make_atlas(
		sheet, frame_index, TILE_TILE, TILE_TILE, TILE_COLS, SPACING
	)
	_tile_frames[frame_index] = atlas
	return atlas


static func background_texture() -> Texture2D:
	return _get_bg_tex()


static func apply_ship_sprite(sprite: Sprite2D, frame_index: int, scale_factor: float = 1.0) -> void:
	if sprite == null:
		return
	sprite.texture = ships_frame(frame_index)
	sprite.scale = Vector2(scale_factor, scale_factor)


static func apply_tile_sprite(sprite: Sprite2D, frame_index: int, scale_factor: float = 1.0) -> void:
	if sprite == null:
		return
	sprite.texture = tiles_frame(frame_index)
	sprite.scale = Vector2(scale_factor, scale_factor)


static func _get_ships_tex() -> Texture2D:
	if _ships_tex == null:
		_ships_tex = _load_image_texture(SHIPS_PATH)
	return _ships_tex


static func _get_tiles_tex() -> Texture2D:
	if _tiles_tex == null:
		_tiles_tex = _load_image_texture(TILES_PATH)
	return _tiles_tex


static func _get_bg_tex() -> Texture2D:
	if _bg_tex == null:
		_bg_tex = _load_image_texture(BG_PATH)
	return _bg_tex


static func _load_image_texture(res_path: String) -> Texture2D:
	var disk_path: String = res_path
	if res_path.begins_with("res://"):
		disk_path = ProjectSettings.globalize_path(res_path)
	var img: Image = Image.new()
	var err: Error = img.load(disk_path)
	if err != OK:
		push_error("ShmupSheet: cannot load image %s (err %s)" % [res_path, str(err)])
		return null
	return ImageTexture.create_from_image(img)


static func _make_atlas(
	sheet_tex: Texture2D,
	frame_index: int,
	tile_w: int,
	tile_h: int,
	columns: int,
	spacing: int
) -> AtlasTexture:
	var atlas: AtlasTexture = AtlasTexture.new()
	if sheet_tex == null:
		return atlas
	atlas.atlas = sheet_tex
	var col: int = frame_index % columns
	var row: int = int(floor(float(frame_index) / float(columns)))
	var x: float = float(col * (tile_w + spacing))
	var y: float = float(row * (tile_h + spacing))
	atlas.region = Rect2(x, y, float(tile_w), float(tile_h))
	return atlas
