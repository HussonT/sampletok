'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { createAuthenticatedClient } from '@/lib/api-client';
import { TOPUP_PACKAGES, TOPUP_DISCOUNTS, SUBSCRIPTION_TIERS } from '@/lib/constants';
import { Coins, Loader2, AlertCircle, ShoppingCart, ArrowRight, TrendingUp } from 'lucide-react';

interface CreditBalanceData {
  credits: number;
  has_subscription: boolean;
  subscription_tier: 'basic' | 'pro' | 'ultimate' | null;
  monthly_credits: number | null;
}

export default function TopUpPage() {
  const [loading, setLoading] = useState(true);
  const [purchasingPackage, setPurchasingPackage] = useState<string | null>(null);
  const [creditData, setCreditData] = useState<CreditBalanceData | null>(null);
  const { getToken } = useAuth();
  const router = useRouter();

  // Fetch user's credit balance and subscription status
  useEffect(() => {
    const fetchCreditData = async () => {
      try {
        const token = await getToken();
        if (!token) {
          router.push('/sign-in');
          return;
        }

        const api = createAuthenticatedClient(async () => token);
        const data = await api.get<CreditBalanceData>('/credits/balance');
        setCreditData(data);
      } catch (error) {
        console.error('Failed to fetch credit data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCreditData();
  }, [getToken, router]);

  const handlePurchase = async (packageType: string) => {
    setPurchasingPackage(packageType);

    try {
      const token = await getToken();
      if (!token) {
        router.push('/sign-in');
        return;
      }

      const api = createAuthenticatedClient(async () => token);

      // Create Stripe checkout session for top-up
      const response = await api.post<{ session_id: string; checkout_url: string }>(
        '/credits/top-up',
        {
          package: packageType,
        }
      );

      // Redirect to Stripe Checkout
      window.location.href = response.checkout_url;
    } catch (error) {
      console.error('Failed to create top-up checkout:', error);
      alert(
        error instanceof Error
          ? error.message
          : 'Failed to start checkout. Please try again.'
      );
      setPurchasingPackage(null);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Show subscription required message
  if (!creditData?.has_subscription) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <Card className="max-w-md p-8 text-center">
          <AlertCircle className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h2 className="text-2xl font-bold mb-2">Subscription Required</h2>
          <p className="text-muted-foreground mb-6">
            Top-up credits are only available for active subscribers. Please subscribe to a plan
            first.
          </p>
          <Button onClick={() => router.push('/pricing')} className="w-full">
            View Pricing Plans
          </Button>
        </Card>
      </div>
    );
  }

  const userTier = creditData.subscription_tier || 'basic';
  const discount = TOPUP_DISCOUNTS[userTier];
  const packages = [TOPUP_PACKAGES.SMALL, TOPUP_PACKAGES.MEDIUM, TOPUP_PACKAGES.LARGE];

  // Determine upgrade tier
  const getUpgradeTier = () => {
    if (userTier === 'basic') return SUBSCRIPTION_TIERS.PRO;
    if (userTier === 'pro') return SUBSCRIPTION_TIERS.ULTIMATE;
    return null; // Already on highest tier
  };

  const upgradeTier = getUpgradeTier();

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="container mx-auto px-6 py-8 max-w-5xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Purchase Top-Up Credits</h1>
          <p className="text-muted-foreground">
            Need more credits? Purchase additional credits as a one-time top-up.
          </p>
        </div>

        {/* Current Balance */}
        <Card className="p-6 mb-8 bg-gradient-to-br from-primary/10 to-primary/5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground mb-1">Current Balance</p>
              <div className="flex items-center gap-2">
                <Coins className="w-6 h-6 text-primary" />
                <span className="text-3xl font-bold">
                  {creditData.credits.toLocaleString()}
                </span>
                <span className="text-muted-foreground">credits</span>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm text-muted-foreground mb-1">Your Plan</p>
              <Badge variant="secondary" className="text-sm capitalize">
                {userTier} Plan
              </Badge>
              {discount > 0 && (
                <p className="text-xs text-primary mt-1">{discount}% top-up discount</p>
              )}
            </div>
          </div>
        </Card>

        {/* Upgrade Plan Section */}
        {upgradeTier && (
          <Card className="p-6 mb-8 border-primary/50 bg-gradient-to-br from-primary/5 to-primary/10">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp className="w-5 h-5 text-primary" />
                  <h3 className="text-xl font-bold">Want More Credits & Better Discounts?</h3>
                </div>
                <p className="text-sm text-muted-foreground mb-4">
                  Upgrade to {upgradeTier.name} and get more value from your subscription
                </p>
                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div className="flex items-start gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5" />
                    <div>
                      <p className="text-sm font-medium">
                        {upgradeTier.credits} credits/month
                      </p>
                      <p className="text-xs text-muted-foreground">
                        vs {SUBSCRIPTION_TIERS[userTier.toUpperCase() as keyof typeof SUBSCRIPTION_TIERS].credits} currently
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5" />
                    <div>
                      <p className="text-sm font-medium">
                        {TOPUP_DISCOUNTS[upgradeTier.tier]}% top-up discount
                      </p>
                      <p className="text-xs text-muted-foreground">
                        vs {discount}% currently
                      </p>
                    </div>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  Starting at ${(upgradeTier.price.monthly).toFixed(2)}/month
                </p>
              </div>
              <Button
                onClick={() => router.push('/pricing')}
                className="flex-shrink-0"
                variant="default"
              >
                Upgrade Plan
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </Card>
        )}

        {/* Top-Up Packages */}
        <div className="grid md:grid-cols-3 gap-6">
          {packages.map((pkg) => {
            const finalPrice = pkg.basePrice * (1 - discount / 100);
            const pricePerCredit = finalPrice / pkg.credits;
            const isPurchasing = purchasingPackage === pkg.package;
            const isPopular = 'popular' in pkg && pkg.popular;

            return (
              <Card
                key={pkg.package}
                className={`p-6 flex flex-col ${
                  isPopular ? 'border-primary shadow-md' : ''
                }`}
              >
                {/* Popular Badge */}
                {isPopular && (
                  <div className="mb-4">
                    <Badge className="bg-primary text-primary-foreground">Best Value</Badge>
                  </div>
                )}

                {/* Package Name */}
                <h3 className="text-xl font-bold mb-2">{pkg.name}</h3>
                <p className="text-sm text-muted-foreground mb-4">{pkg.description}</p>

                {/* Credits */}
                <div className="mb-4">
                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-bold">{pkg.credits}</span>
                    <span className="text-muted-foreground">credits</span>
                  </div>
                </div>

                {/* Price */}
                <div className="mb-6">
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-bold">${finalPrice.toFixed(2)}</span>
                    {discount > 0 && (
                      <span className="text-sm text-muted-foreground line-through">
                        ${pkg.basePrice.toFixed(2)}
                      </span>
                    )}
                  </div>
                  {discount > 0 && (
                    <p className="text-xs text-primary mt-1">{discount}% discount applied</p>
                  )}
                  <p className="text-xs text-muted-foreground mt-1">
                    ${pricePerCredit.toFixed(3)} per credit
                  </p>
                </div>

                {/* Purchase Button */}
                <Button
                  onClick={() => handlePurchase(pkg.package)}
                  disabled={isPurchasing}
                  className="w-full mt-auto"
                  variant={isPopular ? 'default' : 'outline'}
                >
                  {isPurchasing ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <ShoppingCart className="mr-2 h-4 w-4" />
                      Purchase
                    </>
                  )}
                </Button>
              </Card>
            );
          })}
        </div>

        {/* Information */}
        <div className="mt-8 p-4 bg-muted rounded-lg">
          <h4 className="font-semibold mb-2 text-sm">About Top-Up Credits</h4>
          <ul className="text-sm text-muted-foreground space-y-1">
            <li>• Top-up credits accumulate with your monthly subscription credits</li>
            <li>• Credits never expire while your subscription is active</li>
            <li>
              • {discount > 0 ? `You save ${discount}% as a ${userTier} subscriber` : 'Upgrade to Pro or Ultimate for top-up discounts'}
            </li>
            <li>• All credits are lost if you cancel your subscription</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
