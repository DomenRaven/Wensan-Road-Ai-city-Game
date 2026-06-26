extends Camera2D

const SurvivorWorld := preload("res://core/survivor_world.gd")

var _target: Node2D = null


func _ready() -> void:
	make_current()
	var world_size: Vector2 = SurvivorWorld.get_size()
	limit_left = 0
	limit_top = 0
	limit_right = int(world_size.x)
	limit_bottom = int(world_size.y)
	position_smoothing_enabled = false
	_apply_zoom()


func _apply_zoom() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var world_cfg: Dictionary = tuning.get("world", {}) as Dictionary
	var zoom_value: float = float(world_cfg.get("camera_zoom", 0.58))
	zoom_value = clampf(zoom_value, 0.35, 1.0)
	zoom = Vector2(zoom_value, zoom_value)


func bind_target(target: Node2D) -> void:
	_target = target
	if _target != null:
		global_position = _target.global_position


func _physics_process(_delta: float) -> void:
	if _target == null or not is_instance_valid(_target):
		return
	global_position = _target.global_position
