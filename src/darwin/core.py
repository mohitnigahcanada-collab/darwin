"""
Darwin core — public re-export layer.

All business logic lives in focused modules. This file re-exports everything so
existing callers (cli.py, mcp_server.py) continue to work without changes.
"""

# ── shared constants and helpers ───────────────────────────────────────────────
from darwin.common import (  # noqa: F401
    FORBIDDEN_FILES,
    INIT_DIRS,
    INIT_FILES,
    OPTIONAL_FILES,
    REQUIRED_FILES,
    RISK_ORDER,
    VALID_STATUSES,
    _append_memory_file,
    now,
    parse_card_field,
    parse_latest_result_status,
    parse_latest_review_verdict,
    parse_task_text,
    resolve_chunk_path,
    slug,
    write_if_missing,
)

# ── chunk OS ───────────────────────────────────────────────────────────────────
from darwin.chunk_ops import (  # noqa: F401
    _chunk_templates,
    op_get_file,
    op_init,
    op_list_chunks,
    op_next_chunk,
    op_prepare_chunk,
    op_read_chunk_files,
    op_record_result,
    op_review_chunk,
    op_split_plan,
    op_update_memory,
)

# ── eval harness ───────────────────────────────────────────────────────────────
from darwin.eval_ops import (  # noqa: F401
    EVAL_DIRS,
    EVAL_TASK_FILES,
    op_eval_init,
    op_eval_list,
    op_eval_report,
    op_eval_run,
)

# ── repo intake ────────────────────────────────────────────────────────────────
from darwin.repo_intake_ops import op_inspect_repo  # noqa: F401

# ── status / doctor / version ──────────────────────────────────────────────────
from darwin.status_ops import (  # noqa: F401
    op_doctor,
    op_status,
    op_version,
)

# ── spec surface ───────────────────────────────────────────────────────────────
from darwin.spec_ops import (  # noqa: F401
    op_spec_init,
    op_spec_status,
)

# ── tool registry ──────────────────────────────────────────────────────────────
from darwin.tool_registry_ops import (  # noqa: F401
    op_tool_init,
    op_tool_list,
    op_tool_suggest,
)

# ── feature registry ───────────────────────────────────────────────────────────
from darwin.feature_registry_ops import (  # noqa: F401
    op_feature_init,
    op_feature_list,
    op_feature_status,
)

# ── worker registry ────────────────────────────────────────────────────────────
from darwin.worker_registry_ops import (  # noqa: F401
    op_worker_init,
    op_worker_list,
    op_worker_suggest,
)

# ── batch planner ──────────────────────────────────────────────────────────────
from darwin.batch_plan_ops import op_batch_plan  # noqa: F401
