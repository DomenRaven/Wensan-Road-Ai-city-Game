extends RefCounted
class_name LifeSimInventory

var _items: Dictionary = {}


func clear() -> void:
	_items.clear()


func add(item_id: String, amount: int = 1) -> void:
	var count: int = int(_items.get(item_id, 0))
	_items[item_id] = count + amount


func has(item_id: String, amount: int = 1) -> bool:
	return int(_items.get(item_id, 0)) >= amount


func take(item_id: String, amount: int = 1) -> bool:
	if not has(item_id, amount):
		return false
	_items[item_id] = int(_items[item_id]) - amount
	if int(_items[item_id]) <= 0:
		_items.erase(item_id)
	return true


func get_summary() -> String:
	if _items.is_empty():
		return "背包：空"
	var parts: PackedStringArray = PackedStringArray()
	for item_id: String in _items.keys():
		parts.append("%s×%d" % [item_id, int(_items[item_id])])
	return "背包：" + ", ".join(parts)
