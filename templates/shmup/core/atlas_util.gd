extends RefCounted


static func load_region(sheet_path: String, region: Array) -> AtlasTexture:
	var atlas: AtlasTexture = AtlasTexture.new()
	if not ResourceLoader.exists(sheet_path):
		return atlas
	atlas.atlas = load(sheet_path) as Texture2D
	if region.size() >= 4:
		atlas.region = Rect2(
			float(region[0]),
			float(region[1]),
			float(region[2]),
			float(region[3])
		)
	return atlas


static func apply_sprite(sprite: Sprite2D, sheet_path: String, region: Array) -> void:
	sprite.texture = load_region(sheet_path, region)
