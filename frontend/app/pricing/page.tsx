'use client';

import { useState } from 'react';
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
import { Check, Loader2 } from 'lucide-react';

export default function PricingPage() {
  const [billingInterval, setBillingInterval] = useState<BillingInterval>('month');
  const [loadingTier, setLoadingTier] = useState<string | null>(null);
  const { getToken } = useAuth();
  const router = useRouter();

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

      // Create Stripe checkout session
      const response = await api.post<{ session_id: string; checkout_url: string }>(
        '/subscriptions/create-checkout',
        {
          tier,
          billing_interval: billingInterval,
        }
      );

      // Redirect to Stripe Checkout
      window.location.href = response.checkout_url;
    } catch (error) {
      console.error('Failed to create checkout session:', error);
      alert(
        error instanceof Error
          ? error.message
          : 'Failed to start checkout. Please try again.'
      );
      setLoadingTier(null);
    }
  };

  const tiers = [SUBSCRIPTION_TIERS.BASIC, SUBSCRIPTION_TIERS.PRO, SUBSCRIPTION_TIERS.ULTIMATE];

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
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            Extract high-quality audio samples from TikTok videos with professional-grade BPM
            and key detection. Subscribe to start processing.
          </p>
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

            return (
              <Card
                key={tierConfig.tier}
                className={`relative p-8 flex flex-col ${
                  isPopular ? 'border-primary shadow-lg scale-105' : ''
                }`}
              >
                {/* Popular Badge */}
                {isPopular && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                    <Badge className="bg-primary text-primary-foreground px-4 py-1">
                      Most Popular
                    </Badge>
                  </div>
                )}

                {/* Tier Name */}
                <h3 className="text-2xl font-bold mb-2">{tierConfig.name}</h3>

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

                {/* Subscribe Button */}
                <Button
                  onClick={() => handleSubscribe(tierConfig.tier)}
                  disabled={isLoading}
                  className="w-full mb-6"
                  variant={isPopular ? 'default' : 'outline'}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Loading...
                    </>
                  ) : (
                    'Subscribe'
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
    </div>
  );
}
