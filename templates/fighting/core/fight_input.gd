extends RefCounted

static var _prev_numpad: Dictionary = {}


static func numpad_just(key: Key) -> bool:
	return Input.is_physical_key_pressed(key) and not bool(_prev_numpad.get(key, false))


static func numpad_held(key: Key) -> bool:
	return Input.is_physical_key_pressed(key)


static func end_physics_frame() -> void:
	_prev_numpad[KEY_KP_1] = Input.is_physical_key_pressed(KEY_KP_1)
	_prev_numpad[KEY_KP_2] = Input.is_physical_key_pressed(KEY_KP_2)
	_prev_numpad[KEY_KP_3] = Input.is_physical_key_pressed(KEY_KP_3)
	_prev_numpad[KEY_KP_4] = Input.is_physical_key_pressed(KEY_KP_4)
