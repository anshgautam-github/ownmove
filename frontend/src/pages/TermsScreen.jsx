import React from 'react';

// Plain, standalone route (not a modal) so the "Terms & Conditions" link in
// AuthDialog can open it in a new tab via a real URL instead of trying to
// stack another overlay on top of the auth dialog's own portal.
//
// NOTE: this is starter/template legal copy written to unblock the product
// (the auth flow linked to a Terms page that didn't exist), not legal
// advice. Have an actual lawyer review and tailor it -- especially the
// governing-law, data-handling, and liability sections -- before relying on
// it for a real launch.
const LAST_UPDATED = 'September 2026';

function Section({ title, children }) {
  return (
    <section className="mt-8 first:mt-0">
      <h2 className="text-lg font-semibold tracking-tight text-black">{title}</h2>
      <div className="mt-2 space-y-3 text-sm leading-6 text-[#4B5563]">{children}</div>
    </section>
  );
}

function TermsScreen() {
  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#fffdf9_0%,#fff8f2_42%,#f8f6ff_100%)] px-4 py-10 text-[#131114] sm:px-8">
      <div className="mx-auto max-w-[720px]">
        <div className="mb-8 flex items-center justify-between">
          <a
            href="/"
            className="inline-flex items-center rounded-full border border-[#111827]/18 bg-white/55 px-6 py-3 text-lg font-medium tracking-tight text-black shadow-[0_10px_24px_rgba(17,24,39,0.04)]"
          >
            OwnMove
          </a>
          <a href="/" className="text-sm font-medium text-black underline underline-offset-2">
            Back
          </a>
        </div>

        <div className="rounded-[28px] border border-[#111827]/10 bg-white/70 px-5 py-7 shadow-[0_24px_70px_rgba(96,86,176,0.08)] backdrop-blur-md sm:px-10 sm:py-10">
          <h1 className="text-[2rem] font-medium leading-none tracking-tight text-black">Terms & Conditions</h1>
          <p className="mt-3 text-xs font-medium uppercase tracking-wide text-[#8b929d]">Last updated: {LAST_UPDATED}</p>

          <p className="mt-6 text-sm leading-6 text-[#4B5563]">
            These Terms & Conditions ("Terms") govern access to and use of OwnMove (the "Service"). By creating an
            account, signing in, or otherwise using the Service, you agree to be bound by these Terms. If you do not
            agree, please do not use the Service.
          </p>

          <Section title="1. Eligibility">
            <p>
              You must be able to form a binding contract to use the Service. If you're using OwnMove on behalf of
              yourself as an individual, you confirm you meet any minimum age required by the laws of your
              jurisdiction to do so.
            </p>
          </Section>

          <Section title="2. Your Account">
            <p>
              You can create an account with an email and password, or by signing in with Google. You're responsible
              for keeping your login credentials confidential and for all activity that happens under your account.
              Tell us right away if you suspect unauthorized access.
            </p>
            <p>
              You agree to provide accurate information when you register and to keep it up to date. We may suspend
              or terminate accounts that provide false information or that we reasonably believe are being used
              fraudulently or abusively.
            </p>
          </Section>

          <Section title="3. What You Can Use OwnMove For">
            <p>
              OwnMove helps you build a profile, discover opportunities, track applications, and get AI-assisted
              career guidance and analysis. The Service is provided to help with your own career and job search — not
              for scraping, reselling, or redistributing opportunity listings or other users' data.
            </p>
          </Section>

          <Section title="4. Your Content">
            <p>
              You may upload information to your profile, including your resume, work experience, and other career
              details ("Your Content"). You retain ownership of Your Content. By uploading it, you grant OwnMove a
              limited license to store, process, and display it back to you, and to use it to power features you use
              (like recommendations, AI coaching, and profile analysis).
            </p>
            <p>
              You're responsible for Your Content and for having the right to share it. Don't upload anything that
              infringes someone else's rights, that you don't have permission to share, or that's unlawful.
            </p>
          </Section>

          <Section title="5. AI-Assisted Features">
            <p>
              Some features (such as career coaching, profile analysis, and career simulations) use AI models to
              generate suggestions, summaries, or guidance based on the information you provide. These outputs are
              informational and may be incomplete or inaccurate — they are not professional, legal, financial, or
              career advice, and you should use your own judgment before relying on them for major decisions.
            </p>
          </Section>

          <Section title="6. Third-Party Sign-In & Services">
            <p>
              Signing in with Google is handled by Google and our authentication provider (Supabase). We receive the
              account information those services choose to share with us (such as your name and email) in order to
              create and manage your account. Your use of any third-party sign-in is also subject to that provider's
              own terms.
            </p>
          </Section>

          <Section title="7. Acceptable Use">
            <p>You agree not to:</p>
            <p>
              Attempt to gain unauthorized access to the Service or other users' accounts; interfere with or disrupt
              the Service's infrastructure; use automated tools to scrape data beyond your own account; upload
              malicious code; or use the Service to harass, impersonate, or harm others.
            </p>
          </Section>

          <Section title="8. Intellectual Property">
            <p>
              The Service, including its design, branding, and underlying software, is owned by OwnMove or its
              licensors and is protected by applicable intellectual property laws. These Terms don't grant you any
              rights to OwnMove's trademarks, logos, or branding.
            </p>
          </Section>

          <Section title="9. Privacy">
            <p>
              How we collect, use, and store your information is described in our Privacy Policy. By using the
              Service, you consent to that handling of your data.
            </p>
          </Section>

          <Section title="10. Disclaimers">
            <p>
              The Service is provided "as is" and "as available," without warranties of any kind, whether express or
              implied. We don't guarantee that the Service will be uninterrupted, error-free, or that any
              opportunity, recommendation, or AI-generated output will lead to any particular outcome, including
              employment.
            </p>
          </Section>

          <Section title="11. Limitation of Liability">
            <p>
              To the fullest extent permitted by law, OwnMove and its team will not be liable for any indirect,
              incidental, special, consequential, or punitive damages, or any loss of data, opportunities, or
              earnings, arising from your use of the Service.
            </p>
          </Section>

          <Section title="12. Termination">
            <p>
              You may stop using the Service and request account deletion at any time. We may suspend or terminate
              your access if you violate these Terms or if we discontinue the Service.
            </p>
          </Section>

          <Section title="13. Changes to These Terms">
            <p>
              We may update these Terms from time to time. If we make material changes, we'll take reasonable steps
              to let you know (for example, by updating the "Last updated" date above). Continuing to use the Service
              after changes take effect means you accept the updated Terms.
            </p>
          </Section>

          <Section title="14. Contact">
            <p>
              Questions about these Terms? Reach out to us through the contact details provided within the app.
            </p>
          </Section>
        </div>
      </div>
    </main>
  );
}

export default TermsScreen;
