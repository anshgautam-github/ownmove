import FloatingCompanyLogos from '../shared/FloatingCompanyLogos';

// Thin wrapper kept around so AuthDialog.jsx's existing import doesn't need
// to change -- the actual logo list, verification notes, and animation
// live in the shared component (also used by the landing page's
// FounderTrustSection), so a broken CDN slug only needs fixing once.
function AuthBackgroundLogos() {
  return <FloatingCompanyLogos position="fixed" opacity={0.22} />;
}

export default AuthBackgroundLogos;
