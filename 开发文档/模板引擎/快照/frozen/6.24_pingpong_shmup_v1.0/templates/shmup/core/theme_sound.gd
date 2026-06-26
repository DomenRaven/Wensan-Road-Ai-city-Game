extends RefCounted


static func resolve_path(group: String, key: String) -> String:
	var theme: Dictionary = GameConfig.get_theme()
	if not theme.has("sounds") or not theme["sounds"] is Dictionary:
		return ""
	var sounds: Dictionary = theme["sounds"] as Dictionary
	if not sounds.has(group) or not sounds[group] is Dictionary:
		return ""
	var block: Dictionary = sounds[group] as Dictionary
	return str(block.get(key, ""))


static var _stream_cache: Dictionary = {}


static func load_stream(path: String) -> AudioStream:
	if _stream_cache.has(path):
		return _stream_cache[path] as AudioStream
	var abs_path: String = path
	if path.begins_with("res://"):
		abs_path = ProjectSettings.globalize_path(path)
	if not FileAccess.file_exists(abs_path):
		return null
	var stream: AudioStream = null
	if abs_path.ends_with(".ogg"):
		stream = AudioStreamOggVorbis.load_from_file(abs_path)
	elif abs_path.ends_with(".wav"):
		stream = AudioStreamWAV.load_from_file(abs_path)
	else:
		stream = load(path) as AudioStream
	if stream != null:
		_stream_cache[path] = stream
	return stream


static func play(owner: Node, group: String, key: String, volume_db: float = 0.0) -> void:
	var path: String = resolve_path(group, key)
	if path == "":
		return
	var stream: AudioStream = load_stream(path)
	if stream == null:
		return
	var player: AudioStreamPlayer = AudioStreamPlayer.new()
	player.stream = stream
	player.volume_db = volume_db
	owner.get_tree().root.add_child(player)
	player.finished.connect(player.queue_free)
	player.play()
