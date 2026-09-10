// Static catalog for the Learning Hub tab in Discover — a directory of
// official, company-run learning platforms (not third-party course
// aggregators), grouped loosely by focus area. Same rationale as
// certificationTracks.js: this is reference content that changes rarely, so
// a versioned source file is the right fit rather than a database table.
//
// Each platform entry:
//   name        - platform name
//   company     - the company that runs it
//   description - one sentence on what it's for
//   url         - the platform's own official homepage/landing page
//   category    - focus-area key, used to drive the pill filter

export const learningHubCategories = [
  { key: 'all', label: 'All' },
  { key: 'cloud-infrastructure', label: 'Cloud & Infrastructure' },
  { key: 'data-ai', label: 'Data & AI' },
  { key: 'software-development', label: 'Software Development' },
  { key: 'networking-security', label: 'Networking & Security' },
  { key: 'business-marketing', label: 'Business & Marketing' },
  { key: 'project-management', label: 'Project Management & Agile' },
  { key: 'design-product', label: 'Design & Product' },
  { key: 'professional-skills', label: 'Professional Skills' },
];

const learningPlatforms = [
  {
    name: 'Google Cloud Skills Boost',
    company: 'Google',
    description: 'Hands-on labs, courses, and skill badges across Google Cloud products, from foundations through specialized tracks.',
    url: 'https://www.cloudskillsboost.google/',
    category: 'cloud-infrastructure',
  },
  {
    name: 'Microsoft Learn',
    company: 'Microsoft',
    description: 'Free, self-paced learning paths covering Azure, Microsoft 365, Power Platform, and every Microsoft certification track.',
    url: 'https://learn.microsoft.com/',
    category: 'cloud-infrastructure',
  },
  {
    name: 'AWS Skill Builder',
    company: 'Amazon',
    description: 'Amazon\'s own training platform for AWS services, with free digital courses and certification exam prep.',
    url: 'https://skillbuilder.aws/',
    category: 'cloud-infrastructure',
  },
  {
    name: 'Red Hat Learning',
    company: 'Red Hat',
    description: 'Official Linux, OpenShift, and DevOps training and certification paths, including free introductory courses.',
    url: 'https://www.redhat.com/en/services/training-and-certification',
    category: 'cloud-infrastructure',
  },
  {
    name: 'Oracle University',
    company: 'Oracle',
    description: 'Oracle\'s learning platform (MyLearn) for Database, Java, Cloud Infrastructure, and APEX training and certification.',
    url: 'https://mylearn.oracle.com/',
    category: 'cloud-infrastructure',
  },
  {
    name: 'IBM SkillsBuild',
    company: 'IBM',
    description: 'Free courses and practical labs in AI, data, cybersecurity, and cloud, built for students and early-career learners.',
    url: 'https://skillsbuild.org/',
    category: 'data-ai',
  },
  {
    name: 'NVIDIA Deep Learning Institute',
    company: 'NVIDIA',
    description: 'Hands-on training in AI, accelerated computing, and generative AI, taught directly by the company building the hardware.',
    url: 'https://www.nvidia.com/en-us/training/',
    category: 'data-ai',
  },
  {
    name: 'Salesforce Trailhead',
    company: 'Salesforce',
    description: 'Gamified, hands-on learning for the entire Salesforce platform, from admin basics to Apex development.',
    url: 'https://trailhead.salesforce.com/',
    category: 'software-development',
  },
  {
    name: 'GitHub Skills',
    company: 'GitHub',
    description: 'Interactive, repository-based courses that teach Git, GitHub Actions, and collaborative development workflows by doing.',
    url: 'https://skills.github.com/',
    category: 'software-development',
  },
  {
    name: 'freeCodeCamp',
    company: 'freeCodeCamp.org',
    description: 'A free, nonprofit curriculum covering web development, data analysis, and machine learning, with project-based certifications.',
    url: 'https://www.freecodecamp.org/',
    category: 'software-development',
  },
  {
    name: 'Cisco Networking Academy',
    company: 'Cisco',
    description: 'Cisco\'s global IT and networking education program, covering everything from networking basics to cybersecurity.',
    url: 'https://www.netacad.com/',
    category: 'networking-security',
  },
  {
    name: 'Meta Blueprint',
    company: 'Meta',
    description: 'Meta\'s official education platform for advertising and marketing across Facebook, Instagram, and WhatsApp.',
    url: 'https://www.facebookblueprint.com/',
    category: 'business-marketing',
  },
  {
    name: 'Google Skillshop',
    company: 'Google',
    description: 'Google\'s official certification platform for Ads, Analytics, and Google Marketing Platform tools.',
    url: 'https://skillshop.withgoogle.com/',
    category: 'business-marketing',
  },
  {
    name: 'HubSpot Academy',
    company: 'HubSpot',
    description: 'Free courses and certifications in inbound marketing, sales, and CRM, built around HubSpot\'s own tools.',
    url: 'https://academy.hubspot.com/',
    category: 'business-marketing',
  },
  {
    name: 'SAP Learning',
    company: 'SAP',
    description: 'SAP\'s own learning journeys and certification prep across S/4HANA, business process integration, and more.',
    url: 'https://learning.sap.com/',
    category: 'business-marketing',
  },
  {
    name: 'Atlassian University',
    company: 'Atlassian',
    description: 'Official training on Jira, Confluence, and agile/ITSM practices, straight from the company that builds the tools.',
    url: 'https://university.atlassian.com/',
    category: 'project-management',
  },
  {
    name: 'Adobe Experience League',
    company: 'Adobe',
    description: 'Adobe\'s learning and certification hub for its Experience Cloud and creative applications.',
    url: 'https://experienceleague.adobe.com/en/certification-home',
    category: 'design-product',
  },
  {
    name: 'LinkedIn Learning',
    company: 'LinkedIn',
    description: 'A broad professional-skills library spanning business, creative, and technology topics, with courses tied to LinkedIn profiles.',
    url: 'https://www.linkedin.com/learning/',
    category: 'professional-skills',
  },
];

export default learningPlatforms;
