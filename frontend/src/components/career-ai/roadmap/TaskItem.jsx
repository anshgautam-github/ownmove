// Superseded by ObjectiveItem.jsx.
//
// The roadmap schema was deepened from a flat per-phase `tasks` list to a
// richer per-phase `objectives` list (topics, resources, a concrete
// deliverable, observable completion criteria — see
// backend/app/career_roadmap/schemas/roadmap.py's `RoadmapObjective`).
// PhaseCard.jsx now renders `phase.objectives` via ObjectiveItem, not
// `phase.tasks` via this component. Left in place (rather than deleted)
// per this workspace's file-retention convention.
export {};
