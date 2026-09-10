-- ---------------------------------------------------------------------------
-- Follow-up to seeds/001_opportunities.sql, scoped to the "programs"
-- category only:
--
--   1. Four rows seeded in 001 had real names but placeholder
--      example.com/apply/... links. Those are corrected here to their real,
--      working application/info pages.
--   2. Ten more real (verified, currently active) student programs are
--      added — ambassador/leadership programs, fellowships, and open-source
--      programs, deliberately not internships, matching the character of
--      the rest of this category.
--
-- The UPDATEs are safe to re-run (they just re-set the same value). The
-- INSERT reuses 001's NOT EXISTS-on-(title, organization) guard, so this
-- file is also safe to run more than once.
-- ---------------------------------------------------------------------------

-- 1. Fix placeholder links on existing rows -----------------------------

update public.opportunities
set apply_url = 'https://builder.aws.com/community/student-builder-groups'
where title = 'AWS Cloud Clubs Captain' and organization = 'Amazon Web Services';

update public.opportunities
set apply_url = 'https://www.summerofbitcoin.org/'
where title = 'Summer of Bitcoin' and organization = 'Summer of Bitcoin';

update public.opportunities
set apply_url = 'https://www.spaceappschallenge.org/'
where title = 'NASA Space Apps Ambassador' and organization = 'NASA';

-- Google rebranded "Google Developer Student Clubs" to "Google Developer
-- Groups on Campus" in September 2024 — renamed to match, and relinked to
-- the real GDG community site instead of a generic developers.google.com
-- placeholder link.
update public.opportunities
set title = 'Google Developer Groups on Campus Lead',
    logo_url = 'https://www.google.com/s2/favicons?domain=gdg.community.dev&sz=128',
    apply_url = 'https://gdg.community.dev/'
where title = 'Google Developer Student Clubs Lead' and organization = 'Google';

-- 2. Ten more real programs ----------------------------------------------

insert into public.opportunities
  (category, title, organization, logo_url, description, location, is_remote, apply_url, tags, application_deadline)
select v.category, v.title, v.organization, v.logo_url, v.description, v.location,
       v.is_remote, v.apply_url, v.tags, v.application_deadline::date
from (
  values
    ('programs', 'beVisioneers: The Mercedes-Benz Fellowship', 'Mercedes-Benz', 'https://www.google.com/s2/favicons?domain=bevisioneers.world&sz=128', 'Global fellowship for aspiring eco-innovators aged 16-28, offering innovation training, mentorship, and project funding for environmental ideas.', 'Remote', true, 'https://www.bevisioneers.world/', array['Fellowship', 'Sustainability', 'Mentorship'], null),
    ('programs', 'GirlScript Summer of Code', 'GirlScript Foundation', 'https://www.google.com/s2/favicons?domain=gssoc.girlscript.org&sz=128', 'India''s largest free open-source program — contribute to real projects, get mentored, and grow your GitHub profile over a multi-month cycle.', 'Remote', true, 'https://gssoc.girlscript.org/', array['Open Source', 'Mentorship', 'Community'], null),
    ('programs', 'MLH Fellowship', 'Major League Hacking', 'https://www.google.com/s2/favicons?domain=fellowship.mlh.io&sz=128', 'Fully remote 12-week internship alternative: earn a stipend while contributing to real open-source projects under the guidance of expert mentors.', 'Remote', true, 'https://fellowship.mlh.io/', array['Open Source', 'Software Engineering', 'Mentorship'], null),
    ('programs', 'GitHub Campus Experts', 'GitHub', 'https://www.google.com/s2/favicons?domain=github.com&sz=128', 'Train as a student technology leader, build a developer community on your campus, and get access to GitHub swag, sponsorship, and events.', 'Remote', true, 'https://github.com/campus-experts', array['Ambassador', 'Community', 'Developer'], null),
    ('programs', 'Notion Campus Leaders', 'Notion', 'https://www.google.com/s2/favicons?domain=notion.com&sz=128', 'Represent Notion on campus — host events, build templates, and grow a student community as part of a global network of Campus Leaders.', 'Remote', true, 'https://ntn.so/campus-leaders', array['Ambassador', 'Community'], null),
    ('programs', 'ColorStack Membership', 'ColorStack', 'https://www.google.com/s2/favicons?domain=colorstack.org&sz=128', 'Community for Black and Latinx undergraduate Computer Science students in the US and Canada, with mentorship, academic support, and access to top tech companies.', 'Remote', true, 'https://www.colorstack.org/students', array['Community', 'Diversity', 'Mentorship'], null),
    ('programs', 'Technovation Girls', 'Technovation', 'https://www.google.com/s2/favicons?domain=technovationchallenge.org&sz=128', 'Global program where girls learn to build mobile apps and AI solutions that address real problems in their communities, guided by volunteer mentors.', 'Remote', true, 'https://technovationchallenge.org/', array['STEM', 'AI', 'Women in Tech'], null),
    ('programs', 'Kode With Klossy', 'Kode With Klossy', 'https://www.google.com/s2/favicons?domain=kodewithklossy.com&sz=128', 'Free two-week coding camps for young women and gender-expansive youth aged 13-18, held in cities across the US.', 'United States', false, 'https://www.kodewithklossy.com/', array['Summer Camp', 'Women in Tech', 'Coding'], null),
    ('programs', 'Bank of America Student Leaders', 'Bank of America', 'https://www.google.com/s2/favicons?domain=bankofamerica.com&sz=128', 'Paid six-week summer internship with a nonprofit plus a national Leadership Summit, for community-minded students building career and civic-leadership skills.', 'United States', false, 'https://about.bankofamerica.com/en/making-an-impact/student-leaders', array['Leadership', 'Community', 'Paid Program'], null),
    ('programs', 'Adobe Creative Residency', 'Adobe', 'https://www.google.com/s2/favicons?domain=adobe.com&sz=128', 'Year-long, salaried residency supporting emerging creators as they pursue a personal passion project, with mentorship and full access to Adobe Creative Cloud.', 'Multiple Locations', false, 'https://www.adobe.com/about-adobe/creative-residency.html', array['Creative', 'Residency', 'Mentorship'], null)
) as v(category, title, organization, logo_url, description, location, is_remote, apply_url, tags, application_deadline)
where not exists (
  select 1 from public.opportunities o
  where o.title = v.title and o.organization = v.organization
);
