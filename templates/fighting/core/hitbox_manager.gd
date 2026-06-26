extends Area2D

signal hit_landed(target: Node)

var _owner_fighter: Node = null
var _active: bool = false
var _struck_targets: Array[Node] = []


func setup(owner_fighter: Node) -> void:
	_owner_fighter = owner_fighter
	monitoring = false
	monitorable = false
	area_entered.connect(_on_area_entered)


func set_active(active: bool) -> void:
	if active and not _active:
		_struck_targets.clear()
	_active = active
	monitoring = active


func process_active_frame() -> void:
	if not _active or _owner_fighter == null:
		return
	for area: Area2D in get_overlapping_areas():
		_try_hit_area(area)


func _on_area_entered(area: Area2D) -> void:
	_try_hit_area(area)


func _try_hit_area(area: Area2D) -> void:
	if not _active or _owner_fighter == null:
		return
	if not area.is_in_group("hurtbox"):
		return
	var victim: Node = area.get_parent()
	if victim == _owner_fighter or victim in _struck_targets:
		return
	if not victim.has_method("receive_hit"):
		return
	var move_data: Resource = _owner_fighter.call("get_current_move_data") as Resource
	if move_data == null:
		return
	var landed: bool = bool(victim.call("receive_hit", _owner_fighter, move_data))
	if landed:
		_struck_targets.append(victim)
		hit_landed.emit(victim)
