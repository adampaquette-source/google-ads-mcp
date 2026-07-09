"""AI Max built-in experiment (ADOPT_AI_MAX): propose, commit, schedule, end.

Google's built-in 50/50 AI Max experiment (Experiments > Campaign features and
settings > AI Max; API experiment type ADOPT_AI_MAX, added in Google Ads API
v24.1). It splits an existing Search campaign's traffic between a control arm
(AI Max off) and a treatment arm (AI Max on), so lift is measured incrementally
against the control instead of trusting AI Max's in-platform credit.

Flow, human-gated at each step (mirrors the project's propose/commit pattern):
  1. propose_ai_max_experiment()  -> validates + stores a JSON proposal, NO API call.
  2. commit_ai_max_experiment()   -> creates the Experiment (SETUP) + control and
                                     treatment arms. Still not running. dry_run=True
                                     builds the ops and returns them without any API call.
  3. schedule_ai_max_experiment() -> starts the experiment (long-running op). This is
                                     the step that actually spends money; requires an
                                     explicit, separate call after Adam's go.
  4. end_ai_max_experiment()      -> stop early (rollback is turning AI Max off, not
                                     deleting anything).

Preconditions Google enforces (see AI_MAX_SKILL.md section 10): the base campaign
must be Search on conversion Smart Bidding, not use a Portfolio bid strategy or a
shared budget, not target Display, have no other active experiment, and not use
legacy features. Nothing here un-pauses the base campaign; enable it first.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from google.ads.googleads.client import GoogleAdsClient


def _proposals_dir() -> Path:
    data_dir = os.environ.get("MCP_DATA_DIR", "").strip()
    if data_dir:
        d = Path(data_dir) / "creation_proposals"
        d.mkdir(parents=True, exist_ok=True)
        return d
    here = Path(__file__).resolve()
    root = here
    for _ in range(6):
        root = root.parent
        if (root / "pyproject.toml").exists():
            break
    d = root / "creation_proposals"
    d.mkdir(exist_ok=True)
    return d


def _proposal_path(proposal_id: str) -> Path:
    return _proposals_dir() / f"aimax_experiment_{proposal_id}.json"


def _validate(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not str(config.get("base_campaign_id", "")).strip():
        errors.append("base_campaign_id is required")
    if not str(config.get("experiment_name", "")).strip():
        errors.append("experiment_name is required")
    split = int(config.get("treatment_split", 50) or 50)
    if not (1 <= split <= 99):
        errors.append("treatment_split must be between 1 and 99 (percent)")
    if int(config.get("duration_days", 28) or 28) < 14:
        errors.append("duration_days must be >= 14 (AI Max needs a 14-day minimum read)")
    return errors


def propose_ai_max_experiment(
    client: GoogleAdsClient,
    customer_id: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Validate + store a pending AI Max experiment proposal. NO API changes.

    config keys: base_campaign_id (required), experiment_name (required),
    suffix (default "aimax", appended to the trial campaign name), treatment_split
    (percent to the AI Max arm, default 50), duration_days (default 28),
    description (optional).
    """
    cfg = dict(config)
    cfg.setdefault("suffix", "aimax")
    cfg.setdefault("treatment_split", 50)
    cfg.setdefault("duration_days", 28)
    cfg.setdefault("description", "AI Max incrementality test (built-in 50/50 experiment)")
    errors = _validate(cfg)
    if errors:
        raise ValueError("AI Max experiment config failed validation:\n"
                         + "\n".join(f"  - {e}" for e in errors))
    proposal_id = str(uuid.uuid4())[:8]
    proposal = {
        "proposal_id": proposal_id,
        "customer_id": customer_id,
        "config": cfg,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }
    _proposal_path(proposal_id).write_text(json.dumps(proposal, indent=2), encoding="utf-8")
    return proposal


def get_ai_max_experiment_proposal(proposal_id: str) -> dict[str, Any]:
    path = _proposal_path(proposal_id)
    if not path.exists():
        raise FileNotFoundError(
            f"No AI Max experiment proposal {proposal_id!r}. Run propose_ai_max_experiment() first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def commit_ai_max_experiment(
    client: GoogleAdsClient,
    proposal_id: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Create the Experiment (SETUP) + control and treatment arms. Does NOT start it.

    dry_run=True builds and returns a description of the operations without any API
    call (use to validate field/enum resolution before a real create).
    """
    proposal = get_ai_max_experiment_proposal(proposal_id)
    if proposal["status"] not in ("pending",) and not dry_run:
        raise ValueError(
            f"Proposal {proposal_id!r} has status {proposal['status']!r}; only pending can be committed."
        )
    customer_id = proposal["customer_id"]
    cfg = proposal["config"]
    campaign_id = str(cfg["base_campaign_id"])
    campaign_resource = f"customers/{customer_id}/campaigns/{campaign_id}"
    split = int(cfg.get("treatment_split", 50))
    start = date.today() + timedelta(days=1)
    end = start + timedelta(days=int(cfg.get("duration_days", 28)))

    # Experiment (type ADOPT_AI_MAX, SETUP). Temp resource name so arms can reference it.
    exp_temp = f"customers/{customer_id}/experiments/-1"
    exp_op = client.get_type("ExperimentOperation")
    e = exp_op.create
    e.resource_name = exp_temp
    e.name = str(cfg["experiment_name"])
    e.description = str(cfg.get("description", ""))
    e.suffix = str(cfg.get("suffix", "aimax"))
    e.type_ = client.enums.ExperimentTypeEnum.ADOPT_AI_MAX
    e.status = client.enums.ExperimentStatusEnum.SETUP
    e.start_date = start.strftime("%Y-%m-%d")
    e.end_date = end.strftime("%Y-%m-%d")

    # Arms: control (AI Max off, references the base campaign) + treatment (AI Max on;
    # Google creates the trial campaign for the ADOPT_AI_MAX type).
    control_op = client.get_type("ExperimentArmOperation")
    ca = control_op.create
    ca.experiment = exp_temp
    ca.name = "Control (no AI Max)"
    ca.control = True
    ca.traffic_split = 100 - split
    ca.campaigns.append(campaign_resource)

    treat_op = client.get_type("ExperimentArmOperation")
    ta = treat_op.create
    ta.experiment = exp_temp
    ta.name = "Treatment (AI Max)"
    ta.control = False
    ta.traffic_split = split
    ta.campaigns.append(campaign_resource)

    if dry_run:
        return {
            "dry_run": True,
            "experiment_name": e.name,
            "type": "ADOPT_AI_MAX",
            "base_campaign_id": campaign_id,
            "traffic_split": {"control": 100 - split, "treatment": split},
            "start_date": e.start_date,
            "end_date": e.end_date,
            "arms": ["Control (no AI Max)", "Treatment (AI Max)"],
        }

    exp_service = client.get_service("ExperimentService")
    exp_resp = exp_service.mutate_experiments(
        customer_id=customer_id, operations=[exp_op]
    )
    experiment_resource = exp_resp.results[0].resource_name

    # Re-point arms at the real experiment resource, then create them.
    ca.experiment = experiment_resource
    ta.experiment = experiment_resource
    arm_service = client.get_service("ExperimentArmService")
    arm_resp = arm_service.mutate_experiment_arms(
        customer_id=customer_id, operations=[control_op, treat_op]
    )
    arm_resources = [r.resource_name for r in arm_resp.results]

    proposal["status"] = "committed"
    proposal["experiment_resource"] = experiment_resource
    _proposal_path(proposal_id).write_text(json.dumps(proposal, indent=2), encoding="utf-8")

    return {
        "proposal_id": proposal_id,
        "experiment_resource": experiment_resource,
        "arm_resources": arm_resources,
        "status": "setup_not_scheduled",
        "note": "Experiment created in SETUP. Call schedule_ai_max_experiment() to start it (this is the step that spends).",
    }


def schedule_ai_max_experiment(
    client: GoogleAdsClient,
    experiment_resource: str,
    wait: bool = True,
) -> dict[str, Any]:
    """Start a SETUP experiment (long-running operation). This is the step that goes
    live and spends. Requires the base campaign to be ENABLED and eligible."""
    exp_service = client.get_service("ExperimentService")
    operation = exp_service.schedule_experiment(resource_name=experiment_resource)
    result: dict[str, Any] = {"experiment_resource": experiment_resource, "scheduled": True}
    if wait:
        operation.result()  # block until the schedule LRO completes
        result["lro_done"] = True
    return result


def end_ai_max_experiment(
    client: GoogleAdsClient,
    experiment_resource: str,
) -> dict[str, Any]:
    """Stop a running experiment early (rollback = AI Max off, nothing deleted)."""
    exp_service = client.get_service("ExperimentService")
    exp_service.end_experiment(experiment=experiment_resource)
    return {"experiment_resource": experiment_resource, "ended": True}
