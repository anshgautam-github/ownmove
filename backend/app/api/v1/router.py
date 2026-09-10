"""v1 API router.

Single place where every feature router is mounted. Adding a feature =
create a module under routes/ and register it here.
"""

from fastapi import APIRouter

from app.ai_coach.routers.coach_router import router as ai_coach_router
from app.api.v1.routes import (
    analytics,
    auth,
    health,
    ingestion,
    opportunities,
    profiles,
    recommendations,
)
from app.career_roadmap.routers.roadmap_router import router as career_roadmap_router
from app.career_simulation.routers.simulation_router import router as career_simulation_router
from app.profile_analysis.routers.analysis_router import router as profile_analysis_router

api_router = APIRouter()

# Health is unprefixed within v1 so it resolves at /api/v1/health.
api_router.include_router(health.router)

api_router.include_router(auth.router)
api_router.include_router(profiles.router)
api_router.include_router(opportunities.router)
api_router.include_router(recommendations.router)
api_router.include_router(analytics.router)
# Server-to-server trigger, not a user-facing feature -- see that
# module's own docstring for why it's guarded by a shared-secret header
# instead of CurrentUser, and why it's a plain APIRouter here rather than
# a self-contained feature module like career_roadmap/ etc.
api_router.include_router(ingestion.router)
# Self-contained feature modules (backend/app/profile_analysis/,
# backend/app/career_roadmap/) rather than a routes/services/schemas split
# across the top-level layer folders — see each module's README for why.
# Resolves at POST/GET /api/v1/career-ai/profile-analysis and
# POST/GET /api/v1/career-ai/career-roadmap respectively. The older,
# scaffolded roadmap/simulation/chat routers that used to live under
# routes/ (/api/v1/roadmap/..., /api/v1/simulation/..., /api/v1/chat/...)
# were removed -- they were pure 501 stubs, never called by the frontend,
# fully superseded by these real modules, and were unnecessary reachable
# API surface. See PRODUCTION_READINESS_SECURITY_AUDIT_2026-08-31.md
# finding #14.
api_router.include_router(profile_analysis_router)
api_router.include_router(career_roadmap_router)
api_router.include_router(career_simulation_router)
api_router.include_router(ai_coach_router)
