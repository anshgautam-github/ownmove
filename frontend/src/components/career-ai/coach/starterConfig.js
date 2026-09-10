/** The four starter cards shown on the AI Coach landing screen (section 5
 * of the feature spec). Each is primarily a way to start a useful
 * conversation, not a separate workflow — clicking one pre-fills the ask
 * box rather than submitting immediately, so the user can adjust it to
 * their real situation before sending. */
export const STARTER_CARDS = [
  {
    key: 'decision',
    label: 'Make a Decision',
    example: 'Internship or another project?',
    prompt: 'I need to decide between two options: ',
  },
  {
    key: 'prioritization',
    label: 'Prioritize My Next Move',
    example: 'What should I focus on this month?',
    prompt: 'What should I focus on for the next few weeks, given ',
  },
  {
    key: 'evaluation',
    label: 'Evaluate Something',
    example: 'Is this course, internship, or project worth my time?',
    prompt: 'Is this worth doing for me: ',
  },
  {
    key: 'problem_solving',
    label: 'Work Through a Problem',
    example: "I'm applying but not getting interviews.",
    prompt: "I'm applying but not getting interviews. ",
  },
];
