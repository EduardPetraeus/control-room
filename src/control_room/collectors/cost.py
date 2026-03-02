from __future__ import annotations

import logging
from pathlib import Path

from control_room.collectors.governance import get_cost_data
from control_room.collectors.heartbeat import find_heartbeat_files, parse_heartbeat
from control_room.config import RepoConfig
from control_room.models.cost import CostSummary, SessionCost

logger = logging.getLogger(__name__)

DEFAULT_BUDGET_USD = 50.0


def collect_session_costs(repo_paths: list[Path]) -> list[SessionCost]:
    """Collect cost data from heartbeat files."""
    costs = []
    heartbeat_files = find_heartbeat_files(repo_paths)
    for hb_file in heartbeat_files:
        hb = parse_heartbeat(hb_file)
        if hb is not None and (hb.cost_usd > 0 or hb.tokens_used > 0):
            costs.append(
                SessionCost(
                    name=hb.session_id,
                    model=hb.model,
                    total_tokens=hb.tokens_used,
                    cost_usd=hb.cost_usd,
                )
            )
    return costs


def collect_repo_costs(repos: list[RepoConfig]) -> list[SessionCost]:
    """Collect cost data from repo COST_LOG.md files via governance collector."""
    costs = []
    for repo in repos:
        try:
            repo_path = Path(repo.path)
            cost_entries = get_cost_data(repo_path)
            for entry in cost_entries:
                costs.append(
                    SessionCost(
                        name=entry.get("session", repo.name),
                        model=entry.get("model", ""),
                        input_tokens=entry.get("input_tokens", 0),
                        output_tokens=entry.get("output_tokens", 0),
                        total_tokens=entry.get("input_tokens", 0) + entry.get("output_tokens", 0),
                        cost_usd=entry.get("cost", entry.get("cost_usd", 0.0)),
                    )
                )
        except Exception as e:
            logger.warning("Cost collection failed for %s: %s", repo.name, e)
    return costs


def build_cost_summary(
    repos: list[RepoConfig],
    budget_limit_usd: float = DEFAULT_BUDGET_USD,
) -> CostSummary:
    """Build aggregated cost summary from all sources."""
    repo_paths = [Path(r.path) for r in repos]

    all_costs: list[SessionCost] = []
    all_costs.extend(collect_session_costs(repo_paths))
    all_costs.extend(collect_repo_costs(repos))

    total_cost = sum(c.cost_usd for c in all_costs)
    total_tokens = sum(c.total_tokens for c in all_costs)

    # Cost by model
    cost_by_model: dict[str, float] = {}
    for c in all_costs:
        model = c.model or "unknown"
        cost_by_model[model] = cost_by_model.get(model, 0.0) + c.cost_usd

    budget_used_pct = (total_cost / budget_limit_usd * 100) if budget_limit_usd > 0 else 0.0
    budget_alert = budget_used_pct >= 80.0

    return CostSummary(
        total_cost_usd=total_cost,
        total_tokens=total_tokens,
        sessions=all_costs,
        budget_limit_usd=budget_limit_usd,
        budget_used_pct=budget_used_pct,
        budget_alert=budget_alert,
        cost_by_model=cost_by_model,
    )
