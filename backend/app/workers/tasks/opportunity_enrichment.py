"""AI enrichment for ingested opportunities. Not implemented yet.

Queued by `app.ingestion.services.opportunity_service.OpportunityService.
mark_for_enrichment()` via `app.workers.queue.get_queue()` — see that
module for what "enrichment" is expected to mean (richer tags, a cleaned
description, embedding generation, etc. — genuinely undecided yet, hence no
implementation here).
"""

from app.core.exceptions import NotImplementedYetError


async def enrich_opportunity(opportunity_id: str) -> None:
    raise NotImplementedYetError()
