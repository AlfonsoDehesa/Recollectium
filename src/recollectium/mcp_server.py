"""MCP server for Recollectium memory operations using FastMCP."""

from __future__ import annotations

import json
import logging
from typing import Annotated, Any, Literal, TypeAlias, cast

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from recollectium.config import RESPONSE_VERBOSITY_COMPACT, RESPONSE_VERBOSITY_VERBOSE
from recollectium.core import RecollectiumCore
from recollectium.models import SPACE_USER, SPACE_WORKSPACE
from recollectium.retrieval import UNSET, UnsetType
from recollectium.errors import RecollectiumError
from recollectium.representations import (
    OPERATION_CAPABILITIES_READ,
    OPERATION_EMBEDDING_JOBS_CLEAR,
    OPERATION_EMBEDDING_JOBS_GET,
    OPERATION_EMBEDDING_JOBS_LIST,
    OPERATION_EMBEDDING_REFRESH,
    OPERATION_EMBEDDING_STATUS,
    OPERATION_HEALTH_READ,
    OPERATION_MEMORIES_ADD,
    OPERATION_MEMORIES_ARCHIVE,
    OPERATION_MEMORIES_GET,
    OPERATION_MEMORIES_LIST,
    OPERATION_MEMORIES_SEARCH_USER,
    OPERATION_MEMORIES_SEARCH_WORKSPACE,
    OPERATION_MEMORIES_UPDATE,
    OPERATION_WORKSPACES_ALIASES_ADD,
    OPERATION_WORKSPACES_ALIASES_LIST,
    OPERATION_WORKSPACES_ALIASES_REMOVE,
    OPERATION_WORKSPACES_LIST,
    OPERATION_WORKSPACES_RENAME,
    OPERATION_WORKSPACES_RESOLVE,
    OPERATION_VERSION_READ,
    project_payload,
    validate_response_verbosity,
)
from recollectium.service_contract import (
    capabilities_payload,
    health_payload,
    serialize_embedding_job,
    serialize_embedding_jobs,
    serialize_embedding_operation_result,
    serialize_embedding_status,
    serialize_memories,
    serialize_memory,
    serialize_search_results,
    version_payload,
)

_log = logging.getLogger(__name__)

ResponseVerbosityArg = Annotated[
    Literal["compact", "verbose"] | None,
    Field(
        description=(
            "Optional response verbosity. Use 'compact' for token-sensitive, "
            "minimal JSON payloads or 'verbose' for full detail."
        ),
    ),
]
SearchProtectedMinimumArg: TypeAlias = Annotated[
    int,
    Field(
        description=(
            "Optional minimum number of highest-ranked matches protected from "
            "threshold filtering. Omit to use configuration defaults."
        ),
        ge=0,
        strict=True,
    ),
]
SearchMatchThresholdNumberArg: TypeAlias = Annotated[
    float,
    Field(
        description=(
            "Numeric semantic match threshold from 0.0 to 1.0. Omit to use "
            "configuration defaults."
        ),
        ge=0.0,
        le=1.0,
        strict=True,
    ),
]
SearchMatchThresholdArg: TypeAlias = (
    SearchMatchThresholdNumberArg | Literal["model_recommended_default"] | None
)
NonEmptyStringArg: TypeAlias = Annotated[str, Field(min_length=1)]
SpaceArg: TypeAlias = Annotated[
    Literal["user", "workspace"], Field(description="Memory space.")
]
StatusArg: TypeAlias = Annotated[
    Literal["active", "archived"] | None,
    Field(description="Optional memory status filter."),
]
StrictBoolArg: TypeAlias = Annotated[bool, Field(strict=True)]
PositiveLimitArg: TypeAlias = Annotated[int, Field(ge=1, strict=True)]
ConfidenceArg: TypeAlias = Annotated[float | None, Field(ge=0.0, le=1.0, strict=True)]


def create_mcp_server(core: RecollectiumCore) -> FastMCP:
    """Create a FastMCP server with Recollectium memory tools."""

    mcp = FastMCP("Recollectium")

    def _json(payload: Any) -> str:
        return json.dumps(payload, sort_keys=True)

    def _error(message: str) -> str:
        return _json({"error": message})

    def _strict_bool(name: str, value: object) -> bool | str:
        if type(value) is not bool:
            return f"{name} must be a JSON boolean"
        return value

    def _strict_int(
        name: str, value: object, *, minimum: int | None = None
    ) -> int | str:
        if type(value) is not int:
            return f"{name} must be a JSON integer"
        if minimum is not None and value < minimum:
            return f"{name} must be greater than or equal to {minimum}"
        return value

    def _strict_float(
        name: str,
        value: object,
        *,
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> float | None | str:
        if value is None:
            return None
        if type(value) not in {int, float}:
            return f"{name} must be a JSON number"
        numeric = float(cast(int | float, value))
        if minimum is not None and numeric < minimum:
            return f"{name} must be greater than or equal to {minimum}"
        if maximum is not None and numeric > maximum:
            return f"{name} must be less than or equal to {maximum}"
        return numeric

    def _search_overrides(
        *,
        limit: object,
        protected_minimum: object,
        match_threshold: object,
        include_archived: object,
    ) -> (
        tuple[
            int,
            int | UnsetType,
            float | None | Literal["model_recommended_default"] | UnsetType,
            bool,
        ]
        | str
    ):
        checked_limit = _strict_int("limit", limit, minimum=1)
        if isinstance(checked_limit, str):
            return checked_limit
        checked_archived = _strict_bool("include_archived", include_archived)
        if isinstance(checked_archived, str):
            return checked_archived
        checked_protected: int | UnsetType = UNSET
        if protected_minimum is not UNSET:
            parsed_protected = _strict_int(
                "protected_minimum", protected_minimum, minimum=0
            )
            if isinstance(parsed_protected, str):
                return parsed_protected
            checked_protected = parsed_protected
        checked_threshold: (
            float | None | Literal["model_recommended_default"] | UnsetType
        ) = UNSET
        if (
            match_threshold is not UNSET
            and match_threshold != "model_recommended_default"
            and match_threshold is not None
        ):
            parsed_threshold = _strict_float(
                "match_threshold", match_threshold, minimum=0.0, maximum=1.0
            )
            if isinstance(parsed_threshold, str):
                return parsed_threshold
            checked_threshold = parsed_threshold
        elif match_threshold == "model_recommended_default":
            checked_threshold = "model_recommended_default"
        elif match_threshold is None:
            checked_threshold = None
        return checked_limit, checked_protected, checked_threshold, checked_archived

    def _resolve_verbosity(verbosity: str | None) -> str:
        config_default = None
        config = getattr(core, "config", None)
        effective_config = getattr(config, "effective_config", None)
        if isinstance(effective_config, dict):
            value = effective_config.get("response_verbosity")
            if isinstance(value, str):
                config_default = value
        selected = verbosity if verbosity is not None else config_default
        if selected is None:
            selected = RESPONSE_VERBOSITY_COMPACT
        return validate_response_verbosity(selected).value

    @mcp.tool()
    def health(verbosity: ResponseVerbosityArg = None) -> str:
        """Return local Recollectium service health."""
        _resolve_verbosity(verbosity)
        return _json(
            project_payload(health_payload()["data"], operation=OPERATION_HEALTH_READ)
        )

    @mcp.tool()
    def version(verbosity: ResponseVerbosityArg = None) -> str:
        """Return Recollectium and local service API versions."""
        _resolve_verbosity(verbosity)
        return _json(
            project_payload(version_payload()["data"], operation=OPERATION_VERSION_READ)
        )

    @mcp.tool()
    def capabilities(verbosity: ResponseVerbosityArg = None) -> str:
        """Return local service capabilities and memory type enums."""
        resolved = _resolve_verbosity(verbosity)
        data = capabilities_payload()["data"]
        if resolved == RESPONSE_VERBOSITY_VERBOSE:
            data["response_verbosity"] = resolved
        return _json(
            project_payload(
                data,
                verbosity=resolved,
                operation=OPERATION_CAPABILITIES_READ,
            )
        )

    @mcp.tool()
    def search_user_memory(
        query: NonEmptyStringArg,
        type: str | None = None,
        limit: PositiveLimitArg = 20,
        protected_minimum: SearchProtectedMinimumArg | UnsetType = UNSET,
        match_threshold: SearchMatchThresholdArg | UnsetType = UNSET,
        include_archived: StrictBoolArg = False,
        verbosity: ResponseVerbosityArg = None,
    ) -> str:
        """Search user-space memories by semantic similarity to the query."""
        try:
            checked = _search_overrides(
                limit=limit,
                protected_minimum=protected_minimum,
                match_threshold=match_threshold,
                include_archived=include_archived,
            )
            if isinstance(checked, str):
                return _error(checked)
            limit, protected_minimum, match_threshold, include_archived = checked
            resolved = _resolve_verbosity(verbosity)
            results = core.search_user_memories(
                query=query,
                type=type,
                limit=limit,
                protected_minimum=protected_minimum,
                match_threshold=match_threshold,
                include_archived=include_archived,
            )
            return _json(
                serialize_search_results(
                    results,
                    verbosity=resolved,
                    operation=OPERATION_MEMORIES_SEARCH_USER,
                )
            )
        except RecollectiumError as e:
            _log.error(
                "MCP tool %s failed",
                "search_user_memory",
                extra={
                    "event": "mcp.search_user_memory_failed",
                    "context": {"error": str(e)},
                },
            )
            return _error(str(e))

    @mcp.tool()
    def search_workspace_memory(
        query: NonEmptyStringArg,
        workspace_uid: NonEmptyStringArg,
        type: str | None = None,
        limit: PositiveLimitArg = 20,
        protected_minimum: SearchProtectedMinimumArg | UnsetType = UNSET,
        match_threshold: SearchMatchThresholdArg | UnsetType = UNSET,
        include_archived: StrictBoolArg = False,
        verbosity: ResponseVerbosityArg = None,
    ) -> str:
        """Search workspace memories by semantic similarity to the query."""
        try:
            checked = _search_overrides(
                limit=limit,
                protected_minimum=protected_minimum,
                match_threshold=match_threshold,
                include_archived=include_archived,
            )
            if isinstance(checked, str):
                return _error(checked)
            limit, protected_minimum, match_threshold, include_archived = checked
            resolved = _resolve_verbosity(verbosity)
            results = core.search_workspace_memories(
                query=query,
                workspace_uid=workspace_uid,
                type=type,
                limit=limit,
                protected_minimum=protected_minimum,
                match_threshold=match_threshold,
                include_archived=include_archived,
            )
            return _json(
                serialize_search_results(
                    results,
                    verbosity=resolved,
                    operation=OPERATION_MEMORIES_SEARCH_WORKSPACE,
                )
            )
        except RecollectiumError as e:
            _log.error(
                "MCP tool %s failed",
                "search_workspace_memory",
                extra={
                    "event": "mcp.search_workspace_memory_failed",
                    "context": {"error": str(e)},
                },
            )
            return _error(str(e))

    def _hide_search_unset_schema_defaults() -> None:
        for tool_name in ("search_user_memory", "search_workspace_memory"):
            tool = mcp._tool_manager._tools[tool_name]
            properties = tool.parameters["properties"]
            for parameter_name in ("protected_minimum", "match_threshold"):
                schema = properties[parameter_name]
                schema.pop("default", None)
                options = [
                    option
                    for option in schema["anyOf"]
                    if option.get("$ref") != "#/$defs/_UnsetType"
                ]
                if len(options) == 1:
                    replacement = {"title": schema.get("title"), **options[0]}
                    properties[parameter_name] = {
                        key: value
                        for key, value in replacement.items()
                        if value is not None
                    }
                else:
                    schema["anyOf"] = options

    _hide_search_unset_schema_defaults()

    def _parse_metadata(
        metadata: str | dict[str, object] | None,
    ) -> dict[str, object] | None | str:
        if metadata is None:
            return None
        if isinstance(metadata, dict):
            return metadata
        if not isinstance(metadata, str):
            return "metadata must be a JSON object"
        try:
            parsed_metadata = json.loads(metadata)
        except json.JSONDecodeError:
            return "metadata must be valid JSON"
        if not isinstance(parsed_metadata, dict):
            return "metadata must be a JSON object"
        return parsed_metadata

    @mcp.tool()
    def add_memory(
        space: SpaceArg,
        type: NonEmptyStringArg,
        content: NonEmptyStringArg,
        workspace_uid: str | None = None,
        metadata: str | dict[str, object] | None = None,
        source: NonEmptyStringArg | None = None,
        confidence: ConfidenceArg = None,
        sensitivity: str | None = None,
        verbosity: ResponseVerbosityArg = None,
    ) -> str:
        """Add a new memory. Returns the created memory as JSON."""
        try:
            if space == SPACE_USER and workspace_uid is not None:
                return _error("workspace_uid is only valid for workspace memories")
            if space == SPACE_WORKSPACE and not workspace_uid:
                return _error("workspace_uid is required for workspace memories")
            checked_confidence = _strict_float(
                "confidence", confidence, minimum=0.0, maximum=1.0
            )
            if isinstance(checked_confidence, str):
                return _error(checked_confidence)
            resolved = _resolve_verbosity(verbosity)
            parsed_metadata = _parse_metadata(metadata)
            if isinstance(parsed_metadata, str):
                return _error(parsed_metadata)

            memory = core.add_memory(
                space=space,
                type=type,
                content=content,
                workspace_uid=workspace_uid,
                metadata=parsed_metadata,
                source=source,
                confidence=checked_confidence,
                sensitivity=sensitivity,
            )
            return _json(
                serialize_memory(
                    memory,
                    verbosity=resolved,
                    operation=OPERATION_MEMORIES_ADD,
                )
            )
        except RecollectiumError as e:
            _log.error(
                "MCP tool %s failed",
                "add_memory",
                extra={"event": "mcp.add_memory_failed", "context": {"error": str(e)}},
            )
            return _error(str(e))

    @mcp.tool()
    def get_memory(id: str, verbosity: ResponseVerbosityArg = None) -> str:
        """Get a single memory by ID. Returns the memory as JSON."""
        try:
            resolved = _resolve_verbosity(verbosity)
            memory = core.get_memory(id)
            return _json(
                serialize_memory(
                    memory,
                    verbosity=resolved,
                    operation=OPERATION_MEMORIES_GET,
                )
            )
        except RecollectiumError as e:
            _log.error(
                "MCP tool %s failed",
                "get_memory",
                extra={"event": "mcp.get_memory_failed", "context": {"error": str(e)}},
            )
            return _error(str(e))

    @mcp.tool()
    def update_memory(
        id: str,
        type: NonEmptyStringArg | None = None,
        content: NonEmptyStringArg | None = None,
        metadata: str | dict[str, object] | None = None,
        source: NonEmptyStringArg | None = None,
        confidence: ConfidenceArg = None,
        sensitivity: str | None = None,
        verbosity: ResponseVerbosityArg = None,
    ) -> str:
        """Update an existing memory. Returns the updated memory as JSON."""
        try:
            if not any(
                value is not None
                for value in (type, content, metadata, source, confidence, sensitivity)
            ):
                return _error("at least one update field is required")
            checked_confidence = _strict_float(
                "confidence", confidence, minimum=0.0, maximum=1.0
            )
            if isinstance(checked_confidence, str):
                return _error(checked_confidence)
            resolved = _resolve_verbosity(verbosity)
            parsed_metadata = _parse_metadata(metadata)
            if isinstance(parsed_metadata, str):
                return _error(parsed_metadata)

            memory = core.update_memory(
                id,
                type=type,
                content=content,
                metadata=parsed_metadata,
                source=source,
                confidence=checked_confidence,
                sensitivity=sensitivity,
            )
            return _json(
                serialize_memory(
                    memory,
                    verbosity=resolved,
                    operation=OPERATION_MEMORIES_UPDATE,
                )
            )
        except RecollectiumError as e:
            _log.error(
                "MCP tool %s failed",
                "update_memory",
                extra={
                    "event": "mcp.update_memory_failed",
                    "context": {"error": str(e)},
                },
            )
            return _error(str(e))

    @mcp.tool()
    def archive_memory(id: str, verbosity: ResponseVerbosityArg = None) -> str:
        """Archive a memory. Returns the archived memory as JSON."""
        try:
            resolved = _resolve_verbosity(verbosity)
            memory = core.archive_memory(id)
            return _json(
                serialize_memory(
                    memory,
                    verbosity=resolved,
                    operation=OPERATION_MEMORIES_ARCHIVE,
                )
            )
        except RecollectiumError as e:
            _log.error(
                "MCP tool %s failed",
                "archive_memory",
                extra={
                    "event": "mcp.archive_memory_failed",
                    "context": {"error": str(e)},
                },
            )
            return _error(str(e))

    @mcp.tool()
    def list_memories(
        space: Literal["user", "workspace"] | None = None,
        type: str | None = None,
        status: StatusArg = None,
        workspace_uid: str | None = None,
        include_archived: StrictBoolArg = False,
        limit: PositiveLimitArg | None = None,
        verbosity: ResponseVerbosityArg = None,
    ) -> str:
        """List memories, optionally filtered by space, type, status, workspace UID, and limit."""
        try:
            checked_archived = _strict_bool("include_archived", include_archived)
            if isinstance(checked_archived, str):
                return _error(checked_archived)
            if limit is not None:
                checked_limit = _strict_int("limit", limit, minimum=1)
                if isinstance(checked_limit, str):
                    return _error(checked_limit)
                limit = checked_limit
            resolved = _resolve_verbosity(verbosity)
            results = core.list_memories(
                space=space,
                type=type,
                status=status,
                workspace_uid=workspace_uid,
                include_archived=checked_archived,
                limit=limit,
            )
            return _json(
                serialize_memories(
                    results,
                    verbosity=resolved,
                    operation=OPERATION_MEMORIES_LIST,
                )
            )
        except RecollectiumError as e:
            _log.error(
                "MCP tool %s failed",
                "list_memories",
                extra={
                    "event": "mcp.list_memories_failed",
                    "context": {"error": str(e)},
                },
            )
            return _error(str(e))

    @mcp.tool()
    def list_workspaces(
        include_archived: StrictBoolArg = False,
        include_aliases: StrictBoolArg = False,
        verbosity: ResponseVerbosityArg = None,
    ) -> str:
        """List known workspace UIDs, optionally with aliases."""
        try:
            checked_archived = _strict_bool("include_archived", include_archived)
            if isinstance(checked_archived, str):
                return _error(checked_archived)
            checked_aliases = _strict_bool("include_aliases", include_aliases)
            if isinstance(checked_aliases, str):
                return _error(checked_aliases)
            resolved = _resolve_verbosity(verbosity)
            uids = core.list_workspaces(
                include_archived=checked_archived,
                include_aliases=checked_aliases,
                include_alias_records=checked_aliases
                and resolved == RESPONSE_VERBOSITY_VERBOSE,
            )
            return _json(
                project_payload(
                    uids, verbosity=resolved, operation=OPERATION_WORKSPACES_LIST
                )
            )
        except RecollectiumError as e:
            _log.error(
                "MCP tool %s failed",
                "list_workspaces",
                extra={
                    "event": "mcp.list_workspaces_failed",
                    "context": {"error": str(e)},
                },
            )
            return _error(str(e))

    @mcp.tool()
    def resolve_workspace(uid: str, verbosity: ResponseVerbosityArg = None) -> str:
        """Resolve a workspace UID candidate to its canonical UID."""
        try:
            resolved = _resolve_verbosity(verbosity)
            return _json(
                project_payload(
                    core.resolve_workspace(uid),
                    verbosity=resolved,
                    operation=OPERATION_WORKSPACES_RESOLVE,
                )
            )
        except RecollectiumError as e:
            _log.error(
                "MCP tool %s failed",
                "resolve_workspace",
                extra={
                    "event": "mcp.resolve_workspace_failed",
                    "context": {"error": str(e)},
                },
            )
            return _error(str(e))

    @mcp.tool()
    def add_workspace_alias(
        canonical_uid: str,
        alias_uid: str,
        migrate_existing: StrictBoolArg = False,
        verbosity: ResponseVerbosityArg = None,
    ) -> str:
        """Create an alias for a canonical workspace UID."""
        try:
            checked_migrate = _strict_bool("migrate_existing", migrate_existing)
            if isinstance(checked_migrate, str):
                return _error(checked_migrate)
            resolved = _resolve_verbosity(verbosity)
            result = core.add_workspace_alias(
                canonical_uid=canonical_uid,
                alias_uid=alias_uid,
                migrate_existing=checked_migrate,
            )
            return _json(
                project_payload(
                    result,
                    verbosity=resolved,
                    operation=OPERATION_WORKSPACES_ALIASES_ADD,
                )
            )
        except RecollectiumError as e:
            _log.error(
                "MCP tool %s failed",
                "add_workspace_alias",
                extra={
                    "event": "mcp.add_workspace_alias_failed",
                    "context": {"error": str(e)},
                },
            )
            return _error(str(e))

    @mcp.tool()
    def list_workspace_aliases(
        canonical_uid: str | None = None,
        verbosity: ResponseVerbosityArg = None,
    ) -> str:
        """List workspace alias mappings, optionally filtered by canonical UID."""
        try:
            resolved = _resolve_verbosity(verbosity)
            aliases = core.list_workspace_aliases(canonical_uid=canonical_uid)
            return _json(
                project_payload(
                    aliases,
                    verbosity=resolved,
                    operation=OPERATION_WORKSPACES_ALIASES_LIST,
                )
            )
        except RecollectiumError as e:
            _log.error(
                "MCP tool %s failed",
                "list_workspace_aliases",
                extra={
                    "event": "mcp.list_workspace_aliases_failed",
                    "context": {"error": str(e)},
                },
            )
            return _error(str(e))

    @mcp.tool()
    def remove_workspace_alias(
        alias_uid: str,
        verbosity: ResponseVerbosityArg = None,
    ) -> str:
        """Remove a workspace alias mapping."""
        try:
            resolved = _resolve_verbosity(verbosity)
            alias = core.remove_workspace_alias(alias_uid)
            return _json(
                project_payload(
                    alias,
                    verbosity=resolved,
                    operation=OPERATION_WORKSPACES_ALIASES_REMOVE,
                )
            )
        except RecollectiumError as e:
            _log.error(
                "MCP tool %s failed",
                "remove_workspace_alias",
                extra={
                    "event": "mcp.remove_workspace_alias_failed",
                    "context": {"error": str(e)},
                },
            )
            return _error(str(e))

    @mcp.tool()
    def rename_workspace(
        old_uid: str,
        new_uid: str,
        verbosity: ResponseVerbosityArg = None,
    ) -> str:
        """Rename a workspace. Migrates all workspace memories from old_uid to new_uid."""
        try:
            resolved = _resolve_verbosity(verbosity)
            result = core.rename_workspace(old_uid=old_uid, new_uid=new_uid)
            return _json(
                project_payload(
                    result,
                    verbosity=resolved,
                    operation=OPERATION_WORKSPACES_RENAME,
                )
            )
        except RecollectiumError as e:
            _log.error(
                "MCP tool %s failed",
                "rename_workspace",
                extra={
                    "event": "mcp.rename_workspace_failed",
                    "context": {"error": str(e)},
                },
            )
            return _error(str(e))

    @mcp.tool()
    def embedding_status(verbosity: ResponseVerbosityArg = None) -> str:
        """Get active local FastEmbed profile and startup job status."""
        try:
            resolved = _resolve_verbosity(verbosity)
            status = core.active_embedding_status()
            return _json(
                serialize_embedding_status(
                    status,
                    verbosity=resolved,
                    operation=OPERATION_EMBEDDING_STATUS,
                )
            )
        except RecollectiumError as e:
            _log.error(
                "MCP tool %s failed",
                "embedding_status",
                extra={
                    "event": "mcp.embedding_status_failed",
                    "context": {"error": str(e)},
                },
            )
            return _error(str(e))

    @mcp.tool()
    def embedding_jobs(
        state: Literal["queued", "running", "completed", "failed", "pending"]
        | None = None,
        limit: PositiveLimitArg | None = None,
        verbosity: ResponseVerbosityArg = None,
    ) -> str:
        """List embedding jobs, optionally filtered by state."""
        try:
            if limit is not None:
                checked_limit = _strict_int("limit", limit, minimum=1)
                if isinstance(checked_limit, str):
                    return _error(checked_limit)
                limit = checked_limit
            resolved = _resolve_verbosity(verbosity)
            jobs = core.list_embedding_jobs(state=state, limit=limit)
            return _json(
                serialize_embedding_jobs(
                    jobs,
                    verbosity=resolved,
                    operation=OPERATION_EMBEDDING_JOBS_LIST,
                )
            )
        except RecollectiumError as e:
            _log.error(
                "MCP tool %s failed",
                "embedding_jobs",
                extra={
                    "event": "mcp.embedding_jobs_failed",
                    "context": {"error": str(e)},
                },
            )
            return _error(str(e))

    @mcp.tool()
    def refresh_embeddings(
        space: Literal["user", "workspace"] | None = None,
        workspace_uid: str | None = None,
        include_archived: StrictBoolArg = False,
        verbosity: ResponseVerbosityArg = None,
    ) -> str:
        """Force stale embedding refresh inline and return the completed job summary."""
        try:
            checked_archived = _strict_bool("include_archived", include_archived)
            if isinstance(checked_archived, str):
                return _error(checked_archived)
            resolved = _resolve_verbosity(verbosity)
            result = core.refresh_stale_embeddings(
                space=space,
                workspace_uid=workspace_uid,
                include_archived=checked_archived,
            )
            return _json(
                serialize_embedding_operation_result(
                    result,
                    verbosity=resolved,
                    operation=OPERATION_EMBEDDING_REFRESH,
                )
            )
        except RecollectiumError as e:
            _log.error(
                "MCP tool %s failed",
                "refresh_embeddings",
                extra={
                    "event": "mcp.refresh_embeddings_failed",
                    "context": {"error": str(e)},
                },
            )
            return _error(str(e))

    @mcp.tool()
    def clear_embedding_jobs(
        states: list[str] | None = None,
        verbosity: ResponseVerbosityArg = None,
    ) -> str:
        """Delete embedding job audit records without deleting memories."""
        try:
            resolved = _resolve_verbosity(verbosity)
            result = core.clear_embedding_jobs(states=states)
            return _json(
                serialize_embedding_operation_result(
                    result,
                    verbosity=resolved,
                    operation=OPERATION_EMBEDDING_JOBS_CLEAR,
                )
            )
        except RecollectiumError as e:
            _log.error(
                "MCP tool %s failed",
                "clear_embedding_jobs",
                extra={
                    "event": "mcp.clear_embedding_jobs_failed",
                    "context": {"error": str(e)},
                },
            )
            return _error(str(e))

    @mcp.tool()
    def get_embedding_job(job_id: str, verbosity: ResponseVerbosityArg = None) -> str:
        """Get a single embedding job by ID."""
        try:
            resolved = _resolve_verbosity(verbosity)
            job = core.get_embedding_job(job_id)
            return _json(
                serialize_embedding_job(
                    job,
                    verbosity=resolved,
                    operation=OPERATION_EMBEDDING_JOBS_GET,
                )
            )
        except RecollectiumError as e:
            _log.error(
                "MCP tool %s failed",
                "get_embedding_job",
                extra={
                    "event": "mcp.get_embedding_job_failed",
                    "context": {"error": str(e)},
                },
            )
            return _error(str(e))

    def _finalize_tool_schemas() -> None:
        for tool in mcp._tool_manager._tools.values():
            tool.parameters["additionalProperties"] = False

    _finalize_tool_schemas()
    return mcp
