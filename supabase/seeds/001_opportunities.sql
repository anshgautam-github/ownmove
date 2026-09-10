-- ---------------------------------------------------------------------------
-- Seed data for the Discover categories.
--
-- Every insert is guarded with NOT EXISTS on (title, organization) so this
-- file is safe to run repeatedly — it will never create duplicates.
--
-- Logos use Google's free favicon endpoint. (Clearbit's logo API, the obvious
-- alternative, was shut down in Dec 2025 after the HubSpot acquisition.)
-- ---------------------------------------------------------------------------

insert into public.opportunities
  (category, title, organization, logo_url, description, location, is_remote, apply_url, tags, application_deadline)
select v.category, v.title, v.organization, v.logo_url, v.description, v.location,
       v.is_remote, v.apply_url, v.tags, v.application_deadline::date
from (
  values
    -- ------------------------------ internships ----------------------------
    ('internships', 'Frontend Engineering Intern', 'Notion', 'https://www.google.com/s2/favicons?domain=notion.so&sz=128', 'Build UI for millions of users alongside the core product team.', 'San Francisco, CA', false, 'https://example.com/apply/notion-frontend', array['React', 'JavaScript', 'Frontend'], '2026-09-15'),
    ('internships', 'Backend Intern', 'Razorpay', 'https://www.google.com/s2/favicons?domain=razorpay.com&sz=128', 'Work on payment infra used by thousands of businesses.', 'Bengaluru, India', false, 'https://example.com/apply/razorpay-backend', array['Node.js', 'SQL', 'Backend'], '2026-08-30'),
    ('internships', 'Data Science Intern', 'Zomato', 'https://www.google.com/s2/favicons?domain=zomato.com&sz=128', 'Build models that power recommendations and logistics.', 'Remote', true, 'https://example.com/apply/zomato-ds', array['Python', 'ML', 'Data Science'], '2026-09-01'),
    ('internships', 'Product Design Intern', 'Figma', 'https://www.google.com/s2/favicons?domain=figma.com&sz=128', 'Partner with PMs and engineers to ship new design tools.', 'Remote', true, 'https://example.com/apply/figma-design', array['Figma', 'UI/UX'], '2026-08-20'),
    ('internships', 'Growth Marketing Intern', 'Swiggy', 'https://www.google.com/s2/favicons?domain=swiggy.com&sz=128', 'Run experiments across acquisition and retention channels.', 'Gurugram, India', false, 'https://example.com/apply/swiggy-growth', array['Marketing', 'Communication'], '2026-09-10'),

    -- -------------------------------- programs -----------------------------
    ('programs', 'IBM Z Student Ambassador Program', 'IBM', 'https://www.google.com/s2/favicons?domain=ibm.com&sz=128', 'Represent IBM Z on campus, learn enterprise/mainframe tech, and lead workshops.', 'Remote', true, 'https://example.com/apply/ibmz-ambassador', array['Ambassador', 'Enterprise Tech', 'Leadership'], '2026-08-15'),
    ('programs', 'Microsoft Learn Student Ambassadors', 'Microsoft', 'https://www.google.com/s2/favicons?domain=microsoft.com&sz=128', 'Build technical communities on campus and get early access to Microsoft tech.', 'Remote', true, 'https://example.com/apply/mlsa', array['Ambassador', 'Community', 'Cloud'], '2026-09-30'),
    ('programs', 'Stanford Pre-Collegiate Summer Institutes', 'Stanford University', 'https://www.google.com/s2/favicons?domain=summer.stanford.edu&sz=128', 'Immersive summer program with college-level coursework across STEM and humanities.', 'Stanford, CA', false, 'https://example.com/apply/stanford-summer', array['Summer School', 'Academics'], '2026-05-01'),
    ('programs', 'Google Developer Student Clubs Lead', 'Google', 'https://www.google.com/s2/favicons?domain=developers.google.com&sz=128', 'Lead a campus chapter, run workshops, and build solutions for local communities.', 'Remote', true, 'https://example.com/apply/gdsc-lead', array['Ambassador', 'Community', 'Developer'], '2026-07-31'),
    ('programs', 'AWS Cloud Clubs Captain', 'Amazon Web Services', 'https://www.google.com/s2/favicons?domain=aws.amazon.com&sz=128', 'Run a student cloud community on campus with direct AWS mentorship and credits.', 'Remote', true, 'https://example.com/apply/aws-cloud-clubs', array['Ambassador', 'Cloud', 'Community'], '2026-08-10'),
    ('programs', 'NASA Space Apps Ambassador', 'NASA', 'https://www.google.com/s2/favicons?domain=spaceappschallenge.org&sz=128', 'Champion NASA''s global hackathon on your campus and mentor first-time participants.', 'Remote', true, 'https://example.com/apply/nasa-space-apps', array['Ambassador', 'Space', 'STEM'], '2026-06-15'),
    ('programs', 'Meta University', 'Meta', 'https://www.google.com/s2/favicons?domain=metacareers.com&sz=128', 'Immersive pre-internship program teaching engineering fundamentals to underrepresented students.', 'Menlo Park, CA', false, 'https://example.com/apply/meta-university', array['Engineering', 'Mentorship', 'Diversity'], '2026-03-15'),
    ('programs', 'Summer of Bitcoin', 'Summer of Bitcoin', 'https://www.google.com/s2/favicons?domain=summerofbitcoin.org&sz=128', 'Paid summer program pairing students with open-source Bitcoin projects and mentors.', 'Remote', true, 'https://example.com/apply/summer-of-bitcoin', array['Blockchain', 'Open Source', 'Mentorship'], '2026-02-28'),

    -- ------------------------------ hackathons -----------------------------
    ('hackathons', 'HackIndia 2026', 'Devfolio', 'https://www.google.com/s2/favicons?domain=devfolio.co&sz=128', '48-hour build sprint with tracks across AI, fintech, and climate tech.', 'Remote', true, 'https://example.com/apply/hackindia', array['Hackathon', 'Open Innovation'], '2026-09-05'),
    ('hackathons', 'Smart India Hackathon', 'Government of India', 'https://www.google.com/s2/favicons?domain=sih.gov.in&sz=128', 'National-level hackathon solving real problem statements from ministries and industry.', 'Pan India', false, 'https://example.com/apply/sih', array['Hackathon', 'Government', 'Social Impact'], '2026-08-25'),
    ('hackathons', 'ETHIndia', 'ETHIndia', 'https://www.google.com/s2/favicons?domain=ethindia.co&sz=128', 'India''s largest Web3 hackathon, building on Ethereum and beyond.', 'Bengaluru, India', false, 'https://example.com/apply/ethindia', array['Web3', 'Blockchain', 'Hackathon'], '2026-10-01'),

    -- ------------------------------ open source ----------------------------
    ('open-source', 'Google Summer of Code', 'Google', 'https://www.google.com/s2/favicons?domain=summerofcode.withgoogle.com&sz=128', 'Paid, mentored open-source contributions with organizations worldwide.', 'Remote', true, 'https://example.com/apply/gsoc', array['Open Source', 'Mentorship'], '2026-04-02'),
    ('open-source', 'Hacktoberfest', 'DigitalOcean', 'https://www.google.com/s2/favicons?domain=digitalocean.com&sz=128', 'Month-long celebration of open source — make quality pull requests, get rewarded.', 'Remote', true, 'https://example.com/apply/hacktoberfest', array['Open Source', 'Community'], '2026-10-31'),
    ('open-source', 'Outreachy', 'Outreachy', 'https://www.google.com/s2/favicons?domain=outreachy.org&sz=128', 'Paid remote internships in open source for people from underrepresented groups.', 'Remote', true, 'https://example.com/apply/outreachy', array['Open Source', 'Internship', 'Diversity'], '2026-09-20'),

    -- ------------------------------ communities ----------------------------
    ('communities', 'Women Who Code', 'Women Who Code', 'https://www.google.com/s2/favicons?domain=womenwhocode.com&sz=128', 'Global community helping women pursue and grow in technical careers.', 'Remote', true, 'https://example.com/apply/womenwhocode', array['Community', 'Networking', 'Women in Tech'], null),
    ('communities', 'GDG Community', 'Google Developer Groups', 'https://www.google.com/s2/favicons?domain=gdg.community.dev&sz=128', 'Local developer groups organizing talks, workshops, and study jams.', 'Remote', true, 'https://example.com/apply/gdg', array['Community', 'Developer'], null),
    ('communities', 'Product Hunt Makers', 'Product Hunt', 'https://www.google.com/s2/favicons?domain=producthunt.com&sz=128', 'Community of builders sharing and discovering new products.', 'Remote', true, 'https://example.com/apply/producthunt-makers', array['Community', 'Startups', 'Product'], null),

    -- -------------------------------- events -------------------------------
    ('events', 'TechCrunch Disrupt', 'TechCrunch', 'https://www.google.com/s2/favicons?domain=techcrunch.com&sz=128', 'Flagship startup conference with founders, investors, and product launches.', 'San Francisco, CA', false, 'https://example.com/apply/tc-disrupt', array['Conference', 'Startups'], '2026-10-14'),
    ('events', 'Google I/O', 'Google', 'https://www.google.com/s2/favicons?domain=io.google&sz=128', 'Annual developer conference with keynotes and hands-on sessions.', 'Mountain View, CA', false, 'https://example.com/apply/google-io', array['Conference', 'Developer'], '2026-05-19'),
    ('events', 'PyCon India', 'PyCon India', 'https://www.google.com/s2/favicons?domain=in.pycon.org&sz=128', 'India''s largest gathering of Python developers and enthusiasts.', 'Bengaluru, India', false, 'https://example.com/apply/pycon-india', array['Conference', 'Python'], '2026-09-27')
) as v(category, title, organization, logo_url, description, location, is_remote, apply_url, tags, application_deadline)
where not exists (
  select 1 from public.opportunities o
  where o.title = v.title and o.organization = v.organization
);
