import Link from "next/link";

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-card">
        <div className="container mx-auto px-4 py-6">
          <Link href="/" className="text-3xl font-bold hover:opacity-80 transition-opacity">
            Sampletok
          </Link>
        </div>
      </div>

      <div className="container mx-auto px-4 py-12 max-w-4xl">
        <h1 className="text-4xl font-bold mb-8">Privacy Policy</h1>

        <div className="prose prose-slate dark:prose-invert max-w-none">
          <p className="text-sm text-muted-foreground mb-8">
            Last Updated: November 18, 2024
          </p>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">1. Introduction</h2>
            <p className="mb-4">
              Welcome to Sampletok ("we," "our," or "us"). We are committed to protecting your privacy and ensuring you have a positive experience on our platform. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our service at sampletok.co (the "Service").
            </p>
            <p className="mb-4">
              By using our Service, you agree to the collection and use of information in accordance with this policy. If you do not agree with our policies and practices, please do not use our Service.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">2. Information We Collect</h2>

            <h3 className="text-xl font-semibold mb-3">2.1 Personal Information</h3>
            <p className="mb-4">We collect the following types of personal information:</p>
            <ul className="list-disc pl-6 mb-4 space-y-2">
              <li><strong>Account Information:</strong> When you create an account, we collect your email address, username, and authentication credentials through our third-party authentication provider (Clerk).</li>
              <li><strong>Profile Information:</strong> Any additional information you choose to provide in your profile.</li>
              <li><strong>Payment Information:</strong> When you make a purchase, payment information is processed by our third-party payment processor (Stripe). We do not store your full credit card details.</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3">2.2 Usage Information</h3>
            <p className="mb-4">We automatically collect certain information when you use our Service:</p>
            <ul className="list-disc pl-6 mb-4 space-y-2">
              <li><strong>Device Information:</strong> IP address, browser type, operating system, device identifiers, and mobile network information.</li>
              <li><strong>Log Data:</strong> Pages visited, time and date of visits, time spent on pages, and other diagnostic data.</li>
              <li><strong>Usage Data:</strong> Samples you download, create, favorite, or interact with; search queries; and feature usage patterns.</li>
              <li><strong>Behavioral Analytics:</strong> We track detailed interactions including: audio playback events (play, pause, seek, completion), sample swipes/dismissals (for feed personalization), download actions, favorite/unfavorite actions, collection creation/viewing, subscription events, credit purchases, stem separation requests, search queries, filter changes, button clicks, and navigation patterns.</li>
              <li><strong>Session Recording:</strong> We use PostHog for analytics which may include session replay recordings to understand user experience. All sensitive input fields (passwords, credit cards, etc.) are automatically masked. You can opt out of session recording in your browser settings.</li>
              <li><strong>Cookies and Tracking Technologies:</strong> We use cookies, web beacons, and similar technologies to track activity and store certain information. You can instruct your browser to refuse cookies or alert you when cookies are being sent.</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3">2.3 Content You Provide</h3>
            <ul className="list-disc pl-6 mb-4 space-y-2">
              <li><strong>TikTok URLs:</strong> URLs you submit for audio extraction and processing.</li>
              <li><strong>Instagram URLs:</strong> URLs you submit for audio extraction from Instagram Reels.</li>
              <li><strong>Collections:</strong> Playlists and collections you create.</li>
              <li><strong>Feedback and Communications:</strong> Information you provide when you contact us or provide feedback.</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">3. How We Use Your Information</h2>
            <p className="mb-4">We use the information we collect for the following purposes:</p>
            <ul className="list-disc pl-6 mb-4 space-y-2">
              <li><strong>Provide and Maintain the Service:</strong> To process TikTok videos, extract audio, generate waveforms, analyze BPM and musical key, and deliver processed samples to you.</li>
              <li><strong>Account Management:</strong> To create and manage your account, authenticate you, and provide customer support.</li>
              <li><strong>Payment Processing:</strong> To process transactions and manage subscriptions.</li>
              <li><strong>Personalization:</strong> To personalize your experience, recommend content, and remember your preferences.</li>
              <li><strong>Analytics and Improvements:</strong> To understand how users interact with our Service, identify trends, and improve our features and performance.</li>
              <li><strong>Communications:</strong> To send you service-related announcements, updates, security alerts, and support messages.</li>
              <li><strong>Marketing:</strong> With your consent, to send promotional communications about new features, products, or special offers. You can opt out at any time.</li>
              <li><strong>Legal Compliance:</strong> To comply with legal obligations, respond to legal requests, and protect our rights and the rights of others.</li>
              <li><strong>Fraud Prevention:</strong> To detect, prevent, and address fraud, security issues, and technical problems.</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">4. How We Share Your Information</h2>
            <p className="mb-4">We do not sell your personal information. We may share your information in the following circumstances:</p>

            <h3 className="text-xl font-semibold mb-3">4.1 Service Providers</h3>
            <p className="mb-4">We share information with third-party service providers who perform services on our behalf:</p>
            <ul className="list-disc pl-6 mb-4 space-y-2">
              <li><strong>Authentication:</strong> Clerk (user authentication and identity management)</li>
              <li><strong>Payment Processing:</strong> Stripe (payment and subscription management)</li>
              <li><strong>Cloud Hosting:</strong> Google Cloud Platform, Vercel (infrastructure and hosting)</li>
              <li><strong>Storage:</strong> Cloudflare R2, AWS S3, or Google Cloud Storage (file storage)</li>
              <li><strong>Background Jobs:</strong> Inngest (asynchronous task processing)</li>
              <li><strong>Content APIs:</strong> RapidAPI (TikTok and Instagram video metadata and download services)</li>
              <li><strong>Audio Processing:</strong> La La AI (stem separation services)</li>
              <li><strong>Analytics:</strong> PostHog (product analytics, event tracking, session recording)</li>
              <li><strong>Advertising:</strong> TikTok Pixel (conversion tracking and advertising attribution)</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3">4.2 Legal Requirements</h3>
            <p className="mb-4">We may disclose your information if required to do so by law or in response to valid requests by public authorities (e.g., court orders, subpoenas, or government agencies).</p>

            <h3 className="text-xl font-semibold mb-3">4.3 Business Transfers</h3>
            <p className="mb-4">If we are involved in a merger, acquisition, or sale of assets, your information may be transferred as part of that transaction. We will provide notice before your information becomes subject to a different privacy policy.</p>

            <h3 className="text-xl font-semibold mb-3">4.4 With Your Consent</h3>
            <p className="mb-4">We may share your information for any other purpose with your explicit consent.</p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">5. Data Retention</h2>
            <p className="mb-4">
              We retain your personal information for as long as necessary to provide the Service and fulfill the purposes outlined in this Privacy Policy. We will retain and use your information to the extent necessary to comply with our legal obligations, resolve disputes, and enforce our agreements.
            </p>
            <ul className="list-disc pl-6 mb-4 space-y-2">
              <li><strong>Account Information:</strong> Retained until you delete your account.</li>
              <li><strong>Usage Data:</strong> Typically retained for up to 2 years for analytics purposes.</li>
              <li><strong>Payment Records:</strong> Retained for tax and legal compliance (typically 7 years).</li>
              <li><strong>Audio Samples:</strong> Retained indefinitely unless you delete them or delete your account.</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">6. Your Rights and Choices</h2>
            <p className="mb-4">Depending on your location, you may have the following rights:</p>

            <h3 className="text-xl font-semibold mb-3">6.1 Access and Portability</h3>
            <p className="mb-4">You can access and download your personal information through your account settings or by contacting us.</p>

            <h3 className="text-xl font-semibold mb-3">6.2 Correction</h3>
            <p className="mb-4">You can update or correct your account information at any time through your account settings.</p>

            <h3 className="text-xl font-semibold mb-3">6.3 Deletion</h3>
            <p className="mb-4">You can request deletion of your account and personal information. Note that some information may be retained for legal or legitimate business purposes.</p>

            <h3 className="text-xl font-semibold mb-3">6.4 Opt-Out</h3>
            <ul className="list-disc pl-6 mb-4 space-y-2">
              <li><strong>Marketing Communications:</strong> You can unsubscribe from promotional emails using the unsubscribe link in each email.</li>
              <li><strong>Cookies:</strong> You can control cookies through your browser settings.</li>
              <li><strong>Analytics:</strong> You can opt out of certain analytics tracking.</li>
            </ul>

            <h3 className="text-xl font-semibold mb-3">6.5 Do Not Track</h3>
            <p className="mb-4">Some browsers have a "Do Not Track" feature. Our Service does not currently respond to Do Not Track signals.</p>

            <h3 className="text-xl font-semibold mb-3">6.6 California Privacy Rights</h3>
            <p className="mb-4">If you are a California resident, you have additional rights under the California Consumer Privacy Act (CCPA), including the right to know what personal information we collect, the right to delete your information, and the right to opt out of the sale of your information. We do not sell personal information.</p>

            <h3 className="text-xl font-semibold mb-3">6.7 European Privacy Rights (GDPR)</h3>
            <p className="mb-4">If you are located in the European Economic Area (EEA), UK, or Switzerland, you have rights under the General Data Protection Regulation (GDPR), including:</p>
            <ul className="list-disc pl-6 mb-4 space-y-2">
              <li>Right to access your personal data</li>
              <li>Right to rectification of inaccurate data</li>
              <li>Right to erasure ("right to be forgotten")</li>
              <li>Right to restrict processing</li>
              <li>Right to data portability</li>
              <li>Right to object to processing</li>
              <li>Right to withdraw consent</li>
              <li>Right to lodge a complaint with a supervisory authority</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">7. Security</h2>
            <p className="mb-4">
              We implement appropriate technical and organizational security measures to protect your information against unauthorized access, alteration, disclosure, or destruction. These measures include:
            </p>
            <ul className="list-disc pl-6 mb-4 space-y-2">
              <li>Encryption of data in transit using SSL/TLS</li>
              <li>Encryption of sensitive data at rest</li>
              <li>Regular security audits and monitoring</li>
              <li>Access controls and authentication</li>
              <li>Secure cloud infrastructure (Google Cloud Platform, Cloudflare)</li>
            </ul>
            <p className="mb-4">
              However, no method of transmission over the Internet or electronic storage is 100% secure. While we strive to use commercially acceptable means to protect your information, we cannot guarantee absolute security.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">8. Children's Privacy</h2>
            <p className="mb-4">
              Our Service is not intended for children under the age of 13 (or 16 in the EEA). We do not knowingly collect personal information from children under these ages. If you are a parent or guardian and believe your child has provided us with personal information, please contact us, and we will delete such information from our systems.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">9. International Data Transfers</h2>
            <p className="mb-4">
              Your information may be transferred to and processed in countries other than your country of residence. These countries may have data protection laws that are different from the laws of your country.
            </p>
            <p className="mb-4">
              We take steps to ensure that your information receives an adequate level of protection in the jurisdictions in which we process it. For transfers from the EEA, UK, or Switzerland, we rely on legal mechanisms such as Standard Contractual Clauses approved by the European Commission.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">10. Third-Party Links and Services</h2>
            <p className="mb-4">
              Our Service may contain links to third-party websites, services, or integrations (such as TikTok) that are not operated by us. We are not responsible for the privacy practices of these third parties. We encourage you to review the privacy policies of any third-party services you interact with.
            </p>
            <p className="mb-4">
              <strong>TikTok Integration:</strong> When you submit a TikTok URL, we use third-party APIs to retrieve publicly available content. We do not access your TikTok account or private TikTok data.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">11. Changes to This Privacy Policy</h2>
            <p className="mb-4">
              We may update this Privacy Policy from time to time to reflect changes in our practices, technology, legal requirements, or other factors. We will notify you of any material changes by:
            </p>
            <ul className="list-disc pl-6 mb-4 space-y-2">
              <li>Posting the updated policy on this page with a new "Last Updated" date</li>
              <li>Sending you an email notification (if you have provided an email address)</li>
              <li>Displaying a prominent notice on our Service</li>
            </ul>
            <p className="mb-4">
              Your continued use of the Service after any changes indicates your acceptance of the updated Privacy Policy.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">12. Contact Us</h2>
            <p className="mb-4">
              If you have any questions, concerns, or requests regarding this Privacy Policy or our privacy practices, please contact us:
            </p>
            <div className="bg-muted p-4 rounded-lg">
              <p className="mb-2"><strong>Email:</strong> privacy@sampletok.co</p>
              <p className="mb-2"><strong>Website:</strong> https://sampletok.co</p>
            </div>
            <p className="mt-4">
              We will respond to your inquiry within 30 days.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">13. Specific Platform Compliance</h2>

            <h3 className="text-xl font-semibold mb-3">13.1 Meta (Facebook/Instagram) Compliance</h3>
            <p className="mb-4">
              If you access our Service through Meta platforms, we comply with Meta's Platform Policy. We do not use Meta user data for purposes outside of providing our Service, and we do not transfer or sell Meta user data to data brokers or advertising networks.
            </p>

            <h3 className="text-xl font-semibold mb-3">13.2 Google API Services Compliance</h3>
            <p className="mb-4">
              Our use of information received from Google APIs adheres to the <a href="https://developers.google.com/terms/api-services-user-data-policy" className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">Google API Services User Data Policy</a>, including the Limited Use requirements. We only use Google user data to provide and improve our Service, and we do not transfer Google user data to third parties except as necessary to provide the Service or as required by law.
            </p>

            <h3 className="text-xl font-semibold mb-3">13.3 TikTok Data Usage and Pixel Tracking</h3>
            <p className="mb-4">
              We access publicly available TikTok content through third-party APIs. We do not require access to your TikTok account, and we do not collect or store your TikTok login credentials. The TikTok content we process (videos, metadata) is limited to what you explicitly submit via URL and what is publicly accessible.
            </p>
            <p className="mb-4">
              <strong>TikTok Pixel:</strong> We use TikTok Pixel (a tracking technology) for advertising attribution and conversion tracking. The TikTok Pixel collects information about your interactions with our Service, including:
            </p>
            <ul className="list-disc pl-6 mb-4 space-y-2">
              <li>Page views and content viewed (ViewContent events)</li>
              <li>Search queries performed (Search events)</li>
              <li>Visits to the pricing page (Lead events)</li>
              <li>Subscription checkout initiated (InitiateCheckout events)</li>
              <li>Successful subscription completion (Subscribe events)</li>
              <li>Button clicks and interactions (ClickButton events)</li>
            </ul>
            <p className="mb-4">
              This data is shared with TikTok for Ads to measure ad performance and optimize ad targeting. You can opt out of personalized advertising through your device settings or TikTok's privacy settings.
            </p>

            <h3 className="text-xl font-semibold mb-3">13.4 Instagram Data Usage</h3>
            <p className="mb-4">
              Similar to TikTok, we access publicly available Instagram Reels content through third-party APIs. We do not require access to your Instagram account, and we do not collect or store your Instagram login credentials. The Instagram content we process is limited to what you explicitly submit via URL and what is publicly accessible.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">14. Cookies and Tracking Technologies</h2>
            <p className="mb-4">We use the following types of cookies and tracking technologies:</p>

            <h3 className="text-xl font-semibold mb-3">14.1 Essential Cookies</h3>
            <p className="mb-4">Required for the Service to function properly (authentication, security, session management).</p>

            <h3 className="text-xl font-semibold mb-3">14.2 Analytics Cookies (PostHog)</h3>
            <p className="mb-4">We use PostHog (hosted in the EU at https://eu.posthog.com) for product analytics and session recording. PostHog collects:</p>
            <ul className="list-disc pl-6 mb-4 space-y-2">
              <li><strong>Event Data:</strong> Detailed user interactions (plays, downloads, searches, clicks, navigation)</li>
              <li><strong>Session Recordings:</strong> Visual recordings of user sessions to understand user experience and identify bugs. Sensitive fields (passwords, payment info) are automatically masked.</li>
              <li><strong>User Identification:</strong> We identify users with their Clerk ID, email, username, and account creation date to provide personalized analytics.</li>
              <li><strong>Performance Metrics:</strong> Page load times, audio buffering events, HLS streaming performance</li>
            </ul>
            <p className="mb-4">
              You can opt out of PostHog tracking by enabling "Do Not Track" in your browser, or by blocking PostHog's domain (eu.posthog.com) using browser extensions or privacy tools.
            </p>

            <h3 className="text-xl font-semibold mb-3">14.3 Advertising Cookies (TikTok Pixel)</h3>
            <p className="mb-4">
              TikTok Pixel tracks conversions and user behavior for advertising attribution. See section 13.3 for details on what events are tracked.
            </p>

            <h3 className="text-xl font-semibold mb-3">14.4 Preference Cookies</h3>
            <p className="mb-4">Remember your settings and preferences (theme, language, playback settings).</p>

            <h3 className="text-xl font-semibold mb-3">14.5 Managing Cookies</h3>
            <p className="mb-4">
              You can control and manage cookies through your browser settings. Note that disabling certain cookies may affect the functionality of our Service. To opt out of specific tracking:
            </p>
            <ul className="list-disc pl-6 mb-4 space-y-2">
              <li><strong>PostHog:</strong> Enable "Do Not Track" in your browser or use privacy extensions</li>
              <li><strong>TikTok Pixel:</strong> Adjust privacy settings in your TikTok app or device advertising settings</li>
              <li><strong>All Cookies:</strong> Configure your browser to block third-party cookies</li>
            </ul>
          </section>

          <div className="mt-12 pt-8 border-t border-border">
            <p className="text-sm text-muted-foreground">
              This Privacy Policy is designed to comply with GDPR (Europe), CCPA (California), and privacy requirements from Meta, Google, and other major platforms. By using Sampletok, you acknowledge that you have read and understood this Privacy Policy.
            </p>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t bg-card mt-12">
        <div className="container mx-auto px-4 py-8">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-muted-foreground">
            <p>&copy; {new Date().getFullYear()} Sampletok. All rights reserved.</p>
            <div className="flex gap-6">
              <Link href="/privacy" className="hover:text-foreground transition-colors">
                Privacy Policy
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
