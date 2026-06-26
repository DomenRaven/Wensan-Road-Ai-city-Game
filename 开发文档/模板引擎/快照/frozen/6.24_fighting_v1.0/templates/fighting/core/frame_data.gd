extends Resource

@export var startup_frames: int = 6
@export var active_frames: int = 3
@export var recovery_frames: int = 12
@export var damage: int = 12
@export var hitstun_frames: int = 12
@export var knockback: float = 120.0
@export var hitbox_size: Vector2 = Vector2(36.0, 28.0)
@export var hitbox_offset: Vector2 = Vector2(24.0, -16.0)


func get_total_frames() -> int:
	return startup_frames + active_frames + recovery_frames


func is_active_frame(frame_index: int) -> bool:
	return frame_index >= startup_frames and frame_index < startup_frames + active_frames
