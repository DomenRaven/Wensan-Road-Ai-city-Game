extends Node

var config: Dictionary = {}

const DEFAULT_CONFIG_PATH: String = "res://config/game_config.json"


func _ready() -> void:
	load_config()


func load_config(path: String = DEFAULT_CONFIG_PATH) -> void:
	var file: FileAccess = FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_error("GameConfig: cannot open %s" % path)
		return
	var json: JSON = JSON.new()
	var err: Error = json.parse(file.get_as_text())
	file.close()
	if err != OK:
		push_error("GameConfig: JSON parse error in %s" % path)
		return
	if json.data is Dictionary:
		config = json.data as Dictionary
	else:
		push_error("GameConfig: root must be a Dictionary")


func get_tuning() -> Dictionary:
	if config.has("tuning") and config["tuning"] is Dictionary:
		return config["tuning"] as Dictionary
	return {}


func get_theme() -> Dictionary:
	if config.has("theme") and config["theme"] is Dictionary:
		return config["theme"] as Dictionary
	return {}


func get_session_meta() -> Dictionary:
	if config.has("meta") and config["meta"] is Dictionary:
		return config["meta"] as Dictionary
	return {}


func get_display_name() -> String:
	var meta: Dictionary = get_session_meta()
	return str(meta.get("display_name", "雷霆小卫士"))


func has_skill(skill_id: String) -> bool:
	var tuning: Dictionary = get_tuning()
	if not tuning.has("enabled_skills"):
		return false
	var skills: Array = tuning["enabled_skills"] as Array
	return skill_id in skills


func get_skill_cooldown_scale(skill_id: String) -> float:
	var tuning: Dictionary = get_tuning()
	if not tuning.has("skills") or not tuning["skills"] is Dictionary:
		return 1.0
	var skills_cfg: Dictionary = tuning["skills"] as Dictionary
	if not skills_cfg.has(skill_id) or not skills_cfg[skill_id] is Dictionary:
		return 1.0
	var skill: Dictionary = skills_cfg[skill_id] as Dictionary
	return float(skill.get("cooldown_scale", 1.0))
