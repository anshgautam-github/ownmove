/**
 * Every FastAPI route the frontend will call, in one place.
 *
 * Declaring paths as data (rather than inline strings at call sites) means an
 * API version bump or a rename is a single edit here. These mirror the router
 * layout in backend/app/api/v1/routes/.
 *
 * None of these are wired into the UI yet — the backend endpoints are
 * scaffolded but not implemented.
 */

const V1 = '/api/v1';

export const endpoints = {
  health: `${V1}/health`,

  auth: {
    me: `${V1}/auth/me`,
    verify: `${V1}/auth/verify`,
  },

  profiles: {
    me: `${V1}/profiles/me`,
    update: `${V1}/profiles/me`,
    analysis: `${V1}/profiles/me/analysis`,
    strength: `${V1}/profiles/me/strength`,
  },

  // Career AI dashboard. Backed by self-contained modules
  // (backend/app/profile_analysis, backend/app/career_roadmap,
  // backend/app/career_simulation) rather than backend/app/services/*.py.
  careerAi: {
    profileAnalysis: `${V1}/career-ai/profile-analysis`,
    profileAnalysisHistory: `${V1}/career-ai/profile-analysis/history`,
    // Distinct from the unused `roadmap.*` block below, which points at the
    // older, still-scaffolded /api/v1/roadmap/... routes.
    careerRoadmap: `${V1}/career-ai/career-roadmap`,
    // Distinct from the unused `simulation.*` block below, same story as
    // `careerRoadmap` above vs. `roadmap.*`.
    careerSimulation: `${V1}/career-ai/career-simulation`,
    careerSimulationCompare: `${V1}/career-ai/career-simulation/compare`,
    careerSimulationHistory: `${V1}/career-ai/career-simulation/history`,
    careerSimulationDetail: (id) => `${V1}/career-ai/career-simulation/${id}`,
    careerSimulationDelete: (id) => `${V1}/career-ai/career-simulation/${id}`,
    // Distinct from the unused `chat.*` block below, same story as
    // `careerRoadmap` above vs. `roadmap.*`.
    aiCoachConversations: `${V1}/career-ai/ai-coach/conversations`,
    aiCoachConversation: (id) => `${V1}/career-ai/ai-coach/conversations/${id}`,
    aiCoachMessages: (id) => `${V1}/career-ai/ai-coach/conversations/${id}/messages`,
  },

  opportunities: {
    list: `${V1}/opportunities`,
    detail: (id) => `${V1}/opportunities/${id}`,
    search: `${V1}/opportunities/search`,
    saved: `${V1}/opportunities/saved`,
    save: (id) => `${V1}/opportunities/${id}/save`,
  },

  recommendations: {
    forYou: `${V1}/recommendations/for-you`,
    match: `${V1}/recommendations/match`,
    refresh: `${V1}/recommendations/refresh`,
  },

  roadmap: {
    generate: `${V1}/roadmap/generate`,
    current: `${V1}/roadmap/current`,
  },

  simulation: {
    run: `${V1}/simulation/run`,
    scenarios: `${V1}/simulation/scenarios`,
  },

  chat: {
    send: `${V1}/chat/messages`,
    stream: `${V1}/chat/stream`,
    conversations: `${V1}/chat/conversations`,
  },

  analytics: {
    track: `${V1}/analytics/events`,
    overview: `${V1}/analytics/overview`,
  },
};

export default endpoints;
