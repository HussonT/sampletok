'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { createAuthenticatedClient } from '@/lib/api-client';
import {
  SUBSCRIPTION_TIERS,
  BillingInterval,
  ANNUAL_DISCOUNT_PERCENT,
} from '@/lib/constants';
import { Check, Loader2, AlertCircle } from 'lucide-react';
import { analytics } from '@/lib/analytics';

interface CurrentSubscription {
  tier: 'basic' | 'pro' | 'ultimate';
  billing_interval: 'month' | 'year';
  is_active: boolean;
}

interface UpgradePreview {
  proration_amount_cents: number;
  new_price_cents: number;
  current_tier: string;
  new_tier: string;
  billing_interval: string;
  next_billing_date: string;
}

export default function PricingPage() {
  const [billingInterval, setBillingInterval] = useState<BillingInterval>('month');
  const [loadingTier, setLoadingTier] = useState<string | null>(null);
  const [currentSubscription, setCurrentSubscription] = useState<CurrentSubscription | null>(null);
  const [loadingSubscription, setLoadingSubscription] = useState(true);
  const [upgradePreview, setUpgradePreview] = useState<UpgradePreview | null>(null);
  const [showUpgradeDialog, setShowUpgradeDialog] = useState(false);
  const { getToken } = useAuth();
  const router = useRouter();

  // Typing effect state
  const words = ['best.', 'weirdest.', 'most viral.', 'funniest.', 'prettiest.', 'most heartfelt.', 'touching.', 'most creative.', 'boldest.'];
  const [displayText, setDisplayText] = useState('');
  const [wordIndex, setWordIndex] = useState(0);
  const [isDeleting, setIsDeleting] = useState(false);

  // Typing effect
  useEffect(() => {
    const currentWord = words[wordIndex];
    const typingSpeed = isDeleting ? 50 : 100;
    const pauseAfterComplete = 2000;
    const pauseAfterDelete = 500;

    const timer = setTimeout(() => {
      if (!isDeleting) {
        // Typing
        if (displayText.length < currentWord.length) {
          setDisplayText(currentWord.slice(0, displayText.length + 1));
        } else {
          // Pause then start deleting
          setTimeout(() => setIsDeleting(true), pauseAfterComplete);
        }
      } else {
        // Deleting
        if (displayText.length > 0) {
          setDisplayText(currentWord.slice(0, displayText.length - 1));
        } else {
          // Move to next word
          setIsDeleting(false);
          setWordIndex((prev) => (prev + 1) % words.length);
          setTimeout(() => {}, pauseAfterDelete);
        }
      }
    }, typingSpeed);

    return () => clearTimeout(timer);
  }, [displayText, isDeleting, wordIndex, words]);

  // Fetch current subscription on mount
  useEffect(() => {
    const fetchSubscription = async () => {
      try {
        const token = await getToken();
        if (!token) {
          setLoadingSubscription(false);
          return;
        }

        const api = createAuthenticatedClient(async () => token);
        const data = await api.get<CurrentSubscription>('/subscriptions/current');
        setCurrentSubscription(data);
      } catch (error) {
        // User may not have a subscription yet - that's okay
      } finally {
        setLoadingSubscription(false);
      }
    };

    fetchSubscription();

    // Track that user viewed the pricing page
    analytics.subscriptionViewed();
  }, [getToken]);

  const confirmUpgrade = async () => {
    if (!upgradePreview) return;

    setLoadingTier(upgradePreview.new_tier);
    setShowUpgradeDialog(false);

    try {
      const token = await getToken();
      if (!token) {
        router.push('/sign-in');
        return;
      }

      const api = createAuthenticatedClient(async () => token);

      // Perform the upgrade
      await api.post('/subscriptions/upgrade', {
        new_tier: upgradePreview.new_tier,
      });

      // Reload immediately to show updated subscription
      // The new "Your Current Plan" badge will make it clear
      window.location.reload();
    } catch (error) {
      console.error('Failed to upgrade subscription:', error);
      alert(
        error instanceof Error
          ? error.message
          : 'Failed to upgrade subscription. Please try again.'
      );
      setLoadingTier(null);
    }
  };

  const handleSubscribe = async (tier: string) => {
    setLoadingTier(tier);

    try {
      const token = await getToken();
      if (!token) {
        // Redirect to sign in if not authenticated
        router.push('/sign-in');
        return;
      }

      const api = createAuthenticatedClient(async () => token);

      // Check if user is upgrading/downgrading existing subscription
      if (currentSubscription && currentSubscription.is_active) {
        // Same tier - do nothing
        if (currentSubscription.tier === tier) {
          alert('You are already subscribed to this plan.');
          setLoadingTier(null);
          return;
        }

        // Fetch upgrade preview first
        const preview = await api.post<UpgradePreview>('/subscriptions/upgrade/preview', {
          new_tier: tier,
        });

        setUpgradePreview(preview);
        setShowUpgradeDialog(true);
        setLoadingTier(null);
      } else {
        // Create new subscription via Stripe checkout
        const response = await api.post<{ session_id: string; checkout_url: string }>(
          '/subscriptions/create-checkout',
          {
            tier,
            billing_interval: billingInterval,
          }
        );

        // Track subscription checkout started
        analytics.subscriptionStarted(tier);

        // Redirect to Stripe Checkout
        window.location.href = response.checkout_url;
      }
    } catch (error) {
      console.error('Failed to modify subscription:', error);
      alert(
        error instanceof Error
          ? error.message
          : 'Failed to process request. Please try again.'
      );
      setLoadingTier(null);
    }
  };

  const tiers = [SUBSCRIPTION_TIERS.BASIC, SUBSCRIPTION_TIERS.PRO, SUBSCRIPTION_TIERS.ULTIMATE];

  // Tier ranking for comparison
  const tierRank = { basic: 1, pro: 2, ultimate: 3 };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-card">
        <div className="container mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold">Sampletok</h1>
        </div>
      </div>

      {/* Pricing Content */}
      <div className="container mx-auto px-4 py-12">
        {/* Title and Description */}
        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold mb-4">Choose Your Plan</h2>
          <div className="text-lg max-w-2xl mx-auto">
            <p className="text-muted-foreground">
              Start making music at the speed of culture.
            </p>
            <p className="text-muted-foreground mt-2">
              Co-create with the{' '}
              <span className="text-foreground font-semibold">
                {displayText}
                <span className="animate-pulse">|</span>
              </span>
            </p>
          </div>
        </div>

        {/* Billing Toggle */}
        <div className="flex justify-center mb-12">
          <div className="inline-flex items-center bg-muted rounded-lg p-1">
            <button
              onClick={() => setBillingInterval('month')}
              className={`px-6 py-2 rounded-md font-medium transition-colors ${
                billingInterval === 'month'
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setBillingInterval('year')}
              className={`px-6 py-2 rounded-md font-medium transition-colors flex items-center gap-2 ${
                billingInterval === 'year'
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Annual
              <Badge variant="secondary" className="text-xs">
                Save {ANNUAL_DISCOUNT_PERCENT}%
              </Badge>
            </button>
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {tiers.map((tierConfig) => {
            const price = tierConfig.price[billingInterval === 'month' ? 'monthly' : 'annual'];
            const monthlyPrice =
              billingInterval === 'year' ? (price / 12).toFixed(2) : price.toFixed(2);
            const isLoading = loadingTier === tierConfig.tier;
            const isPopular = 'popular' in tierConfig && tierConfig.popular;
            const isCurrentPlan = currentSubscription?.tier === tierConfig.tier;
            const isUpgrade = currentSubscription && tierRank[currentSubscription.tier] < tierRank[tierConfig.tier as keyof typeof tierRank];
            const isDowngrade = currentSubscription && tierRank[currentSubscription.tier] > tierRank[tierConfig.tier as keyof typeof tierRank];

            // Determine button text
            let buttonText = 'Subscribe';
            if (isCurrentPlan) {
              buttonText = 'Current Plan';
            } else if (isUpgrade) {
              buttonText = 'Upgrade';
            } else if (isDowngrade) {
              buttonText = 'Downgrade';
            }

            return (
              <Card
                key={tierConfig.tier}
                className={`relative p-8 flex flex-col transition-all ${
                  isCurrentPlan
                    ? 'border-2 border-primary shadow-xl ring-2 ring-primary/20'
                    : isUpgrade
                    ? 'border-primary/50 hover:border-primary hover:shadow-lg'
                    : isDowngrade
                    ? 'opacity-60 hover:opacity-80'
                    : isPopular
                    ? 'border-primary shadow-lg scale-105'
                    : ''
                }`}
              >
                {/* Current Plan Badge */}
                {isCurrentPlan && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                    <Badge className="bg-primary text-primary-foreground px-4 py-1 shadow-md">
                      Your Current Plan
                    </Badge>
                  </div>
                )}

                {/* Popular Badge (only for new subscribers, not existing ones) */}
                {isPopular && !currentSubscription && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                    <Badge className="bg-primary text-primary-foreground px-4 py-1">
                      Most Popular
                    </Badge>
                  </div>
                )}

                {/* Tier Name with Upgrade/Downgrade Label */}
                <div className="mb-2">
                  <h3 className="text-2xl font-bold">{tierConfig.name}</h3>
                  {!isCurrentPlan && currentSubscription && (
                    <p className="text-xs text-muted-foreground mt-1">
                      {isUpgrade ? '↑ Upgrade from ' : isDowngrade ? '↓ Downgrade from ' : ''}
                      {currentSubscription.tier.charAt(0).toUpperCase() + currentSubscription.tier.slice(1)}
                    </p>
                  )}
                </div>

                {/* Price */}
                <div className="mb-6">
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-bold">${monthlyPrice}</span>
                    <span className="text-muted-foreground">/month</span>
                  </div>
                  {billingInterval === 'year' && (
                    <p className="text-sm text-muted-foreground mt-1">
                      Billed ${price.toFixed(2)} annually
                    </p>
                  )}
                </div>

                {/* Subscribe/Upgrade Button */}
                <Button
                  onClick={() => handleSubscribe(tierConfig.tier)}
                  disabled={isLoading || isCurrentPlan || loadingSubscription}
                  className="w-full mb-6"
                  variant={isPopular && !currentSubscription ? 'default' : 'outline'}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    buttonText
                  )}
                </Button>

                {/* Features List */}
                <ul className="space-y-3 flex-grow">
                  {tierConfig.features.map((feature, index) => (
                    <li key={index} className="flex items-start gap-3">
                      <Check className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
                      <span className="text-sm text-muted-foreground">{feature}</span>
                    </li>
                  ))}
                </ul>
              </Card>
            );
          })}
        </div>

        {/* Additional Info */}
        <div className="text-center mt-12 text-sm text-muted-foreground">
          <p>All plans include unlimited credit accumulation while subscribed.</p>
          <p className="mt-2">
            Need more credits? Purchase top-up packs with tier-based discounts.
          </p>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t bg-card mt-12">
        <div className="container mx-auto px-4 py-8">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-muted-foreground">
            <p>&copy; {new Date().getFullYear()} Sampletok. All rights reserved.</p>
            <div className="flex gap-6">
              <a href="/privacy" className="hover:text-foreground transition-colors">
                Privacy Policy
              </a>
              <a href="/pricing" className="hover:text-foreground transition-colors">
                Pricing
              </a>
            </div>
          </div>
        </div>
      </footer>

      {/* Upgrade Confirmation Dialog */}
      {showUpgradeDialog && upgradePreview && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="max-w-md w-full p-6">
            <div className="flex items-start gap-3 mb-4">
              <AlertCircle className="w-6 h-6 text-primary flex-shrink-0" />
              <div>
                <h3 className="text-lg font-bold mb-1">Confirm Plan Change</h3>
                <p className="text-sm text-muted-foreground">
                  Review the changes to your subscription
                </p>
              </div>
            </div>

            <div className="space-y-4 mb-6">
              {/* Current → New Plan */}
              <div>
                <p className="text-sm text-muted-foreground mb-1">Plan Change</p>
                <p className="font-medium">
                  {upgradePreview.current_tier.charAt(0).toUpperCase() + upgradePreview.current_tier.slice(1)} →{' '}
                  {upgradePreview.new_tier.charAt(0).toUpperCase() + upgradePreview.new_tier.slice(1)}
                </p>
              </div>

              {/* Charge Today */}
              <div className="p-4 bg-muted rounded-lg">
                <p className="text-sm text-muted-foreground mb-1">Charge today</p>
                <p className="text-2xl font-bold">
                  ${(upgradePreview.proration_amount_cents / 100).toFixed(2)}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Prorated difference charged to your card on file
                </p>
              </div>

              {/* New Recurring Price */}
              <div>
                <p className="text-sm text-muted-foreground mb-1">New recurring price</p>
                <p className="font-medium">
                  ${(upgradePreview.new_price_cents / 100).toFixed(2)}/
                  {upgradePreview.billing_interval === 'year' ? 'year' : 'month'}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Next billing: {new Date(upgradePreview.next_billing_date).toLocaleDateString()}
                </p>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <Button
                onClick={() => {
                  setShowUpgradeDialog(false);
                  setUpgradePreview(null);
                }}
                variant="outline"
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                onClick={confirmUpgrade}
                className="flex-1"
              >
                Confirm & Pay ${(upgradePreview.proration_amount_cents / 100).toFixed(2)}
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
