extends RefCounted

const WarriorSheet := preload("res://core/warrior_sheet.gd")

const W2_FRAMES: Dictionary = {
	"idle": {"count": 5, "fps": 8.0, "loop": true},
	"walk": {"count": 8, "fps": 10.0, "loop": true},
	"attack1": {"count": 4, "fps": 12.0, "loop": false},
	"attack2": {"count": 4, "fps": 8.0, "loop": false},
	"ultimate": {"count": 4, "fps": 12.0, "loop": false},
	"protect": {"count": 2, "fps": 8.0, "loop": true},
	"hurt": {"count": 3, "fps": 10.0, "loop": false},
	"dead": {"count": 4, "fps": 8.0, "loop": false},
}

const W3_FRAMES: Dictionary = {
	"idle": {"count": 5, "fps": 8.0, "loop": true},
	"walk": {"count": 8, "fps": 10.0, "loop": true},
	"attack1": {"count": 4, "fps": 12.0, "loop": false},
	"attack2": {"count": 3, "fps": 8.0, "loop": false},
	"ultimate": {"count": 4, "fps": 12.0, "loop": false},
	"protect": {"count": 3, "fps": 8.0, "loop": true},
	"hurt": {"count": 2, "fps": 10.0, "loop": false},
	"dead": {"count": 4, "fps": 8.0, "loop": false},
}

static var _frames_cache: Dictionary = {}


static func build_sprite_frames(warrior_id: String) -> SpriteFrames:
	if _frames_cache.has(warrior_id):
		return _frames_cache[warrior_id] as SpriteFrames
	var sf: SpriteFrames = SpriteFrames.new()
	var frame_map: Dictionary = W2_FRAMES if warrior_id == "Warrior_2" else W3_FRAMES
	for anim_name: String in frame_map.keys():
		var info: Dictionary = frame_map[anim_name] as Dictionary
		_add_strip(
			sf,
			anim_name,
			WarriorSheet.theme_path(warrior_id, anim_name),
			int(info.get("count", 1)),
			float(info.get("fps", 8.0)),
			bool(info.get("loop", false))
		)
	_frames_cache[warrior_id] = sf
	return sf


static func _add_strip(
	sf: SpriteFrames,
	anim_name: String,
	path: String,
	frame_count: int,
	fps: float,
	loop: bool
) -> void:
	var tex: Texture2D = WarriorSheet.load_strip(path)
	if tex == null:
		return
	if not sf.has_animation(anim_name):
		sf.add_animation(anim_name)
	sf.set_animation_speed(anim_name, fps)
	sf.set_animation_loop(anim_name, loop)
	for i: int in range(frame_count):
		var atlas: AtlasTexture = AtlasTexture.new()
		atlas.atlas = tex
		atlas.region = Rect2(float(i * WarriorSheet.FRAME_W), 0.0, float(WarriorSheet.FRAME_W), float(WarriorSheet.FRAME_H))
		sf.add_frame(anim_name, atlas)
