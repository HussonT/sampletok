'use client';

import { useAuth } from '@clerk/nextjs';
import { Coins, TrendingUp } from 'lucide-react';
import Link from 'next/link';
import { useCredits } from '@/hooks/use-credits';

export function CreditBalance() {
  const { isSignedIn } = useAuth();
  const { creditData, isLoading } = useCredits();

  // Don't show anything if not signed in
  if (!isSignedIn || isLoading) {
    return null;
  }

  // Show error state but don't block UI
  if (!creditData) {
    return null;
  }

  // Determine color based on credit level
  const getColorClass = () => {
    if (!creditData.has_subscription) {
      return 'text-muted-foreground';
    }

    const credits = creditData.credits;
    const monthlyAllowance = creditData.monthly_credits || 100;

    // Green: > 50% of monthly allowance
    // Yellow: 10-50% of monthly allowance
    // Red: < 10% of monthly allowance

    const percentage = (credits / monthlyAllowance) * 100;

    if (percentage > 50) {
      return 'text-green-600 dark:text-green-400';
    } else if (percentage > 10) {
      return 'text-yellow-600 dark:text-yellow-400';
    } else {
      return 'text-red-600 dark:text-red-400';
    }
  };

  // Show upgrade prompt if no subscription
  if (!creditData.has_subscription) {
    return (
      <Link href="/pricing">
        <div className="mx-4 mb-3 p-3 rounded-lg bg-primary/10 hover:bg-primary/15 transition-colors cursor-pointer border border-primary/20">
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className="w-4 h-4 text-primary" />
            <span className="text-xs font-semibold text-primary">Subscribe to Get Credits</span>
          </div>
          <p className="text-xs text-muted-foreground">
            Start processing TikTok videos
          </p>
        </div>
      </Link>
    );
  }

  return (
    <Link href="/top-up">
      <div className="mx-4 mb-3 p-3 rounded-lg bg-sidebar-accent/30 hover:bg-sidebar-accent/50 transition-colors cursor-pointer">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <Coins className={`w-4 h-4 ${getColorClass()}`} />
            <span className="text-xs font-semibold text-sidebar-foreground">Credits</span>
          </div>
          <span className={`text-lg font-bold ${getColorClass()}`}>
            {creditData.credits.toLocaleString()}
          </span>
        </div>
        {creditData.subscription_tier && (
          <div className="flex items-center justify-between text-xs text-sidebar-foreground/60">
            <span className="capitalize">{creditData.subscription_tier} Plan</span>
            <span>{creditData.monthly_credits}/mo</span>
          </div>
        )}
      </div>
    </Link>
  );
}
