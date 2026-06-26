extends Area2D

signal defeated
signal hp_changed(current_hp: int, max_hp: int)

enum LaserState { IDLE, AIMING, FIRING }

const HostileProjectileScene: PackedScene = preload("res://scenes/hostile_projectile.tscn")
const BossOrbScene: PackedScene = preload("res://scenes/boss_orb.tscn")
const SurvivorSpriteUtil := preload("res://core/survivor_sprite_util.gd")
const SurvivorWorld := preload("res://core/survivor_world.gd")

var _max_hp: int = 5000
var _hp: int = 5000
var _speed: float = 40.0
var _bullet_interval_ms: int = 1500
var _bullet_damage: int = 10
var _bullet_speed: float = 200.0
var _summon_interval_ms: int = 5000
var _summon_count: int = 3
var _laser_cooldown_sec: float = 3.0
var _laser_aim_sec: float = 1.0
var _laser_fire_sec: float = 0.5
var _laser_damage: int = 30
var _orb_interval_sec: float = 5.0
var _orb_lifetime_sec: float = 5.0
var _orb_speed_ratio: float = 0.7
var _orb_count: int = 12
var _orb_damage: int = 8

var _laser_state: LaserState = LaserState.IDLE
var _laser_timer: float = 0.0
var _laser_direction: Vector2 = Vector2.DOWN
var _laser_hit_cooldown: float = 0.0
var _bullet_timer: float = 0.0
var _summon_timer: float = 0.0
var _laser_idle_timer: float = 0.0
var _orb_timer: float = 0.0
var _half_hp_phase: bool = false
var _frozen: bool = false
var _spawner: Node = null
var _color_index: int = 0

var _touch_cooldown: float = 0.0

@onready var _sprite: Sprite2D = $Sprite2D
@onready var _laser_line: Line2D = $LaserLine


func setup(spawner: Node) -> void:
	_spawner = spawner
	_apply_tuning()
	_apply_theme()
	_hp = _max_hp
	_half_hp_phase = false
	_orb_timer = 0.0
	_laser_line.visible = false
	_laser_line.z_index = 50
	hp_changed.emit(_hp, _max_hp)


func _apply_tuning() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var boss_cfg: Dictionary = tuning.get("boss", {}) as Dictionary
	_max_hp = int(boss_cfg.get("hp", _max_hp))
	_hp = _max_hp
	_speed = float(boss_cfg.get("speed", _speed))
	_bullet_interval_ms = int(boss_cfg.get("bullet_interval_ms", _bullet_interval_ms))
	_bullet_damage = int(boss_cfg.get("bullet_damage", _bullet_damage))
	_bullet_speed = float(boss_cfg.get("bullet_speed", _bullet_speed))
	_summon_interval_ms = int(boss_cfg.get("summon_interval_ms", _summon_interval_ms))
	_summon_count = int(boss_cfg.get("summon_count", _summon_count))
	_laser_cooldown_sec = float(boss_cfg.get("laser_cooldown_sec", _laser_cooldown_sec))
	_laser_aim_sec = float(boss_cfg.get("laser_aim_sec", _laser_aim_sec))
	_laser_fire_sec = float(boss_cfg.get("laser_fire_sec", _laser_fire_sec))
	_laser_damage = int(boss_cfg.get("laser_damage", _laser_damage))
	_orb_interval_sec = float(boss_cfg.get("orb_interval_sec", _orb_interval_sec))
	_orb_lifetime_sec = float(boss_cfg.get("orb_lifetime_sec", _orb_lifetime_sec))
	_orb_speed_ratio = float(boss_cfg.get("orb_speed_ratio", _orb_speed_ratio))
	_orb_count = int(boss_cfg.get("orb_count", _orb_count))
	_orb_damage = int(boss_cfg.get("orb_damage", _orb_damage))


func _apply_theme() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var sprite_path: String = str(theme.get("boss_sprite", theme.get("enemy_sprite", "")))
	SurvivorSpriteUtil.apply_sprite(_sprite, sprite_path, Vector2(3.0, 3.0))
	_sprite.modulate = Color(1.0, 0.67, 0.67, 1.0)


func get_current_hp() -> int:
	return _hp


func get_max_hp() -> int:
	return _max_hp


func full_heal() -> void:
	_hp = _max_hp
	_color_index += 1
	var palette: Array[Color] = [
		Color(1.0, 0.67, 0.67),
		Color(0.67, 1.0, 0.67),
		Color(0.67, 0.67, 1.0),
		Color(1.0, 1.0, 0.5),
		Color(1.0, 0.5, 1.0)
	]
	_sprite.modulate = palette[_color_index % palette.size()]
	hp_changed.emit(_hp, _max_hp)


func take_damage(amount: int) -> void:
	_hp -= amount
	var palette: Array[Color] = [
		Color(1.0, 0.67, 0.67),
		Color(0.67, 1.0, 0.67),
		Color(0.67, 0.67, 1.0),
		Color(1.0, 1.0, 0.5),
		Color(1.0, 0.5, 1.0)
	]
	_sprite.modulate = Color(1.0, 0.36, 0.46, 1.0)
	if not _half_hp_phase and _hp <= int(_max_hp * 0.5):
		_half_hp_phase = true
		_orb_timer = 0.0
	hp_changed.emit(_hp, _max_hp)
	if _hp <= 0:
		defeated.emit()
		deactivate()
		return
	await get_tree().create_timer(0.1).timeout
	if visible:
		_sprite.modulate = palette[_color_index % palette.size()]


func deactivate() -> void:
	visible = false
	process_mode = Node.PROCESS_MODE_DISABLED
	monitoring = false
	monitorable = false
	_laser_line.visible = false


func is_laser_active() -> bool:
	return _laser_state != LaserState.IDLE


func _physics_process(delta: float) -> void:
	if not visible or get_tree().paused:
		return
	var player: Node2D = get_tree().get_first_node_in_group("player") as Node2D
	if player == null:
		return
	_bullet_timer += delta
	_summon_timer += delta
	_laser_idle_timer += delta
	if _laser_hit_cooldown > 0.0:
		_laser_hit_cooldown = maxf(0.0, _laser_hit_cooldown - delta)
	if _touch_cooldown > 0.0:
		_touch_cooldown = maxf(0.0, _touch_cooldown - delta)
	_update_laser(delta, player)
	if _half_hp_phase:
		_update_orb_ring(delta)
	if _laser_state == LaserState.IDLE and not _frozen:
		var direction: Vector2 = player.global_position - global_position
		if direction.length_squared() > 1.0:
			var move_dir: Vector2 = direction.normalized()
			global_position += move_dir * _speed * delta
			SurvivorSpriteUtil.apply_facing_flip(_sprite, move_dir)
		if _bullet_timer >= float(_bullet_interval_ms) / 1000.0:
			_bullet_timer = 0.0
			_fire_bullet(player)
		if _summon_timer >= float(_summon_interval_ms) / 1000.0 and _spawner != null:
			_summon_timer = 0.0
			if _spawner.has_method("spawn_minions_near"):
				_spawner.call("spawn_minions_near", global_position, _summon_count)


func _update_orb_ring(delta: float) -> void:
	_orb_timer += delta
	if _orb_timer < _orb_interval_sec:
		return
	_orb_timer = 0.0
	_spawn_orb_ring()


func _spawn_orb_ring() -> void:
	var pool_root: Node = get_tree().get_first_node_in_group("boss_orb_pool")
	if pool_root == null:
		return
	var player_speed: float = _get_player_base_speed()
	var orb_speed: float = player_speed * _orb_speed_ratio
	for i: int in _orb_count:
		var angle: float = TAU * float(i) / float(_orb_count)
		var direction: Vector2 = Vector2.from_angle(angle)
		var orb: Area2D = _acquire_orb(pool_root)
		if orb == null or not orb.has_method("activate"):
			continue
		orb.call("activate", global_position, direction, orb_speed, _orb_damage, _orb_lifetime_sec)


func _get_player_base_speed() -> float:
	var tuning: Dictionary = GameConfig.get_tuning()
	var player_cfg: Dictionary = tuning.get("player", {}) as Dictionary
	return float(player_cfg.get("speed", 150.0))


func _acquire_orb(pool_root: Node) -> Area2D:
	for child: Node in pool_root.get_children():
		if child is Area2D and not child.visible:
			return child as Area2D
	var orb: Area2D = BossOrbScene.instantiate() as Area2D
	pool_root.add_child(orb)
	return orb


func _fire_bullet(player: Node2D) -> void:
	var pool_root: Node = get_tree().get_first_node_in_group("hostile_projectile_pool")
	if pool_root == null:
		return
	var direction: Vector2 = player.global_position - global_position
	var projectile: Area2D = _acquire_projectile(pool_root)
	if projectile == null or not projectile.has_method("activate"):
		return
	projectile.call("activate", global_position, direction, _bullet_speed, _bullet_damage)


func _acquire_projectile(pool_root: Node) -> Area2D:
	for child: Node in pool_root.get_children():
		if child is Area2D and not child.visible:
			return child as Area2D
	var projectile: Area2D = HostileProjectileScene.instantiate() as Area2D
	pool_root.add_child(projectile)
	return projectile


func _update_laser(delta: float, player: Node2D) -> void:
	match _laser_state:
		LaserState.IDLE:
			_laser_line.visible = false
			if _laser_idle_timer >= _laser_cooldown_sec:
				_laser_state = LaserState.AIMING
				_laser_timer = 0.0
				_lock_laser_direction(player)
				_frozen = true
		LaserState.AIMING:
			_laser_timer += delta
			_draw_laser_preview()
			if _laser_timer >= _laser_aim_sec:
				_laser_state = LaserState.FIRING
				_laser_timer = 0.0
		LaserState.FIRING:
			_laser_timer += delta
			_draw_laser_beam()
			_check_laser_hit(player)
			if _laser_timer >= _laser_fire_sec:
				_laser_state = LaserState.IDLE
				_laser_timer = 0.0
				_laser_idle_timer = 0.0
				_laser_line.visible = false
				_frozen = false


func _lock_laser_direction(player: Node2D) -> void:
	var direction: Vector2 = player.global_position - global_position
	if direction.length_squared() < 1.0:
		_laser_direction = Vector2.DOWN
	else:
		_laser_direction = direction.normalized()


func _laser_far_point() -> Vector2:
	var length: float = SurvivorWorld.get_size().length() * 1.25
	return global_position + _laser_direction * length


func _draw_laser_preview() -> void:
	_laser_line.visible = true
	_laser_line.width = 3.0
	_laser_line.default_color = Color(1.0, 0.0, 0.0, 0.55)
	_laser_line.points = PackedVector2Array([Vector2.ZERO, to_local(_laser_far_point())])


func _draw_laser_beam() -> void:
	_laser_line.visible = true
	_laser_line.width = 18.0
	_laser_line.default_color = Color(1.0, 0.15, 0.1, 1.0)
	_laser_line.points = PackedVector2Array([Vector2.ZERO, to_local(_laser_far_point())])


func _check_laser_hit(player: Node2D) -> void:
	if _laser_hit_cooldown > 0.0:
		return
	var start: Vector2 = global_position
	var end: Vector2 = _laser_far_point()
	var closest: Vector2 = Geometry2D.get_closest_point_to_segment(player.global_position, start, end)
	if closest.distance_squared_to(player.global_position) <= 576.0:
		if player.has_method("take_laser_hit"):
			player.call("take_laser_hit", _laser_damage, start, _laser_direction)
		elif player.has_method("take_hit"):
			player.call("take_hit", _laser_damage, start)
		_laser_hit_cooldown = 0.5


func _on_area_entered(area: Area2D) -> void:
	if _touch_cooldown > 0.0:
		return
	if area.is_in_group("player") and area.has_method("take_hit"):
		area.call("take_hit", 5, global_position)
		_touch_cooldown = 0.5
