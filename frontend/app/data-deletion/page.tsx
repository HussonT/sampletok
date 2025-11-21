import Link from "next/link";

export default function DataDeletionPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-card">
        <div className="container mx-auto px-4 py-6">
          <Link href="/" className="text-3xl font-bold hover:opacity-80 transition-opacity">
            Sample the Internet
          </Link>
        </div>
      </div>

      <div className="container mx-auto px-4 py-12 max-w-4xl">
        <h1 className="text-4xl font-bold mb-8">User Data Deletion Instructions</h1>

        <div className="prose prose-slate dark:prose-invert max-w-none">
          <p className="text-sm text-muted-foreground mb-8">
            Last Updated: November 18, 2024
          </p>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Overview</h2>
            <p className="mb-4">
              At Sample the Internet, we respect your right to control your personal data. This page provides instructions on how to request deletion of your data from our platform.
            </p>
            <p className="mb-4">
              When you request data deletion, we will remove all personal information associated with your account, including:
            </p>
            <ul className="list-disc pl-6 mb-4 space-y-2">
              <li>Account information (email, username, profile data)</li>
              <li>Audio samples you created or uploaded</li>
              <li>Collections and playlists</li>
              <li>Download history and favorites</li>
              <li>Usage analytics and behavioral data</li>
              <li>Payment history (subject to legal retention requirements)</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">How to Request Data Deletion</h2>

            <p className="mb-4">
              To request deletion of your data, please send an email to:
            </p>
            <div className="bg-muted p-4 rounded-lg mb-4">
              <p className="mb-2"><strong>Email:</strong> privacy@sampletok.co</p>
              <p className="mb-2"><strong>Subject:</strong> Data Deletion Request</p>
            </div>
            <p className="mb-4">
              Please include the following information in your email:
            </p>
            <ul className="list-disc pl-6 mb-4 space-y-2">
              <li>Your full name</li>
              <li>Email address associated with your Sample the Internet account</li>
              <li>Username (if applicable)</li>
              <li>A clear statement requesting deletion of your data</li>
            </ul>
            <p className="mb-4">
              We will verify your identity and process your request within 30 days of receipt.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">What Happens After You Request Deletion</h2>
            <p className="mb-4">Once we receive your data deletion request:</p>
            <ol className="list-decimal pl-6 mb-4 space-y-3">
              <li>
                <strong>Verification (1-3 business days):</strong> We will verify your identity to ensure the request is legitimate.
              </li>
              <li>
                <strong>Account Deactivation (Immediate):</strong> Your account will be immediately deactivated, and you will no longer be able to log in.
              </li>
              <li>
                <strong>Data Deletion (Within 30 days):</strong> We will permanently delete:
                <ul className="list-disc pl-6 mt-2 space-y-1">
                  <li>Your account information and profile data</li>
                  <li>Audio samples, waveforms, and associated files</li>
                  <li>Collections, playlists, and favorites</li>
                  <li>Usage history and analytics data</li>
                  <li>Session recordings and behavioral tracking data</li>
                </ul>
              </li>
              <li>
                <strong>Confirmation (Within 30 days):</strong> We will send you an email confirmation once the deletion process is complete.
              </li>
            </ol>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Data Retention Exceptions</h2>
            <p className="mb-4">
              Some data may be retained for legal, tax, or security purposes, including:
            </p>
            <ul className="list-disc pl-6 mb-4 space-y-2">
              <li>
                <strong>Transaction Records:</strong> Payment and subscription history may be retained for up to 7 years to comply with tax and financial regulations.
              </li>
              <li>
                <strong>Legal Obligations:</strong> Data required by law to be retained (e.g., for fraud prevention, legal disputes, or regulatory compliance).
              </li>
              <li>
                <strong>Backups:</strong> Deleted data may persist in backup systems for up to 90 days before permanent removal.
              </li>
              <li>
                <strong>Aggregated Analytics:</strong> Anonymized and aggregated data used for analytics may be retained indefinitely, as it cannot be linked back to you.
              </li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Third-Party Data Deletion</h2>
            <p className="mb-4">
              Sample the Internet uses third-party services that may have received your data. When you request data deletion from Sample the Internet, we will also notify the following services to delete your data:
            </p>
            <ul className="list-disc pl-6 mb-4 space-y-2">
              <li>
                <strong>Clerk (Authentication):</strong> Your authentication data will be deleted from Clerk's systems. You can also request deletion directly from Clerk at <a href="https://clerk.com/legal/privacy" className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">https://clerk.com/legal/privacy</a>
              </li>
              <li>
                <strong>Stripe (Payment Processing):</strong> Payment data will be deleted subject to Stripe's data retention policies. Learn more at <a href="https://stripe.com/privacy" className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">https://stripe.com/privacy</a>
              </li>
              <li>
                <strong>PostHog (Analytics):</strong> Your analytics and session recording data will be deleted from PostHog. You can also request deletion directly at <a href="https://posthog.com/privacy" className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">https://posthog.com/privacy</a>
              </li>
              <li>
                <strong>TikTok Pixel:</strong> TikTok advertising data will be deleted subject to TikTok's policies. You can manage your TikTok privacy settings at <a href="https://www.tiktok.com/legal/privacy-policy" className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">https://www.tiktok.com/legal/privacy-policy</a>
              </li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Withdrawing Consent</h2>
            <p className="mb-4">
              If you want to withdraw consent for specific data processing activities without deleting your entire account, you can:
            </p>
            <ul className="list-disc pl-6 mb-4 space-y-2">
              <li>Opt out of marketing communications via the unsubscribe link in emails</li>
              <li>Disable cookies and tracking in your browser settings</li>
              <li>Opt out of analytics tracking by enabling "Do Not Track" in your browser</li>
              <li>Adjust advertising preferences in your TikTok account settings</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Questions or Concerns</h2>
            <p className="mb-4">
              If you have any questions about the data deletion process or need assistance, please contact us:
            </p>
            <div className="bg-muted p-4 rounded-lg">
              <p className="mb-2"><strong>Email:</strong> privacy@sampletok.co</p>
              <p className="mb-2"><strong>Website:</strong> <a href="https://sampletok.co" className="text-primary hover:underline">https://sampletok.co</a></p>
            </div>
            <p className="mt-4">
              We are committed to protecting your privacy and will respond to your inquiry within 30 days.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Your Rights Under Privacy Laws</h2>
            <p className="mb-4">
              Depending on your location, you have the following rights under privacy laws such as GDPR (Europe), CCPA (California), and others:
            </p>
            <ul className="list-disc pl-6 mb-4 space-y-2">
              <li><strong>Right to Access:</strong> Request a copy of your personal data</li>
              <li><strong>Right to Rectification:</strong> Request correction of inaccurate data</li>
              <li><strong>Right to Erasure:</strong> Request deletion of your data ("right to be forgotten")</li>
              <li><strong>Right to Restriction:</strong> Request limitation of data processing</li>
              <li><strong>Right to Data Portability:</strong> Request your data in a portable format</li>
              <li><strong>Right to Object:</strong> Object to certain types of data processing</li>
              <li><strong>Right to Withdraw Consent:</strong> Withdraw consent for data processing at any time</li>
            </ul>
            <p className="mb-4">
              To exercise any of these rights, please contact us at privacy@sampletok.co.
            </p>
          </section>

          <div className="mt-12 pt-8 border-t border-border">
            <p className="text-sm text-muted-foreground">
              This Data Deletion Instructions page complies with requirements from Meta (Facebook/Instagram), Google, TikTok, and other platforms. For our full Privacy Policy, please visit <Link href="/privacy" className="text-primary hover:underline">/privacy</Link>.
            </p>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t bg-card mt-12">
        <div className="container mx-auto px-4 py-8">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-muted-foreground">
            <p>&copy; {new Date().getFullYear()} Sample the Internet. All rights reserved.</p>
            <div className="flex gap-6">
              <Link href="/privacy" className="hover:text-foreground transition-colors">
                Privacy Policy
              </Link>
              <Link href="/data-deletion" className="hover:text-foreground transition-colors">
                Data Deletion
              </Link>
              <Link href="/pricing" className="hover:text-foreground transition-colors">
                Pricing
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
