extends RefCounted

## 展厅 shmup 静音：play 为空操作（拖动输入与音效彻底解耦）


static func resolve_path(group: String, key: String) -> String:
	var theme: Dictionary = GameConfig.get_theme()
	if not theme.has("sounds") or not theme["sounds"] is Dictionary:
		return ""
	var sounds: Dictionary = theme["sounds"] as Dictionary
	if not sounds.has(group) or not sounds[group] is Dictionary:
		return ""
	var block: Dictionary = sounds[group] as Dictionary
	return str(block.get(key, ""))


static func load_stream(_path: String) -> AudioStream:
	return null


static func play(_owner: Node, _group: String, _key: String, _volume_db: float = 0.0) -> void:
	pass
