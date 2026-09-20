"""Allowlisted, hash-pinned SHACL shape profiles for the HTTP service."""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path


PROFILE_NAME = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")


@dataclass(frozen=True)
class ShapeProfile:
    name: str
    path: Path
    sha256: str
    scope: str


class ShapeRegistry:
    """Resolve only operator-registered local shape files with pinned hashes."""

    def __init__(self, resource_dir: Path, manifest_path: str | None = None):
        demo_path = resource_dir / "demo-shapes.ttl"
        self._profiles = {
            "demo": ShapeProfile(
                "demo",
                demo_path,
                self._hash_file(demo_path),
                "Conformance to packaged synthetic demo shapes; not a legal compliance determination",
            )
        }
        if manifest_path:
            self._load_manifest(Path(manifest_path))

    @staticmethod
    def _hash_file(path: Path) -> str:
        if not path.is_file():
            raise ValueError(f"Trusted shapes file is unavailable: {path.name}")
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _load_manifest(self, manifest_path: Path) -> None:
        manifest_path = manifest_path.resolve()
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("MAILO_SHAPES_MANIFEST must be readable JSON") from exc
        profiles = data.get("profiles") if isinstance(data, dict) else None
        if not isinstance(profiles, dict):
            raise ValueError("Shapes manifest requires a profiles object")
        base_dir = manifest_path.parent
        for name, entry in profiles.items():
            if name == "demo" or not isinstance(name, str) or not PROFILE_NAME.fullmatch(name):
                raise ValueError("Shapes profile names must be safe identifiers and cannot be demo")
            if not isinstance(entry, dict):
                raise ValueError(f"Shapes profile {name} must be an object")
            filename, expected_hash, scope = (
                entry.get("file"), entry.get("sha256"), entry.get("scope")
            )
            if (
                not isinstance(filename, str)
                or not isinstance(expected_hash, str)
                or not re.fullmatch(r"[0-9a-f]{64}", expected_hash)
                or not isinstance(scope, str)
                or not scope.strip()
            ):
                raise ValueError(f"Shapes profile {name} has invalid file, sha256, or scope")
            path = (base_dir / filename).resolve()
            try:
                path.relative_to(base_dir)
            except ValueError as exc:
                raise ValueError(f"Shapes profile {name} escapes the manifest directory") from exc
            actual_hash = self._hash_file(path)
            if actual_hash != expected_hash:
                raise ValueError(f"Shapes profile {name} SHA-256 does not match manifest")
            self._profiles[name] = ShapeProfile(name, path, actual_hash, scope.strip())

    def get(self, name: str) -> ShapeProfile:
        try:
            profile = self._profiles[name]
        except KeyError as exc:
            raise ValueError("Unknown trusted shapes profile") from exc
        if self._hash_file(profile.path) != profile.sha256:
            raise ValueError(f"Trusted shapes profile {name} has changed on disk")
        return profile

    def ready(self) -> None:
        for name in self._profiles:
            self.get(name)
