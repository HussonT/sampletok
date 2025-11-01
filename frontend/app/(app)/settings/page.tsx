'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { createAuthenticatedClient } from '@/lib/api-client';
import {
  Settings,
  CreditCard,
  Receipt,
  Loader2,
  ExternalLink,
  AlertCircle,
  Sparkles,
} from 'lucide-react';

interface SubscriptionData {
  id: string;
  tier: string;
  billing_interval: string;
  monthly_credits: number;
  status: string;
  current_period_end: string;
  amount_cents: number;
  currency: string;
  cancel_at_period_end: boolean;
  is_active: boolean;
}

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [redirecting, setRedirecting] = useState(false);
  const [subscription, setSubscription] = useState<SubscriptionData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { getToken } = useAuth();
  const router = useRouter();

  // Fetch subscription data
  useEffect(() => {
    const fetchSubscription = async () => {
      try {
        const token = await getToken();
        if (!token) {
          router.push('/sign-in');
          return;
        }

        const api = createAuthenticatedClient(async () => token);
        const data = await api.get<SubscriptionData>('/subscriptions/current');
        setSubscription(data);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch subscription:', err);
        setError('No active subscription found');
      } finally {
        setLoading(false);
      }
    };

    fetchSubscription();
  }, [getToken, router]);

  const handleManageSubscription = async () => {
    setRedirecting(true);

    try {
      const token = await getToken();
      if (!token) {
        router.push('/sign-in');
        return;
      }

      const api = createAuthenticatedClient(async () => token);

      // Create Stripe Customer Portal session
      const response = await api.post<{ portal_url: string }>('/subscriptions/portal', {});

      // Redirect to Stripe Customer Portal
      window.location.href = response.portal_url;
    } catch (error) {
      console.error('Failed to create portal session:', error);
      alert(
        error instanceof Error
          ? error.message
          : 'Failed to open subscription management. Please try again.'
      );
      setRedirecting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // No subscription - show upgrade prompt
  if (error || !subscription) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <Card className="max-w-md p-8 text-center">
          <AlertCircle className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h2 className="text-2xl font-bold mb-2">No Active Subscription</h2>
          <p className="text-muted-foreground mb-6">
            Subscribe to a plan to start processing TikTok videos and extracting audio samples.
          </p>
          <Button onClick={() => router.push('/pricing')} className="w-full">
            View Pricing Plans
          </Button>
        </Card>
      </div>
    );
  }

  const periodEnd = new Date(subscription.current_period_end);
  const formattedDate = periodEnd.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="container mx-auto px-6 py-8 max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Settings</h1>
          <p className="text-muted-foreground">
            Manage your subscription, billing, and payment methods
          </p>
        </div>

        {/* Pricing Plans CTA */}
        <Card className="p-6 mb-6 bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold mb-1 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-primary" />
                Explore Other Plans
              </h2>
              <p className="text-sm text-muted-foreground">
                Compare plans and find the perfect fit for your needs
              </p>
            </div>
            <Button onClick={() => router.push('/pricing')} variant="outline" size="lg">
              View Pricing
            </Button>
          </div>
        </Card>

        {/* Current Subscription */}
        <Card className="p-6 mb-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-xl font-bold mb-1">Current Plan</h2>
              <p className="text-sm text-muted-foreground">
                Your active subscription details
              </p>
            </div>
            <Badge
              variant={subscription.is_active ? 'default' : 'secondary'}
              className="capitalize"
            >
              {subscription.status}
            </Badge>
          </div>

          <div className="space-y-4">
            {/* Tier */}
            <div className="flex justify-between items-center py-3 border-b">
              <span className="text-muted-foreground">Plan</span>
              <span className="font-semibold capitalize">
                {subscription.tier} ({subscription.billing_interval}ly)
              </span>
            </div>

            {/* Credits */}
            <div className="flex justify-between items-center py-3 border-b">
              <span className="text-muted-foreground">Monthly Credits</span>
              <span className="font-semibold">{subscription.monthly_credits} credits</span>
            </div>

            {/* Price */}
            <div className="flex justify-between items-center py-3 border-b">
              <span className="text-muted-foreground">Price</span>
              <span className="font-semibold">
                ${(subscription.amount_cents / 100).toFixed(2)} /{' '}
                {subscription.billing_interval === 'month' ? 'month' : 'year'}
              </span>
            </div>

            {/* Next Billing Date */}
            <div className="flex justify-between items-center py-3">
              <span className="text-muted-foreground">
                {subscription.cancel_at_period_end ? 'Ends on' : 'Next billing date'}
              </span>
              <span className="font-semibold">{formattedDate}</span>
            </div>

            {/* Cancellation Notice */}
            {subscription.cancel_at_period_end && (
              <div className="bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
                <p className="text-sm text-amber-900 dark:text-amber-100">
                  Your subscription will be cancelled on {formattedDate}. You&apos;ll lose access
                  to all credits after this date.
                </p>
              </div>
            )}
          </div>
        </Card>

        {/* Manage Subscription Button */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Subscription Management</h3>
          <p className="text-sm text-muted-foreground mb-6">
            Use Stripe&apos;s secure portal to manage your subscription, update payment methods, view
            invoices, and more.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="flex items-start gap-3 p-4 bg-muted rounded-lg">
              <CreditCard className="w-5 h-5 text-primary mt-0.5" />
              <div>
                <h4 className="text-sm font-semibold mb-1">Payment Method</h4>
                <p className="text-xs text-muted-foreground">
                  Update card or billing details
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-4 bg-muted rounded-lg">
              <Receipt className="w-5 h-5 text-primary mt-0.5" />
              <div>
                <h4 className="text-sm font-semibold mb-1">Billing History</h4>
                <p className="text-xs text-muted-foreground">View and download invoices</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-4 bg-muted rounded-lg">
              <Settings className="w-5 h-5 text-primary mt-0.5" />
              <div>
                <h4 className="text-sm font-semibold mb-1">Plan Changes</h4>
                <p className="text-xs text-muted-foreground">Upgrade, downgrade, or cancel</p>
              </div>
            </div>
          </div>

          <Button
            onClick={handleManageSubscription}
            disabled={redirecting}
            className="w-full"
            size="lg"
          >
            {redirecting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Opening Portal...
              </>
            ) : (
              <>
                <ExternalLink className="mr-2 h-4 w-4" />
                Manage Subscription in Stripe
              </>
            )}
          </Button>

          <p className="text-xs text-muted-foreground text-center mt-4">
            You&apos;ll be securely redirected to Stripe&apos;s billing portal
          </p>
        </Card>
      </div>
    </div>
  );
}
