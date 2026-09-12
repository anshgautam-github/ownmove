import { useState } from 'react';
import { motion } from 'framer-motion';

// Same alias pattern as AuthDialog.jsx/LearningJourney.jsx (see the comment
// there): this repo's eslint config has no eslint-plugin-react, so
// no-unused-vars can't see `motion` referenced via a dotted JSX tag.
const MotionDiv = motion.div;

// Reuses the same tinted Simple Icons CDN pipeline the Learning Hub's
// company checkpoints use (see CheckpointLogo in LearningJourney.jsx), but
// with a DIFFERENT set of companies -- several of the exact brands in
// src/data/learningJourney.js (Microsoft, AWS, Salesforce, Oracle, IBM)
// have been pulled from Simple Icons entirely (cdn.simpleicons.org 404s
// for all five, confirmed directly against the CDN), which is why an
// earlier version of this used to render broken-image "?" boxes for them.
// Every slug below has been verified (200, not just assumed) against
// cdn.simpleicons.org before being added; the onError handler in
// FloatingLogo is a second line of defense that hides a logo if the CDN
// ever drops another one, instead of showing a broken-image icon.
//
// Positions are hand-placed (percentages of the container) rather than
// randomized on every render, so the layout is stable across re-renders.
// This is shared between AuthBackgroundLogos (the login/signup/reset
// password dialog) and FounderTrustSection (the landing page's "Why we
// built OwnMove" section) rather than duplicated, so fixing a broken slug
// here fixes it everywhere it's used.
const LOGOS = [
  { slug: 'google', accent: '4285F4', top: '8%', left: '10%', size: 52, rotate: -8, duration: 9, delay: 0 },
  { slug: 'github', accent: '181717', top: '14%', left: '82%', size: 60, rotate: 10, duration: 11, delay: 1 },
  { slug: 'dropbox', accent: '0061FF', top: '68%', left: '88%', size: 46, rotate: -6, duration: 8, delay: 0.5 },
  { slug: 'nvidia', accent: '76B900', top: '80%', left: '8%', size: 50, rotate: 6, duration: 10, delay: 1.5 },
  { slug: 'figma', accent: 'F24E1E', top: '4%', left: '46%', size: 38, rotate: -4, duration: 12, delay: 2 },
  { slug: 'notion', accent: '000000', top: '42%', left: '3%', size: 44, rotate: 8, duration: 9.5, delay: 0.8 },
  { slug: 'spotify', accent: '1DB954', top: '30%', left: '94%', size: 42, rotate: -10, duration: 10.5, delay: 1.2 },
  { slug: 'cisco', accent: '1BA0D7', top: '90%', left: '42%', size: 48, rotate: 5, duration: 8.5, delay: 0.3 },
  { slug: 'intel', accent: '0071C5', top: '54%', left: '95%', size: 40, rotate: -5, duration: 11.5, delay: 1.8 },
  { slug: 'redhat', accent: 'EE0000', top: '10%', left: '95%', size: 36, rotate: 12, duration: 9, delay: 2.4 },
  { slug: 'cloudflare', accent: 'F38020', top: '93%', left: '76%', size: 44, rotate: -7, duration: 10, delay: 0.6 },
  { slug: 'mongodb', accent: '47A248', top: '60%', left: '1%', size: 38, rotate: 9, duration: 12.5, delay: 1.1 },
  { slug: 'databricks', accent: 'FF3621', top: '2%', left: '28%', size: 34, rotate: -9, duration: 9.8, delay: 2.1 },
  { slug: 'qualcomm', accent: '3253DC', top: '84%', left: '20%', size: 38, rotate: 4, duration: 11, delay: 0.2 },
  // Second wave -- doubling the density so the effect reads clearly instead
  // of as a handful of faint specks. Each of these was verified against
  // cdn.simpleicons.org the same way as the first 14 (see note above).
  { slug: 'netflix', accent: 'E50914', top: '22%', left: '5%', size: 34, rotate: 7, duration: 10.2, delay: 0.4 },
  { slug: 'meta', accent: '0866FF', top: '46%', left: '90%', size: 40, rotate: -6, duration: 9.2, delay: 1.6 },
  { slug: 'stripe', accent: '635BFF', top: '6%', left: '66%', size: 32, rotate: 5, duration: 11.8, delay: 0.9 },
  { slug: 'atlassian', accent: '0052CC', top: '74%', left: '62%', size: 30, rotate: -8, duration: 8.8, delay: 2.2 },
  { slug: 'apple', accent: '1a1a1a', top: '36%', left: '55%', size: 30, rotate: 9, duration: 10.6, delay: 1.4 },
  { slug: 'airbnb', accent: 'FF5A5F', top: '96%', left: '10%', size: 36, rotate: -5, duration: 9.6, delay: 0.2 },
  { slug: 'shopify', accent: '95BF47', top: '20%', left: '30%', size: 28, rotate: 8, duration: 12.4, delay: 1.9 },
  { slug: 'discord', accent: '5865F2', top: '62%', left: '30%', size: 34, rotate: -7, duration: 9, delay: 0.7 },
  { slug: 'youtube', accent: 'FF0000', top: '4%', left: '88%', size: 30, rotate: 6, duration: 11.2, delay: 2.6 },
  { slug: 'reddit', accent: 'FF4500', top: '88%', left: '90%', size: 32, rotate: -9, duration: 8.6, delay: 1.3 },
  { slug: 'whatsapp', accent: '25D366', top: '50%', left: '40%', size: 26, rotate: 4, duration: 10.8, delay: 0.5 },
  { slug: 'pinterest', accent: 'E60023', top: '96%', left: '55%', size: 28, rotate: -4, duration: 9.4, delay: 1.7 },
  { slug: 'samsung', accent: '1428A0', top: '26%', left: '70%', size: 30, rotate: 10, duration: 12, delay: 2.3 },
  { slug: 'asana', accent: 'F06A6A', top: '8%', left: '20%', size: 26, rotate: -6, duration: 10, delay: 0.1 },
];

function FloatingLogo({ logo, opacity }) {
  const [failed, setFailed] = useState(false);
  if (failed) return null;

  return (
    <MotionDiv
      className="absolute"
      style={{ top: logo.top, left: logo.left, width: logo.size, height: logo.size }}
      initial={{ opacity: 0 }}
      animate={{
        opacity,
        y: [0, -14, 0],
        rotate: [logo.rotate, logo.rotate + 6, logo.rotate],
      }}
      transition={{
        opacity: { duration: 0.6 },
        y: { duration: logo.duration, delay: logo.delay, repeat: Infinity, ease: 'easeInOut' },
        rotate: { duration: logo.duration, delay: logo.delay, repeat: Infinity, ease: 'easeInOut' },
      }}
    >
      <img
        src={`https://cdn.simpleicons.org/${logo.slug}/${logo.accent}`}
        alt=""
        className="h-full w-full"
        onError={() => setFailed(true)}
      />
    </MotionDiv>
  );
}

// Purely decorative, low-opacity company logo "cloud" that drifts gently.
// `pointer-events-none` so it never intercepts clicks, and every logo is
// `aria-hidden` since it carries no information.
//
// `position`: 'fixed' pins it to the viewport (for a full-screen overlay
// like the auth dialog); 'absolute' scopes it to the nearest positioned
// ancestor (for a normal in-page section like FounderTrustSection) -- the
// caller must itself be `position: relative` (and usually
// `overflow-hidden`, so drifting logos near the edges don't create
// horizontal scroll) for 'absolute' to size against the right box.
function FloatingCompanyLogos({ position = 'fixed', opacity = 0.16, className = '' }) {
  return (
    <div
      className={`pointer-events-none ${position} inset-0 overflow-hidden ${className}`}
      aria-hidden="true"
    >
      {LOGOS.map((logo) => (
        <FloatingLogo key={logo.slug} logo={logo} opacity={opacity} />
      ))}
    </div>
  );
}

export default FloatingCompanyLogos;
