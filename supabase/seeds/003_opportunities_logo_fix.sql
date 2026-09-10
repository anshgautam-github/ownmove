-- ---------------------------------------------------------------------------
-- Google's favicon endpoint (used throughout 001/002) 404s for three domains:
-- sih.gov.in, outreachy.org, kodewithklossy.com. Confirmed in the browser
-- console (t2/t3.gstatic.com/faviconV2 requests failing) and reproducible
-- from a plain fetch of the s2/favicons URL for each domain.
--
-- Switched those three rows to DuckDuckGo's icon service, which resolves
-- favicons for smaller/less common sites more reliably than Google's.
-- Safe to re-run.
-- ---------------------------------------------------------------------------

update public.opportunities
set logo_url = 'https://icons.duckduckgo.com/ip3/sih.gov.in.ico'
where title = 'Smart India Hackathon' and organization = 'Government of India';

update public.opportunities
set logo_url = 'https://icons.duckduckgo.com/ip3/outreachy.org.ico'
where title = 'Outreachy' and organization = 'Outreachy';

update public.opportunities
set logo_url = 'https://icons.duckduckgo.com/ip3/kodewithklossy.com.ico'
where title = 'Kode With Klossy' and organization = 'Kode With Klossy';
