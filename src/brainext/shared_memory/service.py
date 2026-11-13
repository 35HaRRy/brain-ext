"""Session-bound operations. Model payloads cannot select their own session or vault."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from brainext.mdio import note_text, read_note, safe_path
from brainext.shared_memory.registry import Registry, RegistryError, canonical_directory, project_id
from brainext.shared_memory.runtime import RuntimeUnavailable, VaultRuntime


def response(status="ok", mode="disabled", **values):
    return {"version": 1, "status": status, "mode": mode, "project": None,
            "context": "", "records": [], "warnings": [], "result": {}, **values}


def metadata_of(content):
    normalized = content.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return {}
    header, sep, _ = normalized[4:].partition("\n---\n")
    if not sep:
        raise ValueError("frontmatter")
    meta = yaml.safe_load(header)
    if not isinstance(meta, dict):
        raise ValueError("frontmatter")
    return meta


class MemoryService:
    def __init__(self, vault: Path, registry: Path):
        self.vault = vault.absolute()
        self.registry = Registry(registry, vault)

    def handle(self, request: dict) -> dict:
        try:
            if (not isinstance(request, dict) or type(request.get("version")) is not int
                    or request.get("version") != 1
                    or set(request) != {"version", "action", "session", "payload"}):
                raise ValueError("request")
            session, payload = request["session"], request["payload"]
            if (not isinstance(session, dict) or not isinstance(payload, dict)
                    or not isinstance(session.get("id"), str) or not session["id"]):
                raise ValueError("session")
            directory = canonical_directory(session["directory"])
            runtime = VaultRuntime(self.vault)
            mapping = self.registry.resolve(directory)
            if mapping["status"] == "conflict":
                return response("conflict", "general", warnings=["project_mapping_conflict"],
                                context=self._render(runtime.general_context(4000)),
                                result={"mapping": mapping})
            project = mapping["project"]
            mode = "project" if project else "general"
            catalog = {item["id"]: item for item in runtime.project_catalog()}
            if project and project not in catalog:
                raise RuntimeUnavailable("project_record_unavailable")
            action = request["action"]
            if action == "context":
                if payload.get("refresh") is True:
                    refreshed = runtime.beyin("sync")
                    if refreshed.get("status") != "succeeded":
                        raise RuntimeUnavailable("source_sync_incomplete")
                general = runtime.general_context(4000)
                scoped = runtime.project_context(project, str(payload.get("query", ""))[:2000], 6000
                                                 ) if project else {"records": []}
                records = general["records"] + scoped["records"]
                return response(mode=mode, project=project, records=records,
                                context=self._render({"records": records}),
                                result={"mapping": mapping})
            if action == "catalog":
                return response(mode=mode, project=project, result={"projects": list(catalog.values()),
                                                                 "mapping": mapping})
            if action in {"register", "bind", "ignore"}:
                if session.get("parent_id") or payload.get("confirmed") is not True:
                    raise ValueError("confirmation_required")
                root = canonical_directory(payload["root"])
                detected = self.registry.resolve(directory)
                if (not directory.is_relative_to(root)
                        or (detected["kind"] == "git" and str(root) != detected["root"])
                        or root == Path(root.anchor)):
                    raise ValueError("root_outside_session")
                if action == "ignore":
                    result = self.registry.ignore(root, payload["expected_revision"])
                else:
                    id = project_id(payload["id"])
                    if action == "register":
                        self._register(runtime, id, payload)
                    elif id not in catalog:
                        raise ValueError("unknown_project")
                    result = self.registry.bind(root, id, payload["expected_revision"])
                    project = id
                return response(result["status"], "project" if project else "general",
                                project=project, result=result)
            if action == "search":
                target = payload.get("project", project)
                if not target or target not in catalog:
                    raise ValueError("target_project_required")
                if target != project and payload.get("cross_project_confirmed") is not True:
                    raise ValueError("cross_project_confirmation")
                result = runtime.project_context(target, payload["query"], 6000)
                return response(mode=mode, project=project, records=result["records"], result=result)
            result = self._write(runtime, project, action, payload, session)
            status = "conflict" if result.get("status") == "conflict" else "ok"
            return response(status, mode, project=project, result=result)
        except RegistryError:
            return response("unavailable", warnings=["mapping_unavailable; memory writes disabled"])
        except RuntimeUnavailable:
            return response("unavailable", warnings=["memory_unavailable; memory writes disabled"])
        except (ValueError, TypeError, KeyError):
            return response("invalid", warnings=["invalid_request_or_scope"])
        except Exception:
            return response("unavailable", warnings=["memory_operation_failed; verify before retry"])

    @staticmethod
    def _render(result):
        # JSON preserves source boundaries; the plugin labels this entire block as source data.
        return json.dumps(result.get("records", []), ensure_ascii=False)

    def _register(self, runtime, id, payload):
        title, purpose = payload["title"], payload["purpose"]
        if not all(isinstance(v, str) and v.strip() and len(v) <= 500 for v in (title, purpose)):
            raise ValueError("project_details")
        source = f"projects/{id}/Project.md"
        meta = {"id": id, "title": title, "purpose": purpose, "kind": "fact",
                "project": id, "visibility": "internal"}
        body = f"# {title}\n\n{purpose}\n"
        path = safe_path(self.vault, source)
        if path.exists():
            if read_note(path) != (meta, body):
                raise ValueError("project_exists_with_different_content")
        else:
            result = runtime.beyin("note-edit", {"source": source, "expected_sha256": None,
                                                 "content": note_text(meta, body)})
            if result.get("status") not in {"written", "unchanged"}:
                raise RuntimeUnavailable("project_write")
        if read_note(path) != (meta, body):
            raise RuntimeUnavailable("project_readback")

    def _authorize_source(self, runtime, source, project, *, create=False, metadata=None):
        path = safe_path(self.vault, source)
        if path.suffix != ".md" or any(part.startswith(".") for part in Path(source).parts):
            raise ValueError("source")
        if path.exists():
            meta, _ = read_note(path)
        elif create:
            meta = metadata or {}
        else:
            raise ValueError("source_missing")
        if (meta.get("visibility") == "private" or meta.get("kind") in {"untrusted", "receipt"}
                or meta.get("trust") == "untrusted" or meta.get("trusted") is False
                or meta.get("status") == "untrusted" or meta.get("validity") == "rejected"):
            raise ValueError("source_excluded")
        companion = runtime.companion.directory(self.vault)
        general = companion and path.parent == companion and path.name in {
            "Core.md", "Soul.md", "Kurallar.md"} and not meta.get("project")
        if general:
            return path, meta
        if not project or runtime.record_project({**meta, "source": source}) != project:
            raise ValueError("source_scope")
        if Path(source).parts[0] not in {"projects", "notes", "knowledge", "tasks"}:
            raise ValueError("source_region")
        return path, meta

    def _write(self, runtime, project, action, payload, session):
        payload = dict(payload)
        confirmed = payload.pop("confirmed", None) is True
        if action in {"note-read", "note-create", "note-edit", "task-create"}:
            source = payload["source"]
            create = action in {"note-create", "task-create"}
            meta = payload.get("metadata", {})
            path, previous = self._authorize_source(runtime, source, project,
                                                    create=create, metadata=meta)
            if action == "note-read":
                result = runtime.beyin(action, {"source": source})
                companion = runtime.companion.directory(self.vault)
                if path.parent == companion and path.name == "Kurallar.md":
                    result["content"] = runtime.companion.filter_scoped_rules(
                        result["content"], active_project="__general__")
                return result
            if action == "task-create":
                if not confirmed or not project or meta.get("project") != project:
                    raise ValueError("task_confirmation_or_scope")
            elif meta.get("kind") == "task" or previous.get("kind") == "task":
                raise ValueError("use_task_commands")
            if action == "note-create":
                if path.exists() or meta.get("kind") in {"task", "receipt"} or meta.get("generated"):
                    raise ValueError("new_note")
                return runtime.beyin("note-edit", {"source": source, "expected_sha256": None,
                    "content": note_text(meta, payload["text"])})
            if action == "note-edit":
                before = runtime.beyin("note-read", {"source": source})["content"]
                after = before
                if set(payload) != {"source", "expected_sha256", "edits"}:
                    raise ValueError("body_edits_only")
                for edit in payload["edits"]:
                    if not edit["old"] or after.count(edit["old"]) != 1:
                        raise ValueError("ambiguous_edit")
                    after = after.replace(edit["old"], edit["new"], 1)
                if metadata_of(before) != metadata_of(after):
                    raise ValueError("metadata_changes_require_dedicated_command")
            result = runtime.beyin(action, payload)
            if action == "task-create" and any(result.get(k) != v for k, v in meta.items()):
                raise RuntimeUnavailable("task_readback")
            return result
        if not project:
            raise ValueError("project_required")
        if action == "task-update":
            if not confirmed:
                raise ValueError("task_confirmation")
            records, _ = runtime.store._eligible()
            task = next((r for r in records if r["id"] == payload["id"]), None)
            if not task or task.get("kind") != "task" or runtime.record_project(task) != project:
                raise ValueError("task_scope")
            if task["revision"] != payload["expected_revision"]:
                return {"status": "conflict"}
            if set(payload["changes"]) & {"id", "source", "project", "kind", "revision"}:
                raise ValueError("task_identity")
            for ref in payload["changes"].get("evidence_refs", []):
                self._authorize_source(runtime, ref, project)
            return runtime.beyin(action, payload)
        if action == "receipt":
            if not payload.get("refs"):
                raise ValueError("receipt_refs")
            for source in payload["refs"]:
                _, meta = self._authorize_source(runtime, source, project)
                if runtime.record_project({**meta, "source": source}) != project:
                    raise ValueError("receipt_scope")
            payload["session"] = session["id"]
            # The runtime CLI takes the harness separately; JSON cannot spoof another client.
            payload["harness"] = "opencode"
            return runtime.beyin(action, payload)
        raise ValueError("unknown_action")
