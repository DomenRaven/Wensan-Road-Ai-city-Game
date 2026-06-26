extends RefCounted
class_name TdCombat

## Core locked: damage = max(1, atk - def)


static func calc_damage(attack: int, defense: int) -> int:
	return maxi(1, attack - defense)


static func is_in_tile_range(
	origin: Vector2i,
	target: Vector2i,
	range_tiles: int
) -> bool:
	var dx: int = absi(origin.x - target.x)
	var dy: int = absi(origin.y - target.y)
	return maxi(dx, dy) <= range_tiles
