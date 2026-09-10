"""Application configuration.

All settings are read from the environment exactly once, validated by
pydantic, and exposed through a cached `get_settings()`. Nothing else in the
codebase should call `os.getenv` directly — that keeps configuration
discoverable and makes it trivial to swap values per environment.
"""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application -----------------------------------------------------
    APP_NAME: str = "Marketeam API"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    # Not currently read anywhere in the app (nothing branches on it) --
    # kept only because some .env files still set it. Defaults to False
    # rather than True so it's never a landmine if something starts
    # reading it later.
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # ---- CORS ------------------------------------------------------------
    # The Vite dev server origin. Add deployed frontend origins per env.
    #
    # `NoDecode` stops pydantic-settings from trying to JSON-parse the raw
    # .env string before our validator sees it — without it, a list[str]
    # field makes pydantic-settings assume the env value is JSON and it
    # throws on a plain comma-separated string like
    # "http://localhost:5173,http://127.0.0.1:5173".
    CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value):
        """Allow CORS_ORIGINS to be given as a comma-separated string in .env."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _reject_wildcard_cors_with_credentials(self) -> "Settings":
        """main.py always sets allow_credentials=True on CORSMiddleware, so
        a wildcard origin here would be a real misconfiguration (browsers
        themselves refuse `*` + credentials, but failing fast here catches
        it at boot instead of relying on that browser-side behavior)."""
        if "*" in self.CORS_ORIGINS:
            raise ValueError(
                "CORS_ORIGINS must not contain '*' -- this app always sends "
                "allow_credentials=True, and a wildcard origin combined with "
                "credentials is a real misconfiguration, not just a browser "
                "warning. List explicit origins instead."
            )
        return self

    # ---- Supabase --------------------------------------------------------
    # Supabase remains the source of truth for Postgres, Auth, Storage and RLS.
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    # Service-role key bypasses RLS. Server-side only — never expose to the
    # browser. Used for admin/background work (seeding, batch embeddings).
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    # Used to verify the JWTs the frontend forwards from Supabase Auth.
    SUPABASE_JWT_SECRET: str = ""
    SUPABASE_JWT_ALGORITHM: str = "HS256"
    SUPABASE_JWT_AUDIENCE: str = "authenticated"

    # Direct Postgres connection (needed for pgvector / heavy analytical work
    # that is impractical through PostgREST).
    DATABASE_URL: str = ""

    # ---- AI providers ----------------------------------------------------
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DEFAULT_LLM_PROVIDER: Literal["openai", "anthropic"] = "openai"
    DEFAULT_CHAT_MODEL: str = "gpt-4o-mini"
    # Local sentence-transformers model, not an API-backed one — no key
    # needed, runs in-process. Dimension must match the `vector(384)`
    # columns on public.profiles.embedding / public.opportunities.embedding
    # (see supabase/schema — those columns were added directly on the live
    # tables rather than via the separate profile_embeddings/
    # opportunity_embeddings tables schema/006_ai_embeddings.sql describes;
    # that file's 1536-dim design predates this and was never applied to
    # the live database, so app/vector/pgvector_store.py, which was written
    # against it, is intentionally left unused by the recommendation engine
    # below in favour of direct RPC calls against those columns).
    DEFAULT_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSIONS: int = 384
    # Optional: pins the on-disk cache directory sentence-transformers/
    # huggingface_hub download the model into (maps to the HF_HOME env var
    # read by huggingface_hub). Leave blank to use the library's default
    # (~/.cache/huggingface) — set this in Docker images that pre-bake the
    # model at build time so it doesn't try to re-download at runtime.
    EMBEDDING_MODEL_CACHE_DIR: str = ""

    # Profile Analysis is a multi-section structured-output call, worth a
    # stronger/pricier model than routine chat even if DEFAULT_CHAT_MODEL is
    # kept cheap. Empty means "fall back to DEFAULT_CHAT_MODEL" — see
    # profile_analysis/services/generators/factory.py.
    PROFILE_ANALYSIS_MODEL: str = ""

    @property
    def profile_analysis_model(self) -> str:
        return self.PROFILE_ANALYSIS_MODEL or self.DEFAULT_CHAT_MODEL

    # Career Roadmap is another multi-section structured-output call — same
    # reasoning as PROFILE_ANALYSIS_MODEL above. Empty means "fall back to
    # DEFAULT_CHAT_MODEL" — see career_roadmap/services/generators/factory.py.
    CAREER_ROADMAP_MODEL: str = ""

    @property
    def career_roadmap_model(self) -> str:
        return self.CAREER_ROADMAP_MODEL or self.DEFAULT_CHAT_MODEL

    # Career Simulation is another structured-output call — same reasoning
    # as PROFILE_ANALYSIS_MODEL/CAREER_ROADMAP_MODEL above. Empty means
    # "fall back to DEFAULT_CHAT_MODEL" — see
    # career_simulation/services/generators/factory.py.
    CAREER_SIMULATION_MODEL: str = ""

    @property
    def career_simulation_model(self) -> str:
        return self.CAREER_SIMULATION_MODEL or self.DEFAULT_CHAT_MODEL

    # AI Coach is a conversational structured-output call — same reasoning
    # as the other *_MODEL settings above. Empty means "fall back to
    # DEFAULT_CHAT_MODEL" — see ai_coach/services/generators/factory.py.
    AI_COACH_MODEL: str = ""

    @property
    def ai_coach_model(self) -> str:
        return self.AI_COACH_MODEL or self.DEFAULT_CHAT_MODEL

    # ---- Vector search ---------------------------------------------------
    # Unused by the recommendation engine (app/services/recommendation_*)
    # — see the comment on DEFAULT_EMBEDDING_MODEL above. Left as-is for
    # app/vector/pgvector_store.py, which is still a stub.
    VECTOR_TABLE: str = "opportunity_embeddings"
    VECTOR_SEARCH_TOP_K: int = 10
    VECTOR_SIMILARITY_THRESHOLD: float = 0.7

    # ---- Recommendations (For You) ----------------------------------------
    # Ranking weights themselves live in app/services/ranking.py (one
    # centralized dict, per the product spec) — these are just the request
    # shape knobs, kept here so they're tunable per environment without a
    # code change.
    RECOMMENDATION_CANDIDATE_LIMIT: int = 50  # top-N pulled per retrieval leg
    RECOMMENDATION_RESULT_LIMIT: int = 24  # top-N returned after ranking
    # Bounded lazy backfill: how many opportunities missing an embedding
    # get embedded inline before a /for-you request is answered, vs. a
    # larger batch for an explicit /recommendations/refresh call. Keeps a
    # /for-you request's worst-case latency predictable — MiniLM-L6 on CPU
    # is fast, but not free — while still converging the corpus to fully
    # embedded over ordinary traffic without a background worker running
    # (ENABLE_BACKGROUND_WORKERS is off by default; see
    # app/workers/tasks/embeddings.py::backfill_opportunity_embeddings,
    # which calls the same EmbeddingService.backfill() once a worker does
    # pick this up).
    RECOMMENDATION_INLINE_BACKFILL_LIMIT: int = 20
    RECOMMENDATION_REFRESH_BACKFILL_LIMIT: int = 200

    # ---- Background jobs -------------------------------------------------
    REDIS_URL: str = ""
    ENABLE_BACKGROUND_WORKERS: bool = False

    # ---- Rate limiting -----------------------------------------------------
    # Redis-backed, distributed rate limiting for our own FastAPI endpoints
    # (app/core/rate_limiter.py, app/core/rate_limit_policy.py). Deliberately
    # separate from: Supabase Auth's own abuse protection on signup/login/
    # OAuth/password-recovery (a Supabase-dashboard concern, not this
    # codebase's — see backend/RATE_LIMITING.md); and
    # INGESTION_DEFAULT_RATE_LIMIT_PER_SECOND above, which throttles OUR
    # outbound requests to third-party sites, not inbound API traffic.
    #
    # Uses the same REDIS_URL as ENABLE_BACKGROUND_WORKERS. If REDIS_URL is
    # unset (or Redis is unreachable at request time), behavior is governed
    # per-category by RATE_LIMIT_FAIL_OPEN_* below rather than the app
    # crashing or hanging.
    RATE_LIMIT_ENABLED: bool = True

    # How many reverse-proxy hops in front of this service are trusted to
    # have themselves appended (not merely relayed) the real client IP to
    # X-Forwarded-For. 0 (the safe default) means trust nothing but the
    # direct TCP peer (request.client.host) and ignore
    # X-Forwarded-For/X-Real-IP entirely — correct when FastAPI is reachable
    # directly, or until the real deployment topology is confirmed. Set to 1
    # for exactly one trusted load balancer/proxy in front of every request,
    # 2 for e.g. CDN + LB, etc. See app/core/client_ip.py — getting this
    # wrong in the trusting direction lets a client forge its own
    # X-Forwarded-For and pick a fresh rate-limit bucket for every request.
    TRUSTED_PROXY_HOPS: int = 0

    # Fail-open: if Redis is unreachable, let the request through (logged at
    # ERROR) rather than taking ordinary read/write endpoints down over a
    # cache outage.
    RATE_LIMIT_FAIL_OPEN_DEFAULT: bool = True
    # Fail-closed for the AI/expensive tier specifically: if Redis is down we
    # cannot bound per-user/per-IP LLM spend, so these endpoints reject
    # (503) rather than risk unmetered AI-provider usage until Redis
    # recovers. Deliberately the opposite default from the tier above.
    RATE_LIMIT_FAIL_OPEN_AI: bool = False

    # Ordinary authenticated reads (GET) — cheap, DB-bound. Generous; this
    # exists to catch runaway/buggy clients, not to constrain normal use.
    RATE_LIMIT_AUTH_READ_PER_MINUTE: int = 120
    # Authenticated writes (POST/PUT/PATCH/DELETE) that are NOT AI/expensive
    # (e.g. deleting a saved simulation or coach conversation). Tighter than
    # reads (side effects), still generous for normal use.
    RATE_LIMIT_AUTH_WRITE_PER_MINUTE: int = 30

    # Expensive/AI-backed endpoints: Profile Analysis, Career Roadmap and
    # Career Simulation generation, AI Coach messages, and Recommendations
    # (LLM calls and/or CPU-bound embedding work — real external API cost on
    # the LLM-backed ones). The strictest tier, keyed per authenticated user
    # AND layered with a per-IP cap below. 10/minute gives headroom for a
    # real user iterating (e.g. regenerating a roadmap a few times) while
    # blocking scripted abuse; 100/day bounds total per-account cost
    # exposure.
    RATE_LIMIT_AI_PER_MINUTE: int = 10
    RATE_LIMIT_AI_PER_DAY: int = 100
    # IP-layer cap on the same AI tier — looser than the per-user cap (to
    # tolerate legitimate shared IPs: offices, campus/mobile NAT) but still
    # bounding "attacker creates many accounts from one IP/script," which a
    # per-user-only limit cannot catch.
    RATE_LIMIT_AI_IP_PER_MINUTE: int = 30
    RATE_LIMIT_AI_IP_PER_DAY: int = 300

    # Fallback for any future unauthenticated route. Nothing in this API
    # currently allows anonymous access — every real route requires
    # CurrentUser, and /health is exempt from rate limiting altogether, not
    # merely PUBLIC-classified (see app/api/v1/routes/health.py) — but this
    # exists so a future anonymous route isn't unprotected by default.
    RATE_LIMIT_PUBLIC_PER_MINUTE: int = 60

    # ---- Opportunity Ingestion ---------------------------------------------
    # Framework-wide defaults for `app.ingestion` agents — see
    # `app/ingestion/README.md`. Individual agents may override any of these
    # per-source via `AgentConfig`; these are just the sane starting point so
    # a new source's class doesn't have to specify every field.
    INGESTION_USER_AGENT: str = "OwnMoveOpportunityBot/1.0 (+https://ownmove.app; contact: support@ownmove.app)"
    INGESTION_DEFAULT_TIMEOUT_SECONDS: float = 15.0
    INGESTION_DEFAULT_MAX_RETRIES: int = 3
    INGESTION_DEFAULT_RETRY_BASE_DELAY_SECONDS: float = 1.0
    INGESTION_DEFAULT_RATE_LIMIT_PER_SECOND: float = 1.0
    INGESTION_DEFAULT_BURST: int = 2
    INGESTION_DEFAULT_MAX_CONCURRENCY: int = 5

    # ---- Hackathon ingestion (Devpost) -------------------------------------
    # The first real `app.ingestion` source agent (`app/ingestion/agents/
    # sources/devpost.py`) -- see `app/ingestion/README.md`. Kept as its own
    # small settings block rather than folded into INGESTION_DEFAULT_* above,
    # since these are specific to this one source/category, not
    # framework-wide defaults every future agent should inherit.
    DEVPOST_ENABLED: bool = True
    # Devpost is a third-party site we don't control, not our own API --
    # deliberately more conservative than INGESTION_DEFAULT_RATE_LIMIT_PER_SECOND/
    # INGESTION_DEFAULT_MAX_CONCURRENCY (see DevpostHackathonAgent.default_config()).
    DEVPOST_RATE_LIMIT_PER_SECOND: float = 0.5
    DEVPOST_REQUEST_TIMEOUT_SECONDS: float = 15.0
    # Hard ceiling on how many `/api/hackathons` listing pages discover() will
    # paginate through in one run, independent of the daily selection limit
    # below -- bounds worst-case request volume against Devpost even if
    # HACKATHON_DAILY_LIMIT is raised later or `status[]=open` briefly returns
    # far more open hackathons than usual.
    DEVPOST_MAX_DISCOVERY_PAGES: int = 6

    # Target number of hackathon opportunities INSERTED/UPDATED per
    # ingestion run -- NOT a cap on candidates processed. `discover()` ranks
    # (open-before-upcoming, soonest deadline, ...) and selects up to
    # `HACKATHON_CANDIDATE_POOL_SIZE` candidates for extract/normalize/
    # validate; `OpportunityService.save_batch()` then walks the *valid*
    # ones in that same rank order and stops as soon as
    # created + updated == HACKATHON_DAILY_LIMIT, so a handful of invalid or
    # unparseable candidates earlier in the ranking don't silently reduce
    # how many real, live hackathons actually land in the app below 20 (see
    # `app/ingestion/agents/sources/devpost.py`'s module docstring for the
    # full reasoning -- this was previously a cap on candidates *attempted*,
    # not opportunities *saved*; changed after a production-readiness review
    # concluded the product wants the latter). Today this effectively caps
    # Devpost specifically, since it's the only registered hackathon source;
    # if a second hackathon source is added later, whether they share this
    # one budget or each get their own is a product decision to make then,
    # not implied by the name now.
    HACKATHON_DAILY_LIMIT: int = 20

    # Hard upper bound on how many ranked candidates discover() will select
    # for extract()/normalize()/validate() in one run -- the safety margin
    # that makes "stop once HACKATHON_DAILY_LIMIT are saved" possible without
    # risking unbounded work if, say, every candidate this run happened to be
    # invalid or a duplicate. Must be >= HACKATHON_DAILY_LIMIT to be useful;
    # 3x gives real headroom (a handful of invalid/duplicate candidates
    # scattered through the ranked list) without processing Devpost's entire
    # "open" firehose on a day it's unusually large -- extract() itself is
    # free for Devpost (see that agent's module docstring), so this bound is
    # about discovery pagination and validation CPU work, not extra HTTP load
    # against Devpost beyond what DEVPOST_MAX_DISCOVERY_PAGES already caps.
    HACKATHON_CANDIDATE_POOL_SIZE: int = 60

    # ---- Hackathon ingestion (Devfolio) ------------------------------------
    # The second `app.ingestion` hackathon source (`app/ingestion/agents/
    # sources/devfolio.py`) -- shares HACKATHON_DAILY_LIMIT and
    # HACKATHON_CANDIDATE_POOL_SIZE above rather than getting its own copies
    # (both are already documented as hackathon-CATEGORY-wide, not
    # Devpost-specific -- see their own comments), per an explicit
    # instruction not to assume Devpost's tuning is right for a different
    # source while still reusing the existing configurable mechanism where
    # possible. Only the settings that are genuinely source-specific (HTTP
    # manners against a third-party site we don't control) get their own
    # Devfolio-prefixed entries, mirroring DEVPOST_ENABLED/
    # DEVPOST_RATE_LIMIT_PER_SECOND/DEVPOST_REQUEST_TIMEOUT_SECONDS above.
    #
    # Deliberately NO `DEVFOLIO_MAX_DISCOVERY_PAGES`: unlike Devpost's
    # `/api/hackathons?page=N` pagination, Devfolio's confirmed discovery
    # mechanism (see devfolio.py's module docstring) is a fixed two-request
    # sequence -- one HTML shell fetch to read a buildId, one
    # `_next/data/<buildId>/hackathons.json` fetch that already returns
    # every currently-listed hackathon across Devfolio's own open/upcoming/
    # past/featured buckets in a single response. There is no page count to
    # bound, so adding a page-cap setting that discover() would never read
    # would violate "only add configuration that is actually necessary."
    DEVFOLIO_ENABLED: bool = True
    # Devfolio is a third-party site we don't control, not our own API --
    # deliberately more conservative than INGESTION_DEFAULT_RATE_LIMIT_PER_SECOND
    # (see DevfolioAgent.default_config()). Two fixed requests per run means
    # this mostly governs the (small) delay between those two requests, not
    # sustained request volume.
    DEVFOLIO_RATE_LIMIT_PER_SECOND: float = 0.5
    DEVFOLIO_REQUEST_TIMEOUT_SECONDS: float = 15.0
    # Devfolio's listing endpoint (`hackathons.json`, used by discover())
    # never carries a usable cover image, free-text location, or long-form
    # description -- `settings.featured_cover_img`/`featured_cover_img_v2`
    # are confirmed always null there. Each hackathon's OWN page
    # (`_next/data/<buildId>/hackathon3/<slug>/overview.json`, same buildId
    # discover() already extracted -- confirmed reachable from the plain
    # devfolio.co domain, no per-hackathon subdomain request needed) DOES
    # have all three (`cover_img`, `location`, `desc`/`tagline`). When this
    # flag is on, extract() fetches that one extra per-candidate page
    # (skipped, not failed, on any error -- see extract()'s docstring) so
    # normalize() can populate logo_url/location/description from real
    # Devfolio data instead of leaving them empty. This is a genuine,
    # deliberate departure from this agent's original "zero extra requests"
    # design (mirrored from Devpost, where the single discovery call already
    # has everything) -- up to HACKATHON_CANDIDATE_POOL_SIZE extra requests
    # per run, at DEVFOLIO_RATE_LIMIT_PER_SECOND. This flag exists so that
    # trade-off can be turned off from config alone if it ever proves too
    # slow/unreliable against Devfolio, without a code change.
    DEVFOLIO_FETCH_LOGO_AND_DESCRIPTION: bool = True

    # Shared-secret header (`X-Ingestion-Admin-Key`) guarding
    # `api/v1/routes/ingestion.py`. Deliberately NOT built on
    # `CurrentUser`/Supabase JWT auth (see app/api/deps.py) -- those identify
    # a *person*, and nothing in this codebase has an admin/role concept yet
    # to layer on top of one (see that route module's own docstring for why
    # a full RBAC system would be over-building for a single trigger route).
    # Empty string (the default) means the route is unreachable -- fails
    # CLOSED, not open -- until an operator deliberately sets this.
    INGESTION_ADMIN_API_KEY: str = ""

    # ---- Observability ---------------------------------------------------
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "console"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached so the environment is parsed once per process."""
    return Settings()


settings = get_settings()
