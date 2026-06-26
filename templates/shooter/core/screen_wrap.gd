extends RefCounted
class_name ScreenWrapUtil

const VIEW_WIDTH: float = 640.0
const VIEW_HEIGHT: float = 360.0


static func wrap(pos: Vector2) -> Vector2:
	var result: Vector2 = pos
	if result.x < 0.0:
		result.x += VIEW_WIDTH
	elif result.x >= VIEW_WIDTH:
		result.x -= VIEW_WIDTH
	if result.y < 0.0:
		result.y += VIEW_HEIGHT
	elif result.y >= VIEW_HEIGHT:
		result.y -= VIEW_HEIGHT
	return result
