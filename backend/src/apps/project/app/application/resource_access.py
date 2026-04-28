from app.domain.enums import ProjectRole

PROJECT_RESOURCE_KINDS: tuple[str, ...] = (
    "microfons",
    "cameras",
    "camera-tripods",
    "lights",
    "light-tripods",
    "sounds",
    "requisites",
)

VIEWABLE_RESOURCE_KINDS_BY_ROLE: dict[ProjectRole, tuple[str, ...]] = {
    ProjectRole.DIRECTOR: PROJECT_RESOURCE_KINDS,
    ProjectRole.PROP_MASTER: ("requisites",),
    ProjectRole.CAMERA: ("cameras", "camera-tripods"),
    ProjectRole.SOUND: ("sounds", "microfons"),
    ProjectRole.LIGHT: ("lights", "light-tripods"),
    ProjectRole.ACTOR: (),
}

RESOURCE_KIND_ALIASES: dict[str, str] = {
    "microfon": "microfons",
    "microfons": "microfons",
    "camera": "cameras",
    "cameras": "cameras",
    "camera-tripod": "camera-tripods",
    "camera-tripods": "camera-tripods",
    "camera_tripod": "camera-tripods",
    "camera_tripods": "camera-tripods",
    "light": "lights",
    "lights": "lights",
    "light-tripod": "light-tripods",
    "light-tripods": "light-tripods",
    "light_tripod": "light-tripods",
    "light_tripods": "light-tripods",
    "sound": "sounds",
    "sounds": "sounds",
    "requisite": "requisites",
    "requisites": "requisites",
}


def normalize_resource_kind(resource_type: str) -> str | None:
    return RESOURCE_KIND_ALIASES.get(resource_type.strip().lower())
