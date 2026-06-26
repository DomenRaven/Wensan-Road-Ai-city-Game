extends RefCounted

const ThemeSpriteUtil := preload("res://core/theme_sprite.gd")


static func apply_player_frames(anim: AnimatedSprite2D, theme: Dictionary) -> void:
	var sf: SpriteFrames = SpriteFrames.new()
	_add_sheet(sf, "idle", theme, "player_idle", 32, 32, 11, 10.0, true)
	_add_sheet(sf, "run", theme, "player_run", 32, 32, 12, 12.0, true)
	_add_single(sf, "jump", theme, "player_jump", 32, 32)
	_add_single(sf, "fall", theme, "player_fall", 32, 32)
	_add_sheet(sf, "hit", theme, "player_hit", 32, 32, 7, 10.0, false)
	anim.sprite_frames = sf
	anim.play("idle")


static func apply_coin_frames(anim: AnimatedSprite2D, theme: Dictionary) -> void:
	var sf: SpriteFrames = SpriteFrames.new()
	_add_sheet(sf, "spin", theme, "coin_spin", 32, 32, 17, 12.0, true)
	_add_sheet(sf, "collected", theme, "coin_collected", 32, 32, 6, 12.0, false)
	anim.sprite_frames = sf
	anim.play("spin")


static func apply_goal_frames(anim: AnimatedSprite2D, theme: Dictionary) -> void:
	var sf: SpriteFrames = SpriteFrames.new()
	_add_single(sf, "idle", theme, "goal_idle", 64, 64)
	_add_sheet(sf, "pressed", theme, "goal_pressed", 64, 64, 8, 8.0, false)
	anim.sprite_frames = sf
	anim.play("idle")


static func apply_box_frames(anim: AnimatedSprite2D, theme: Dictionary) -> void:
	var sf: SpriteFrames = SpriteFrames.new()
	_add_single(sf, "idle", theme, "box_idle", 28, 24)
	_add_sheet(sf, "hit", theme, "box_hit", 28, 24, 3, 10.0, false)
	_add_sheet(sf, "break", theme, "box_break", 28, 24, 4, 10.0, false)
	anim.sprite_frames = sf
	anim.play("idle")


static func _add_sheet(
	sf: SpriteFrames,
	anim_name: String,
	theme: Dictionary,
	path_key: String,
	frame_w: int,
	frame_h: int,
	frame_count: int,
	fps: float,
	loop: bool
) -> void:
	var tex: Texture2D = _load_theme_texture(theme, path_key, Vector2i(frame_w, frame_h))
	if tex == null:
		return
	if not sf.has_animation(anim_name):
		sf.add_animation(anim_name)
	sf.set_animation_speed(anim_name, fps)
	sf.set_animation_loop(anim_name, loop)
	for i: int in range(frame_count):
		var atlas: AtlasTexture = AtlasTexture.new()
		atlas.atlas = tex
		atlas.region = Rect2(float(i * frame_w), 0.0, float(frame_w), float(frame_h))
		sf.add_frame(anim_name, atlas)


static func _add_single(
	sf: SpriteFrames,
	anim_name: String,
	theme: Dictionary,
	path_key: String,
	frame_w: int,
	frame_h: int
) -> void:
	var tex: Texture2D = _load_theme_texture(theme, path_key, Vector2i(frame_w, frame_h))
	if tex == null:
		return
	if not sf.has_animation(anim_name):
		sf.add_animation(anim_name)
	sf.set_animation_speed(anim_name, 1.0)
	sf.set_animation_loop(anim_name, false)
	sf.add_frame(anim_name, tex)


static func _load_theme_texture(theme: Dictionary, path_key: String, fallback_size: Vector2i) -> Texture2D:
	var path: String = str(theme.get(path_key, ""))
	if path == "":
		return null
	return ThemeSpriteUtil.load_texture(path, Color.MAGENTA, fallback_size)
