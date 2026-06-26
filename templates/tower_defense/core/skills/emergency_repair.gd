extends RefCounted
class_name EmergencyRepairSkill

const BASE_COOLDOWN_MS: int = 30000


static func is_enabled() -> bool:
	return GameConfig.has_skill("emergency_repair")


static func get_cooldown_sec() -> float:
	var scale: float = GameConfig.get_skill_cooldown_scale("emergency_repair")
	return float(BASE_COOLDOWN_MS) * scale / 1000.0


static func try_repair_towers(towers_root: Node2D) -> bool:
	if not is_enabled():
		return false
	if towers_root == null:
		return false
	for child: Node in towers_root.get_children():
		if child.has_method("repair_full"):
			child.call("repair_full")
	return true
