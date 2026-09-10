"""Deterministic, zero-dependency generator.

Runs with no API key and no network call — every field is computed from
rule-based heuristics against the actual profile/experience data in
`RoadmapContext`, plus the setup answers (target role, timeline, weekly
commitment, primary goal) the user chose. This is the fallback path only:
when `OPENAI_API_KEY` is configured, `factory.py` switches to
`LangGraphRoadmapGenerator`, whose system prompt is where the platform's
real depth guarantee lives (role-specific, dependency-aware curricula for
arbitrary target roles). This generator cannot reasonably build an
exhaustive, dependency-aware curriculum for every possible target role
without a live model — its job is narrower: stay honest (never fabricate a
skill the profile doesn't show, never invent a resource URL) and produce a
genuinely gap-driven, correctly-shaped roadmap for the common technical
roles in `_ROLE_SKILL_LIBRARY`, falling back to a generic technical
baseline for anything else.

Every heuristic here is intentionally simple and inspectable. No field is
ever a "trust me" output — every objective exists because of a specific,
named gap or a specific, named goal, never a generic filler line.
"""

from app.career_roadmap.schemas.roadmap import (
    IndustryLandscape,
    RoadmapContent,
    RoadmapMilestone,
    RoadmapObjective,
    RoadmapPhase,
    RoadmapResource,
    StartingPoint,
)
from app.career_roadmap.services.generators.base import BaseRoadmapGenerator
from app.career_roadmap.utils.context import RoadmapContext

# ---- role -> core skill vocabulary, in rough dependency order ------------
#
# Matched against `target_role` by substring, most-specific key first (so
# "llm engineer" matches before the more generic "engineer" would). A role
# that matches nothing falls back to _GENERIC_ROLE_SKILLS — still a real,
# defensible technical baseline, just not role-specific.
_ROLE_SKILL_LIBRARY: dict[str, list[str]] = {
    "llm engineer": [
        "python", "pytorch", "transformers", "prompt engineering", "vector databases",
        "rag", "langchain", "fine-tuning",
    ],
    "ai engineer": ["python", "machine learning", "pytorch", "vector databases", "prompt engineering", "mlops"],
    "machine learning engineer": [
        "python", "statistics", "pytorch", "scikit-learn", "mlops", "data pipelines",
    ],
    "ml engineer": ["python", "statistics", "pytorch", "scikit-learn", "mlops"],
    "data scientist": ["python", "statistics", "sql", "pandas", "machine learning", "data visualization"],
    "data analyst": ["sql", "statistics", "data visualization", "python"],
    "data engineer": ["python", "sql", "data pipelines", "etl", "cloud", "distributed systems"],
    "backend engineer": ["python", "sql", "databases", "api design", "system design", "git"],
    "backend developer": ["python", "sql", "databases", "api design", "system design", "git"],
    "frontend engineer": ["html", "css", "javascript", "react", "typescript", "git"],
    "frontend developer": ["html", "css", "javascript", "react", "typescript", "git"],
    "full stack developer": ["javascript", "react", "node.js", "sql", "api design", "git"],
    "full stack engineer": ["javascript", "react", "node.js", "sql", "api design", "git"],
    "devops engineer": ["linux", "docker", "kubernetes", "ci/cd", "cloud", "infrastructure as code"],
    "cloud engineer": ["networking", "cloud", "infrastructure as code", "docker", "kubernetes"],
    "product manager": ["user research", "product strategy", "roadmapping", "analytics", "communication"],
    "mobile developer": ["git", "rest apis", "mobile ui", "swift", "kotlin"],
    "ios developer": ["git", "rest apis", "mobile ui", "swift"],
    "android developer": ["git", "rest apis", "mobile ui", "kotlin"],
    "cybersecurity engineer": ["networking", "linux", "security fundamentals", "scripting"],
    "software engineer": ["data structures", "algorithms", "git", "system design", "testing"],
}
_GENERIC_ROLE_SKILLS = ["git", "system design", "testing", "technical communication"]

# ---- role -> current industry landscape --------------------------------
#
# Distinct in kind from `_ROLE_SKILL_LIBRARY`/`_TOPIC_LIBRARY` above: those
# describe what THIS roadmap teaches the candidate; this describes what the
# field looks like right now, independent of the candidate's own gaps — see
# schemas/roadmap.py's `IndustryLandscape` docstring. Kept deliberately
# conservative (well-established frameworks/tools and trends, not
# speculative or rapidly-shifting bleeding-edge claims), matching the same
# standard the system prompt holds the LLM generator to.
_INDUSTRY_LANDSCAPE_LIBRARY: dict[str, dict] = {
    "llm engineer": {
        "current_frameworks_and_tools": [
            "PyTorch", "Hugging Face Transformers", "LangChain / LlamaIndex for orchestration",
            "vector databases (Pinecone, Weaviate, pgvector)", "vLLM / TGI for inference serving",
        ],
        "emerging_trends": [
            "retrieval-augmented generation (RAG) as the default pattern for grounding model output",
            "structured/tool-calling outputs replacing free-text prompting for production use cases",
            "growing use of evaluation frameworks (e.g. RAGAS-style metrics) to measure retrieval and generation quality",
        ],
        "why_this_matters": "This field's tooling moves quickly — knowing the current stack, not just the "
        "underlying theory, is often what separates a candidate who can discuss LLMs from one who can "
        "actually ship an LLM-backed product.",
    },
    "ai engineer": {
        "current_frameworks_and_tools": [
            "PyTorch", "Hugging Face ecosystem", "vector databases for retrieval", "MLflow for experiment tracking",
            "cloud-managed inference endpoints (SageMaker, Vertex AI, Azure ML)",
        ],
        "emerging_trends": [
            "a shift from training models from scratch toward adapting and serving pretrained foundation models",
            "increasing emphasis on production concerns (latency, cost, monitoring) over pure model accuracy",
        ],
        "why_this_matters": "AI Engineer roles increasingly sit closer to production systems than pure research — "
        "understanding the current serving/tooling landscape is as relevant as understanding the models themselves.",
    },
    "machine learning engineer": {
        "current_frameworks_and_tools": [
            "PyTorch (the dominant framework for new model development)", "scikit-learn for classical ML",
            "MLflow / Weights & Biases for experiment tracking", "Docker + Kubernetes for model serving",
        ],
        "emerging_trends": [
            "MLOps practices (versioned data/models, CI/CD for ML, monitoring for drift) becoming a baseline expectation, not a nice-to-have",
        ],
        "why_this_matters": "Production ML roles today weight the ability to reliably ship and monitor a model "
        "in production at least as heavily as the ability to train an accurate one.",
    },
    "ml engineer": {
        "current_frameworks_and_tools": [
            "PyTorch", "scikit-learn", "MLflow / Weights & Biases", "Docker + Kubernetes for serving",
        ],
        "emerging_trends": [
            "MLOps practices becoming a baseline expectation for production ML roles",
        ],
        "why_this_matters": "Production ML roles today weight reliable shipping and monitoring at least as "
        "heavily as model accuracy.",
    },
    "data scientist": {
        "current_frameworks_and_tools": [
            "pandas / NumPy", "scikit-learn", "Jupyter notebooks for exploration", "SQL as a daily tool, not a side skill",
            "dashboarding tools (Looker, Tableau, or similar) for communicating results",
        ],
        "emerging_trends": [
            "a growing expectation that data scientists can also ship lightweight production code, not just notebooks",
        ],
        "why_this_matters": "The strongest data scientist candidates today combine statistical rigor with the "
        "ability to actually deploy and communicate their findings, not just analyze data in isolation.",
    },
    "data analyst": {
        "current_frameworks_and_tools": [
            "SQL", "spreadsheets and BI tools (Looker, Tableau, Power BI)", "Python (pandas) for more complex analysis",
        ],
        "emerging_trends": [
            "growing expectation of basic scripting ability (Python or R) alongside traditional SQL/BI skills",
        ],
        "why_this_matters": "Analysts who can move fluidly between SQL, a BI tool, and light scripting are "
        "increasingly favored over those confined to a single tool.",
    },
    "data engineer": {
        "current_frameworks_and_tools": [
            "SQL", "cloud data warehouses (Snowflake, BigQuery, Redshift)", "orchestration tools (Airflow or similar)",
            "distributed processing (Spark) for large-scale pipelines",
        ],
        "emerging_trends": [
            "a shift toward managed cloud data platforms over self-hosted infrastructure",
            "growing emphasis on data quality/observability tooling, not just pipeline throughput",
        ],
        "why_this_matters": "Most current data engineering roles are built around cloud-managed platforms rather "
        "than the self-hosted stacks common a decade ago — familiarity with that shift matters for interviews.",
    },
    "backend engineer": {
        "current_frameworks_and_tools": [
            "a mainstream backend framework for the target language (e.g. FastAPI/Django for Python, Express/NestJS for Node.js)",
            "PostgreSQL or similar relational databases", "Docker for local development and deployment",
            "REST or GraphQL for API design",
        ],
        "emerging_trends": [
            "growing adoption of typed APIs and schema-first API design",
        ],
        "why_this_matters": "Backend hiring increasingly expects familiarity with containerized deployment "
        "workflows, not just application code in isolation.",
    },
    "backend developer": {
        "current_frameworks_and_tools": [
            "a mainstream backend framework for the target language", "PostgreSQL or similar relational databases",
            "Docker for local development and deployment",
        ],
        "emerging_trends": [
            "growing adoption of typed APIs and schema-first API design",
        ],
        "why_this_matters": "Backend hiring increasingly expects familiarity with containerized deployment "
        "workflows, not just application code in isolation.",
    },
    "frontend engineer": {
        "current_frameworks_and_tools": [
            "React as the dominant UI library", "TypeScript over plain JavaScript for most new codebases",
            "a modern build tool (Vite or similar)", "a component-driven styling approach (Tailwind CSS or CSS-in-JS)",
        ],
        "emerging_trends": [
            "TypeScript adoption as close to a default expectation rather than a bonus skill",
            "server-driven rendering patterns (via meta-frameworks like Next.js) growing alongside pure client-side apps",
        ],
        "why_this_matters": "Most current frontend job postings assume TypeScript fluency, not just JavaScript — "
        "this shapes what's worth prioritizing early.",
    },
    "frontend developer": {
        "current_frameworks_and_tools": [
            "React as the dominant UI library", "TypeScript over plain JavaScript for most new codebases",
            "a modern build tool (Vite or similar)",
        ],
        "emerging_trends": [
            "TypeScript adoption as close to a default expectation rather than a bonus skill",
        ],
        "why_this_matters": "Most current frontend job postings assume TypeScript fluency, not just JavaScript.",
    },
    "full stack developer": {
        "current_frameworks_and_tools": [
            "React (or a similar component framework) on the frontend", "Node.js or a similar backend runtime",
            "PostgreSQL or similar for persistence", "TypeScript across both frontend and backend",
        ],
        "emerging_trends": [
            "full-stack meta-frameworks (e.g. Next.js) blurring the line between frontend and backend code",
        ],
        "why_this_matters": "Full-stack roles increasingly expect comfort with a single, shared language "
        "(TypeScript) across the entire stack rather than a hard split between frontend and backend tooling.",
    },
    "full stack engineer": {
        "current_frameworks_and_tools": [
            "React on the frontend", "Node.js or a similar backend runtime", "TypeScript across the stack",
        ],
        "emerging_trends": [
            "full-stack meta-frameworks blurring the line between frontend and backend code",
        ],
        "why_this_matters": "Full-stack roles increasingly expect a single shared language (TypeScript) across "
        "the whole stack.",
    },
    "devops engineer": {
        "current_frameworks_and_tools": [
            "Docker and Kubernetes for containerization/orchestration", "Terraform for infrastructure as code",
            "a CI/CD platform (GitHub Actions or similar)", "a major cloud provider (AWS, GCP, or Azure)",
        ],
        "emerging_trends": [
            "infrastructure-as-code as a baseline expectation rather than manual server configuration",
        ],
        "why_this_matters": "Current DevOps roles are defined almost entirely by containerized, cloud-native "
        "workflows — familiarity with manually-managed servers alone is no longer sufficient.",
    },
    "cloud engineer": {
        "current_frameworks_and_tools": [
            "a major cloud provider (AWS, GCP, or Azure)", "Terraform for infrastructure as code",
            "Docker and Kubernetes for workload deployment",
        ],
        "emerging_trends": [
            "multi-cloud and infrastructure-as-code skills increasingly expected together, not separately",
        ],
        "why_this_matters": "Cloud roles today are rarely single-provider-only — infrastructure-as-code fluency "
        "is what makes cloud skills portable across providers.",
    },
    "product manager": {
        "current_frameworks_and_tools": [
            "product analytics tools (Amplitude, Mixpanel, or similar)", "prioritization frameworks (RICE, or similar)",
            "collaborative design tools (Figma) for working with design",
        ],
        "emerging_trends": [
            "growing expectation that PMs can read basic product analytics/SQL themselves rather than always relying on a data team",
        ],
        "why_this_matters": "PMs who can independently pull and interpret basic usage data are increasingly "
        "differentiated from those who depend entirely on others for that insight.",
    },
    "mobile developer": {
        "current_frameworks_and_tools": [
            "Swift/SwiftUI for iOS", "Kotlin for Android", "a cross-platform framework (React Native or Flutter) where relevant",
        ],
        "emerging_trends": [
            "growing adoption of declarative UI frameworks (SwiftUI, Jetpack Compose) over older imperative UI toolkits",
        ],
        "why_this_matters": "Native mobile development has shifted toward declarative UI patterns — familiarity "
        "with the current toolkit generation matters for interviews at most companies.",
    },
    "ios developer": {
        "current_frameworks_and_tools": [
            "Swift and SwiftUI", "Xcode's current toolchain",
        ],
        "emerging_trends": [
            "SwiftUI increasingly the default for new iOS UI work over the older UIKit",
        ],
        "why_this_matters": "Most new iOS codebases and interview processes now assume SwiftUI familiarity.",
    },
    "android developer": {
        "current_frameworks_and_tools": [
            "Kotlin", "Jetpack Compose for UI", "Android's current toolchain",
        ],
        "emerging_trends": [
            "Jetpack Compose increasingly the default for new Android UI work over the older XML/View system",
        ],
        "why_this_matters": "Most new Android codebases and interview processes now assume Jetpack Compose familiarity.",
    },
    "cybersecurity engineer": {
        "current_frameworks_and_tools": [
            "the OWASP Top 10 as a shared baseline vocabulary", "cloud security tooling (given most workloads are now cloud-hosted)",
            "SIEM/logging tooling for detection and response",
        ],
        "emerging_trends": [
            "growing emphasis on cloud-native security (identity, misconfiguration) alongside traditional network security",
        ],
        "why_this_matters": "As more infrastructure moves to the cloud, cloud-specific security knowledge is "
        "increasingly as important as traditional network security fundamentals.",
    },
    "software engineer": {
        "current_frameworks_and_tools": [
            "Git and a standard code review workflow", "a mainstream language ecosystem relevant to the target company",
            "containerized development environments (Docker) at most companies",
        ],
        "emerging_trends": [
            "growing use of AI coding assistants as a normal part of the development workflow, alongside (not instead of) core fundamentals",
        ],
        "why_this_matters": "Interview processes increasingly assume comfort with modern collaborative tooling "
        "(code review, CI, containerization) on top of core data structures and algorithms knowledge.",
    },
}
_GENERIC_INDUSTRY_LANDSCAPE = {
    "current_frameworks_and_tools": ["Git for version control", "a containerized local development workflow (Docker)"],
    "emerging_trends": ["growing baseline expectations around collaborative tooling (code review, CI/CD) across most technical roles"],
    "why_this_matters": "Even outside role-specific tooling, most current technical hiring assumes comfort with "
    "standard collaborative development workflows.",
}

# ---- skill -> concrete sub-topics, for each objective's `topics` field ----
_TOPIC_LIBRARY: dict[str, list[str]] = {
    "python": ["core syntax & data structures", "functions & modules", "virtual environments", "writing basic tests"],
    "pytorch": ["tensors & autograd", "nn.Module & training loops", "GPU/device handling", "saving/loading models"],
    "transformers": ["self-attention", "positional encoding", "encoder/decoder architecture", "tokenization"],
    "prompt engineering": ["few-shot prompting", "system prompts", "structured/JSON outputs", "prompt evaluation"],
    "vector databases": ["embeddings", "cosine similarity", "indexing (HNSW/IVF)", "metadata filtering"],
    "rag": ["document ingestion", "chunking strategies", "retrieval", "context construction", "retrieval evaluation"],
    "langchain": ["chains & prompt templates", "retrievers", "output parsers", "agents/tool calling"],
    "fine-tuning": ["dataset preparation", "LoRA/PEFT", "evaluation", "overfitting risk"],
    "machine learning": ["supervised vs. unsupervised learning", "bias-variance trade-off", "model evaluation", "feature engineering"],
    "statistics": ["probability distributions", "hypothesis testing", "regression", "sampling"],
    "scikit-learn": ["pipelines", "cross-validation", "model selection", "preprocessing"],
    "mlops": ["experiment tracking", "model versioning", "CI/CD for ML", "monitoring in production"],
    "data pipelines": ["batch vs. streaming", "orchestration", "data quality checks"],
    "sql": ["joins", "aggregations", "indexing", "query optimization"],
    "pandas": ["dataframes", "groupby/aggregation", "merging & joining", "data cleaning"],
    "data visualization": ["chart selection", "storytelling with data", "dashboarding basics"],
    "etl": ["extraction patterns", "transformation logic", "idempotent loads"],
    "cloud": ["compute basics", "storage", "networking fundamentals", "identity & access management"],
    "distributed systems": ["CAP theorem", "partitioning", "replication", "consistency models"],
    "databases": ["normalization", "indexing", "transactions", "ACID properties"],
    "api design": ["REST conventions", "versioning", "authentication", "error handling"],
    "system design": ["scalability basics", "caching", "load balancing", "data store selection"],
    "git": ["branching strategies", "rebasing vs. merging", "pull request workflow"],
    "testing": ["unit tests", "integration tests", "mocking", "CI integration"],
    "javascript": ["closures", "async/await", "prototypes", "modern ES syntax"],
    "react": ["components & props", "hooks", "state management", "render behavior"],
    "html": ["semantic markup", "forms", "accessibility basics"],
    "css": ["flexbox & grid", "responsive design", "specificity"],
    "typescript": ["types & interfaces", "generics", "type narrowing"],
    "node.js": ["event loop", "streams", "building a minimal API server"],
    "linux": ["shell scripting", "process management", "file permissions"],
    "docker": ["images vs. containers", "writing a Dockerfile", "volumes", "container networking"],
    "kubernetes": ["pods & deployments", "services", "scaling", "config/secrets"],
    "ci/cd": ["pipeline stages", "build/test/deploy automation", "artifact management"],
    "infrastructure as code": ["declarative config basics", "state management", "modules/reuse"],
    "networking": ["TCP/IP basics", "DNS", "HTTP", "firewalls"],
    "security fundamentals": ["OWASP Top 10", "authentication vs. authorization", "encryption basics"],
    "scripting": ["automation basics", "scheduling/cron", "error handling in scripts"],
    "user research": ["interview techniques", "usability testing", "synthesizing findings"],
    "product strategy": ["market/competitive research", "prioritization frameworks"],
    "roadmapping": ["prioritization", "stakeholder alignment", "sequencing trade-offs"],
    "analytics": ["funnel analysis", "cohort analysis", "A/B testing basics"],
    "communication": ["writing specs", "stakeholder updates"],
    "swift": ["optionals", "structs vs. classes", "SwiftUI basics"],
    "kotlin": ["coroutines", "null safety", "Android lifecycle basics"],
    "mobile ui": ["layout systems", "navigation patterns"],
    "rest apis": ["HTTP verbs", "authentication", "pagination"],
    "data structures": ["arrays & strings", "trees", "graphs", "hash maps"],
    "algorithms": ["sorting & searching", "dynamic programming", "complexity analysis"],
    "technical communication": ["writing documentation", "explaining trade-offs clearly"],
}

# ---- skill -> resources. No `url` field, deliberately (see
# schemas/roadmap.py's `RoadmapResource` docstring): a resource is named
# precisely enough by title + provider + type that the user can find the
# current version themselves, rather than this system hard-coding a link
# that can go stale (moved, restructured, or dead) after the fact. ---------
_RESOURCE_LIBRARY: dict[str, list[dict]] = {
    "python": [
        {"title": "The Python Tutorial", "provider": "Python Software Foundation", "type": "documentation",
         "reason": "The canonical, official introduction to the language.", "free": True},
    ],
    "pytorch": [
        {"title": "PyTorch Tutorials", "provider": "PyTorch", "type": "documentation",
         "reason": "Official, example-driven tutorials covering tensors through full training loops.", "free": True},
    ],
    "transformers": [
        {"title": "Attention Is All You Need", "provider": "arXiv (Vaswani et al., 2017)", "type": "paper",
         "reason": "The original transformer architecture paper — the primary source for self-attention.", "free": True},
        {"title": "Hugging Face LLM/NLP Course", "provider": "Hugging Face", "type": "course",
         "reason": "Free, applied course covering transformer architecture and use.", "free": True},
    ],
    "rag": [
        {"title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks", "provider": "arXiv (Lewis et al., 2020)", "type": "paper",
         "reason": "The original RAG paper — the primary source for the retrieval + generation pattern.", "free": True},
    ],
    "fine-tuning": [
        {"title": "PEFT Documentation", "provider": "Hugging Face", "type": "documentation",
         "reason": "Official docs for parameter-efficient fine-tuning (LoRA and related methods).", "free": True},
    ],
    "langchain": [
        {"title": "LangChain Python Documentation", "provider": "LangChain", "type": "documentation",
         "reason": "Official documentation for the library this role's stack includes.", "free": True},
    ],
    "prompt engineering": [
        {"title": "Prompt Engineering Guide", "provider": "OpenAI", "type": "documentation",
         "reason": "Official guidance on structuring prompts reliably.", "free": True},
    ],
    "machine learning": [
        {"title": "Machine Learning Specialization", "provider": "Coursera / DeepLearning.AI (Andrew Ng)", "type": "course",
         "reason": "Widely-used structured foundation covering core ML concepts.", "free": False},
    ],
    "scikit-learn": [
        {"title": "scikit-learn Tutorials", "provider": "scikit-learn", "type": "documentation",
         "reason": "Official, example-driven documentation.", "free": True},
    ],
    "pandas": [
        {"title": "pandas Getting Started Guides", "provider": "pandas", "type": "documentation",
         "reason": "Official documentation covering core dataframe operations.", "free": True},
    ],
    "sql": [
        {"title": "PostgreSQL Tutorial", "provider": "PostgreSQL", "type": "documentation",
         "reason": "Official tutorial covering core SQL concepts on a real database engine.", "free": True},
    ],
    "system design": [
        {"title": "System Design Primer", "provider": "donnemartin (open-source, GitHub)", "type": "repository",
         "reason": "Widely-used, thorough open-source reference for system design fundamentals.", "free": True},
    ],
    "api design": [
        {"title": "REST API Guidelines", "provider": "Microsoft (open-source, GitHub)", "type": "repository",
         "reason": "A concrete, widely-referenced set of REST API design conventions.", "free": True},
    ],
    "git": [
        {"title": "Pro Git", "provider": "Scott Chacon & Ben Straub", "type": "book",
         "reason": "The official, free book covering Git from basics through internals.", "free": True},
    ],
    "testing": [
        {"title": "pytest Documentation", "provider": "pytest", "type": "documentation",
         "reason": "Official documentation for the most widely used Python testing framework.", "free": True},
    ],
    "javascript": [
        {"title": "JavaScript Guide", "provider": "MDN Web Docs", "type": "documentation",
         "reason": "The standard reference for the language.", "free": True},
    ],
    "react": [
        {"title": "React Documentation", "provider": "React", "type": "documentation",
         "reason": "The official, current documentation and tutorial.", "free": True},
    ],
    "html": [
        {"title": "HTML Documentation", "provider": "MDN Web Docs", "type": "documentation",
         "reason": "The standard reference for HTML.", "free": True},
    ],
    "css": [
        {"title": "CSS Documentation", "provider": "MDN Web Docs", "type": "documentation",
         "reason": "The standard reference for CSS.", "free": True},
    ],
    "typescript": [
        {"title": "TypeScript Handbook", "provider": "TypeScript", "type": "documentation",
         "reason": "The official language handbook.", "free": True},
    ],
    "node.js": [
        {"title": "Node.js Documentation", "provider": "Node.js", "type": "documentation",
         "reason": "Official documentation for the runtime.", "free": True},
    ],
    "docker": [
        {"title": "Docker Get Started Guide", "provider": "Docker", "type": "documentation",
         "reason": "Official, hands-on introduction.", "free": True},
    ],
    "kubernetes": [
        {"title": "Kubernetes Documentation", "provider": "Kubernetes", "type": "documentation",
         "reason": "The official documentation.", "free": True},
    ],
    "infrastructure as code": [
        {"title": "Terraform Documentation", "provider": "HashiCorp", "type": "documentation",
         "reason": "Official documentation for the most widely used IaC tool.", "free": True},
    ],
    "swift": [
        {"title": "Swift Documentation", "provider": "Swift.org", "type": "documentation",
         "reason": "Official language documentation.", "free": True},
    ],
    "kotlin": [
        {"title": "Kotlin Documentation", "provider": "Kotlin", "type": "documentation",
         "reason": "Official language documentation.", "free": True},
    ],
    "security fundamentals": [
        {"title": "OWASP Top 10", "provider": "OWASP", "type": "documentation",
         "reason": "The standard reference for the most common web security risks.", "free": True},
    ],
    "data structures": [
        {"title": "LeetCode", "provider": "LeetCode", "type": "practice",
         "reason": "The most widely used platform for structured data structure practice.", "free": True},
    ],
    "algorithms": [
        {"title": "LeetCode", "provider": "LeetCode", "type": "practice",
         "reason": "The most widely used platform for structured algorithm practice.", "free": True},
    ],
}


def _matching_role_skills(target_role: str) -> list[str]:
    role_lower = target_role.lower().strip()
    for key in sorted(_ROLE_SKILL_LIBRARY, key=len, reverse=True):
        if key in role_lower:
            return _ROLE_SKILL_LIBRARY[key]
    return _GENERIC_ROLE_SKILLS


def _industry_landscape_for(target_role: str) -> IndustryLandscape:
    role_lower = target_role.lower().strip()
    for key in sorted(_INDUSTRY_LANDSCAPE_LIBRARY, key=len, reverse=True):
        if key in role_lower:
            return IndustryLandscape(**_INDUSTRY_LANDSCAPE_LIBRARY[key])
    return IndustryLandscape(**_GENERIC_INDUSTRY_LANDSCAPE)


def _topics_for(skill: str) -> list[str]:
    return _TOPIC_LIBRARY.get(skill.lower(), [f"core concepts of {skill}", f"applied use of {skill}"])


def _resources_for(skill: str) -> list[RoadmapResource]:
    return [RoadmapResource(**resource) for resource in _RESOURCE_LIBRARY.get(skill.lower(), [])]


def _objectives_per_phase(weekly_commitment: int) -> int:
    return {5: 2, 10: 3, 15: 4, 20: 5}.get(weekly_commitment, 3)


def _hours_for(weekly_commitment: int, weeks: float) -> int:
    return max(1, round(weekly_commitment * weeks))


def _project_topics(target_role: str) -> list[str]:
    role_lower = target_role.lower()
    if any(key in role_lower for key in ("llm", "ai engineer", "machine learning", "ml engineer", "data scientist")):
        return ["data/model pipeline design", "evaluating results against a metric", "handling edge cases", "basic logging"]
    if any(key in role_lower for key in ("frontend", "full stack", "mobile", "ios", "android")):
        return ["component/screen architecture", "state management", "responsive/adaptive layout"]
    if any(key in role_lower for key in ("backend", "data engineer", "devops", "cloud")):
        return ["API/data contract design", "error handling", "persistence layer design", "basic testing"]
    return ["end-to-end implementation", "error handling", "basic testing", "documentation"]


_GOAL_LIBRARY: dict[str, dict] = {
    "Get an Internship": {
        "purpose": "Turn the portfolio built so far into internship applications and interview readiness.",
        "objectives": [
            ("Rewrite your resume and LinkedIn around this target role",
             "Lead with the project(s) and skills from earlier phases, not coursework.",
             "high", "Resume and LinkedIn both name-check the target role and the specific project(s) built.",
             ["Names the target role directly", "Leads with the shipped project, not a course list"]),
            ("Apply to a weekly batch of internships matching this role",
             "Sustain a steady weekly application cadence rather than one late batch.",
             "high", "A running list of applications submitted, with dates.",
             ["A dated log of applications exists and is updated weekly"]),
            ("Run two mock technical interviews",
             "Most rejections at this stage come from interview performance, not resume screening.",
             "medium", "Comfortable walking through your project and solving a live technical problem out loud.",
             ["Two mock interviews completed with specific feedback noted"]),
        ],
    },
    "Land a Full-Time Job": {
        "purpose": "Position the completed portfolio and skill set for full-time applications and interview loops.",
        "objectives": [
            ("Rewrite your resume and LinkedIn around this target role",
             "Lead with the project(s), skills, and any real work experience — full-time screens weight demonstrated impact.",
             "high", "Resume and LinkedIn both name-check the target role and quantify project/work outcomes.",
             ["Quantifies at least one outcome from a project or experience"]),
            ("Apply to a weekly batch of full-time roles matching this target",
             "A steady weekly cadence produces more interviews than a late rush.",
             "high", "A running list of applications submitted, with dates.",
             ["A dated log of applications exists and is updated weekly"]),
            ("Run two to three mock interviews covering both technical and behavioral rounds",
             "Full-time loops typically add behavioral/system-design rounds beyond an internship loop.",
             "medium", "Comfortable in both a live technical problem and a structured behavioral answer.",
             ["At least one technical and one behavioral mock interview completed"]),
        ],
    },
    "Prepare for Placements": {
        "purpose": "Build the technical fundamentals and interview reps that campus placement processes test for.",
        "objectives": [
            ("Work through a structured data structures & algorithms practice set",
             "Placement screens are still DSA-heavy at most companies regardless of the target role.",
             "high", "Comfortable solving medium-difficulty problems in the placement's primary language.",
             ["Consistently solves medium-difficulty problems within a reasonable time"]),
            ("Complete timed mock tests matching the placement format",
             "Timed practice under the real format is what actually transfers to test-day performance.",
             "medium", "Consistent completion within the real test's time limit.",
             ["At least one full timed mock completed within the limit"]),
            ("Prepare a 2-minute pitch connecting your project(s) to the target role",
             "Placement interviews are short — a rehearsed, specific pitch beats an improvised one.",
             "medium", "Can deliver the pitch fluently without reading from notes.",
             ["Can deliver the pitch without notes in under 2 minutes"]),
        ],
    },
    "Switch Career": {
        "purpose": "Build a credible bridge from your current background to this new target role.",
        "objectives": [
            ("Write a short career-change narrative",
             "Recruiters and interviewers will ask 'why the switch' directly — a clear, prepared answer removes the biggest source of doubt.",
             "high", "A 3-4 sentence narrative connecting your prior background to this target role.",
             ["The narrative names the prior background and the specific reason for the switch"]),
            ("Identify and message 3-5 people already working in this target role",
             "A career switch benefits disproportionately from real conversations with people already in the role.",
             "medium", "At least one real conversation completed and notes taken.",
             ["At least one completed conversation with notes"]),
            ("Reframe your resume around transferable skills and the new project(s)",
             "A resume that still reads as your old role will be filtered out before a human sees it.",
             "high", "Resume leads with the target role and the project(s) built in this roadmap, not the old title.",
             ["The target role appears in the resume's first section"]),
        ],
    },
    "Research": {
        "purpose": "Build the specific technical depth and supervised-work track record research tracks weight most heavily.",
        "objectives": [
            ("Identify 3-5 labs, professors, or research groups aligned with this target role",
             "Research opportunities are rarely posted publicly — direct outreach is the primary channel.",
             "high", "A shortlist with a one-line reason each one fits your interests.",
             ["A shortlist of 3-5 groups exists, each with a stated reason"]),
            ("Write and send a short outreach email to each",
             "A specific, well-targeted email gets meaningfully higher response rates than a generic one.",
             "high", "All outreach emails sent, referencing something specific about each group's work.",
             ["All outreach emails sent and reference specific published work"]),
            ("Write up your project work as a short technical report",
             "A written report is what a lab can actually evaluate — a project alone doesn't communicate research thinking.",
             "medium", "A short document stating a question, method, and result from your project work.",
             ["The report states a specific question, method, and result"]),
        ],
    },
    "Build Strong Portfolio": {
        "purpose": "Turn the single project built so far into a small, cohesive body of public work.",
        "objectives": [
            ("Scope and build a second project in a different area of the target role",
             "A single project can look like a one-off; a second project in a different area demonstrates range.",
             "high", "A second project shipped and public, distinct in focus from the first.",
             ["A second project is public and distinct in focus from the first"]),
            ("Write a short case study for each project",
             "A case study explaining the decisions behind a project is often what actually gets read.",
             "medium", "One short, specific write-up per project describing a real decision and its trade-off.",
             ["Each project has a case study naming a specific trade-off"]),
            ("Build a simple personal site linking both projects, your resume, and your GitHub",
             "A single link a recruiter can click through everything from is worth more than several scattered links.",
             "medium", "One live link containing both projects, a resume, and contact information.",
             ["One live link contains both projects, a resume, and contact info"]),
        ],
    },
}


class MockRoadmapGenerator(BaseRoadmapGenerator):
    name = "mock-v1"

    async def generate(self, context: RoadmapContext) -> RoadmapContent:
        role_skills = _matching_role_skills(context.target_role)
        skills_lower = {s.lower() for s in context.all_skills}
        missing_skills = [s for s in role_skills if s.lower() not in skills_lower]
        existing_skills = [s for s in role_skills if s.lower() in skills_lower]
        obj_count = _objectives_per_phase(context.weekly_commitment)

        n_phases = 3 if context.timeline_months == 3 else 4
        total_weeks = context.timeline_months * 4
        weeks_per_phase = total_weeks // n_phases
        remainder = total_weeks - weeks_per_phase * n_phases

        phases: list[RoadmapPhase] = [
            self._skill_gap_phase(context, missing_skills, existing_skills, weeks_per_phase, obj_count, 1),
            self._portfolio_phase(context, weeks_per_phase, obj_count, 2),
        ]
        if n_phases == 4:
            phases.append(self._depth_phase(context, weeks_per_phase, 3))
        phases.append(self._goal_phase(context, weeks_per_phase + remainder, len(phases) + 1))

        # builds_on/unlocks are filled in as a second pass, once every
        # phase's title is known — this is what turns the list into a
        # readable dependency chain rather than independent entries.
        for i, phase in enumerate(phases):
            phase.builds_on = [existing_skills[0]] if i == 0 and existing_skills else (
                ["No directly relevant prior skill logged on the profile"] if i == 0 else [phases[i - 1].title]
            )
            phase.unlocks = (
                [phases[i + 1].title] if i < len(phases) - 1
                else [f"Pursuing '{context.primary_goal}' for {context.target_role} with evidence in hand"]
            )

        starting_point = StartingPoint(
            existing_strengths=existing_skills,
            priority_gaps=missing_skills,
            roadmap_strategy=self._strategy_text(context, missing_skills, existing_skills),
        )

        return RoadmapContent(
            title=f"{context.target_role} Roadmap — {context.timeline_months} Months",
            target_role=context.target_role,
            overall_goal=context.primary_goal,
            estimated_duration=f"{context.timeline_months} months",
            overview=self._overview(context),
            industry_landscape=_industry_landscape_for(context.target_role),
            starting_point=starting_point,
            phases=phases,
            expected_skills=role_skills,
            portfolio_outcomes=self._portfolio_outcomes(context),
            final_outcome=self._final_outcome(context, missing_skills),
        )

    # ---- narrative text ----------------------------------------------------

    def _overview(self, context: RoadmapContext) -> str:
        return (
            f"This plan takes {context.full_name} from the current profile — {len(context.all_skills)} listed "
            f"skill(s) and {len(context.experiences)} logged experience(s) — toward {context.target_role} over "
            f"{context.timeline_months} months at {context.weekly_commitment} hours/week, with "
            f"'{context.primary_goal}' as the primary goal."
        )

    def _strategy_text(self, context: RoadmapContext, missing: list[str], existing: list[str]) -> str:
        if missing:
            return (
                f"The profile already shows {', '.join(existing) if existing else 'no directly matching core skill'} "
                f"for {context.target_role}, so this plan does not re-teach {'that' if len(existing) == 1 else 'those'}; "
                f"it prioritizes {', '.join(missing[:4])} first, since those are the gaps most likely to be noticed. "
                "Skill-building is sequenced before project work so the project can actually use what was just "
                f"learned, and project work is sequenced before the '{context.primary_goal}'-facing final phase."
            )
        return (
            f"Every core skill this plan checked for {context.target_role} is already on the profile, so it moves "
            "straight to applied depth and proof of work rather than re-teaching fundamentals, before the "
            f"'{context.primary_goal}'-facing final phase."
        )

    def _portfolio_outcomes(self, context: RoadmapContext) -> list[str]:
        outcomes = [f"One shipped, publicly linked project demonstrating {context.target_role}'s core skills end-to-end"]
        if context.timeline_months == 6:
            outcomes.append("A documented secondary differentiator (leadership role, hackathon entry, or open-source contribution)")
        outcomes.append("A short written case study explaining at least one real technical trade-off made")
        return outcomes

    def _final_outcome(self, context: RoadmapContext, missing: list[str]) -> str:
        goal_outcome = {
            "Get an Internship": "a portfolio and application history ready to convert internship applications into interviews",
            "Land a Full-Time Job": "a portfolio and application history ready to convert full-time applications into interviews",
            "Prepare for Placements": "the technical fundamentals and interview reps a placement process tests for",
            "Switch Career": "a credible, evidenced bridge from your prior background into this role",
            "Research": "outreach sent to real labs/groups and a written report demonstrating research thinking",
            "Build Strong Portfolio": "a small, cohesive body of public work across two or more projects",
        }.get(context.primary_goal, "a stronger, more evidenced profile for this target role")
        skills_text = ", ".join(missing) if missing else "this role's core stack, at an applied depth"
        return (
            f"By the end of this roadmap, {context.full_name} should be able to demonstrate hands-on, applied use "
            f"of {skills_text}; should have at least one shipped and public project as evidence; and should have "
            f"{goal_outcome}. Completing this roadmap does not guarantee employment or expert-level mastery — it "
            f"closes the specific gaps identified against {context.target_role} at the start of this plan."
        )

    # ---- phase builders ------------------------------------------------------

    def _skill_objective(self, context: RoadmapContext, skill: str, deepen: bool, priority: str) -> RoadmapObjective:
        if deepen:
            return RoadmapObjective(
                title=f"Deepen proficiency in {skill}",
                objective=f"Go beyond the current listed/tutorial-level use of {skill} toward something demonstrable.",
                why_it_matters=(
                    f"{skill} is already on the profile, so this roadmap does not re-teach it from zero — the gap "
                    "at this stage is depth and demonstrated use, not exposure."
                ),
                topics=_topics_for(skill),
                estimated_hours=_hours_for(context.weekly_commitment, 1.5),
                priority=priority,
                resources=_resources_for(skill),
                deliverable=f"A small applied exercise or contribution using {skill} beyond what's already shown on the profile.",
                completion_criteria=[
                    f"Can explain a non-trivial {skill} concept without notes",
                    f"Has one new applied example using {skill} added since starting this roadmap",
                ],
            )
        return RoadmapObjective(
            title=f"Build working proficiency in {skill}",
            objective=f"Build applied, working proficiency in {skill} from the ground up.",
            why_it_matters=(
                f"{skill} is a core requirement for {context.target_role} and is not currently supported by "
                "anything on the profile."
            ),
            topics=_topics_for(skill),
            estimated_hours=_hours_for(context.weekly_commitment, 1.5),
            priority=priority,
            resources=_resources_for(skill),
            deliverable=f"A small, self-contained exercise or notebook applying {skill} to a real (even if simple) problem.",
            completion_criteria=[
                f"Can explain {skill}'s core concepts without notes",
                f"Has a working, runnable example that uses {skill}",
            ],
        )

    def _skill_gap_phase(
        self,
        context: RoadmapContext,
        missing: list[str],
        existing: list[str],
        weeks: int,
        obj_count: int,
        phase_number: int,
    ) -> RoadmapPhase:
        if missing:
            target = missing[:obj_count]
            objectives = [
                self._skill_objective(context, skill, deepen=False, priority="high" if i < 2 else "medium")
                for i, skill in enumerate(target)
            ]
            title = "Close Core Skill Gaps"
            purpose = (
                f"Build the specific skills {context.target_role} requires that are not yet supported by the "
                f"profile: {', '.join(target)}."
            )
            personalization = (
                f"The profile already covers {', '.join(existing) if existing else 'none of this role’s core skills'} "
                f"for {context.target_role}, so this phase skips those entirely and focuses only on {', '.join(target)}."
            )
        else:
            target = (existing or ["this role's core stack"])[:obj_count]
            objectives = [
                self._skill_objective(context, skill, deepen=True, priority="medium") for skill in target
            ]
            title = "Validate and Deepen Existing Strengths"
            purpose = f"Confirm and deepen the skills already listed for {context.target_role} through applied practice."
            personalization = (
                f"Every core skill this roadmap checked for {context.target_role} is already on the profile "
                f"({', '.join(existing)}), so this phase moves straight to depth rather than re-teaching fundamentals."
            )
        return RoadmapPhase(
            phase_number=phase_number,
            title=title,
            duration_weeks=weeks,
            purpose=purpose,
            personalization_reason=personalization,
            objectives=objectives,
            milestone=RoadmapMilestone(
                title="Core skills established" if missing else "Depth confirmed",
                description=f"Baseline, applied proficiency across {', '.join(target)}.",
                completion_criteria=[
                    f"Has a working example or exercise for each of: {', '.join(target)}",
                    "Can discuss each without relying on notes",
                ],
            ),
        )

    def _portfolio_phase(self, context: RoadmapContext, weeks: int, obj_count: int, phase_number: int) -> RoadmapPhase:
        objectives = [
            RoadmapObjective(
                title=f"Scope one project that directly demonstrates {context.target_role}'s core skills",
                objective="Pick something small enough to finish in this phase but specific enough to clearly demonstrate this role's core skills.",
                why_it_matters="A vague or oversized project is the most common reason portfolio projects never ship — scoping is itself a skill this phase practices.",
                topics=["problem scoping", "defining a clear 'done' state", "minimum viable feature set"],
                estimated_hours=_hours_for(context.weekly_commitment, 1),
                priority="high",
                resources=[],
                deliverable="A one-paragraph project spec with a concrete, checkable definition of done.",
                completion_criteria=["The spec names a specific input, output, and success condition"],
            ),
            RoadmapObjective(
                title="Build and ship the project end-to-end",
                objective="Implement the scoped project fully, prioritizing a small complete system over a large incomplete one.",
                why_it_matters="An unfinished project demonstrates less than a small, complete one — both a recruiter and an automated match weight 'does it run' heavily.",
                topics=_project_topics(context.target_role),
                estimated_hours=_hours_for(context.weekly_commitment, max(weeks - 2, 1)),
                priority="high",
                resources=[],
                deliverable="A working project that runs start to finish, not a partial prototype.",
                completion_criteria=[
                    "Runs end-to-end without manual intervention",
                    "Uses at least one skill closed in the previous phase",
                ],
            ),
        ]
        if not context.has_portfolio_signal:
            objectives.append(
                RoadmapObjective(
                    title="Publish the project publicly",
                    objective="Push the project to a public GitHub repository and link it from the profile.",
                    why_it_matters="No GitHub or resume is currently on file — without a public link, nothing built in this phase is visible to a recruiter or automated match.",
                    topics=["README writing", "repository hygiene", "public visibility settings"],
                    estimated_hours=_hours_for(context.weekly_commitment, 1),
                    priority="high",
                    resources=[],
                    deliverable="A public repository link added to the profile.",
                    completion_criteria=["Repository is public and reachable", "README explains what the project does and how to run it"],
                )
            )
        else:
            objectives.append(
                RoadmapObjective(
                    title="Write a short case study explaining your technical decisions",
                    objective="Document the reasoning behind at least one real trade-off made while building the project.",
                    why_it_matters="A portfolio link already exists — the remaining gap is usually explaining the reasoning behind a project, not having a project at all.",
                    topics=["technical writing", "trade-off articulation", "architecture explanation"],
                    estimated_hours=_hours_for(context.weekly_commitment, 1),
                    priority="medium",
                    resources=[],
                    deliverable="A short write-up describing one real technical trade-off made and why.",
                    completion_criteria=["Names a specific alternative that was considered and rejected", "Explains the reasoning in plain language"],
                )
            )
        if obj_count >= 4:
            objectives.append(
                RoadmapObjective(
                    title="Evaluate and improve the shipped project",
                    objective="Identify one concrete weakness in the shipped project and address it.",
                    why_it_matters="Iterating on a shipped project (rather than starting a new one) demonstrates the same evaluative thinking a working engineer applies after an initial release.",
                    topics=["self-review", "identifying failure modes", "targeted improvement"],
                    estimated_hours=_hours_for(context.weekly_commitment, 1),
                    priority="medium",
                    resources=[],
                    deliverable="One concrete improvement shipped to the same project (a fixed edge case, a performance improvement, an added test).",
                    completion_criteria=["A specific, named weakness was identified", "A specific, named fix was shipped for it"],
                )
            )
        return RoadmapPhase(
            phase_number=phase_number,
            title="Build Proof of Work",
            duration_weeks=weeks,
            purpose=f"Ship one project that directly demonstrates {context.target_role}'s core skills, moving from learning to building.",
            personalization_reason=(
                "This phase exists because a finished, public project is the strongest evidence a recruiter or "
                "automated match can act on — stronger than any list of skills alone — and it can only happen "
                "after the previous phase's gaps are closed."
            ),
            objectives=objectives,
            milestone=RoadmapMilestone(
                title="One complete, shareable project",
                description="A project that is live/public and linked from the profile, demonstrating this role's core skills end-to-end.",
                completion_criteria=[
                    "Project runs end-to-end",
                    "Reachable from a public link on the profile",
                    "Uses at least one skill from the previous phase",
                ],
            ),
        )

    def _depth_phase(self, context: RoadmapContext, weeks: int, phase_number: int) -> RoadmapPhase:
        objectives = []
        if not context.has_leadership_signal:
            objectives.append(
                RoadmapObjective(
                    title="Take or document a lead role in a club, project team, or hackathon",
                    objective="Seek out or formalize a leadership-scoped responsibility, however small.",
                    why_it_matters="No leadership-scoped role is currently logged — recruiters and programs look for evidence of initiative beyond individual contribution, even in early-career candidates.",
                    topics=["scoping ownership", "coordinating with others", "communicating outcomes"],
                    estimated_hours=_hours_for(context.weekly_commitment, 2),
                    priority="medium",
                    resources=[],
                    deliverable="A specific, logged leadership role with a concrete outcome.",
                    completion_criteria=["A named role or responsibility exists", "A concrete outcome can be described"],
                )
            )
        if not context.has_hackathon_signal:
            objectives.append(
                RoadmapObjective(
                    title="Enter one hackathon",
                    objective="Participate in a hackathon relevant to this target role and ship something, even if rough.",
                    why_it_matters="Hackathons are one of the fastest ways to demonstrate shipping speed and teamwork under a real deadline, which coursework and solo projects don't test.",
                    topics=["rapid prototyping", "time-boxed scoping", "team collaboration"],
                    estimated_hours=_hours_for(context.weekly_commitment, 1),
                    priority="medium",
                    resources=[],
                    deliverable="One hackathon entered and something shipped, even if rough.",
                    completion_criteria=["Entered a real hackathon", "Shipped something within the event's time limit"],
                )
            )
        if not objectives:
            objectives.append(
                RoadmapObjective(
                    title="Contribute to an existing open-source project in this area",
                    objective="Find and land at least one merged contribution to a public repository relevant to this target role.",
                    why_it_matters="Leadership and hackathon signals are both already present — the remaining differentiator at this stage is public, reviewable code contributed to something beyond your own projects.",
                    topics=["reading unfamiliar codebases", "following contribution guidelines", "responding to code review"],
                    estimated_hours=_hours_for(context.weekly_commitment, 2),
                    priority="medium",
                    resources=[],
                    deliverable="At least one merged contribution to an existing public repository.",
                    completion_criteria=["A pull request was opened", "It was merged or explicitly accepted by a maintainer"],
                )
            )
        return RoadmapPhase(
            phase_number=phase_number,
            title="Depth & Differentiation",
            duration_weeks=weeks,
            purpose="Close the next most visible gap beyond core skills and a single project, using the extra time a longer timeline allows.",
            personalization_reason=(
                "With the additional time a 6-month plan allows beyond a 3-month one, this phase closes a "
                "secondary, differentiating gap rather than stopping at one project."
            ),
            objectives=objectives,
            milestone=RoadmapMilestone(
                title="Secondary differentiation signal added",
                description="One additional, differentiating signal beyond core skills and the first project.",
                completion_criteria=["A specific new entry (role, hackathon, or contribution) is logged on the profile"],
            ),
        )

    def _goal_phase(self, context: RoadmapContext, weeks: int, phase_number: int) -> RoadmapPhase:
        info = _GOAL_LIBRARY[context.primary_goal]
        objectives = [
            RoadmapObjective(
                title=title,
                objective=reason,
                why_it_matters=(
                    f"This directly serves the stated goal of '{context.primary_goal}' — everything built in "
                    f"earlier phases only pays off once it converts into this kind of action. {reason}"
                ),
                topics=[],
                estimated_hours=_hours_for(context.weekly_commitment, max(weeks // 3, 1)),
                priority=priority,
                resources=[],
                deliverable=expected_outcome,
                completion_criteria=criteria,
            )
            for title, reason, priority, expected_outcome, criteria in info["objectives"]
        ]
        return RoadmapPhase(
            phase_number=phase_number,
            title="Apply & Showcase",
            duration_weeks=weeks,
            purpose=info["purpose"],
            personalization_reason=(
                "This phase is last because everything built in earlier phases only pays off once it's put in "
                f"front of the people or processes that matter for '{context.primary_goal}'."
            ),
            objectives=objectives,
            milestone=RoadmapMilestone(
                title="Goal-facing action taken",
                description=f"Concrete progress toward '{context.primary_goal}'.",
                completion_criteria=["Applications submitted, outreach sent, or portfolio published, depending on the stated goal"],
            ),
        )
