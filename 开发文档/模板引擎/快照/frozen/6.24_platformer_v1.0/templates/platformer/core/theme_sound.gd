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


static func load_stream(path: String) -> AudioStream:
	if path == "":
		return null
	if ResourceLoader.exists(path):
		var imported: AudioStream = ResourceLoader.load(path) as AudioStream
		if imported != null:
			return imported
	var abs_path: String = path
	if path.begins_with("res://"):
		abs_path = ProjectSettings.globalize_path(path)
	if FileAccess.file_exists(abs_path):
		if abs_path.ends_with(".ogg"):
			return AudioStreamOggVorbis.load_from_file(abs_path)
		if abs_path.ends_with(".wav"):
			return AudioStreamWAV.load_from_file(abs_path)
	return load(path) as AudioStream


static func play(owner: Node, group: String, key: String, volume_db: float = 0.0) -> void:
	var path: String = resolve_path(group, key)
	if path == "":
		push_warning("ThemeSound: missing path for %s.%s" % [group, key])
		return
	var stream: AudioStream = load_stream(path)
	if stream == null:
		push_warning("ThemeSound: cannot load %s" % path)
		return
	var player: AudioStreamPlayer = AudioStreamPlayer.new()
	player.stream = stream
	player.volume_db = volume_db
	player.bus = &"Master"
	owner.get_tree().root.add_child(player)
	player.finished.connect(player.queue_free)
	player.play()
