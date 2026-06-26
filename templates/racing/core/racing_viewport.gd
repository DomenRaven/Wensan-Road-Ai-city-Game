extends RefCounted
class_name RacingViewport

const WIDTH: float = 540.0
const HEIGHT: float = 960.0
const PLAYER_Y_OFFSET: float = 150.0


static func center_x() -> float:
	return WIDTH * 0.5


static func player_y() -> float:
	return HEIGHT - PLAYER_Y_OFFSET


static func track_right(margin: float) -> float:
	return WIDTH - margin
