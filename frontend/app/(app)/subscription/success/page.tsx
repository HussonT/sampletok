'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import { Card } from '@/components/ui/card';
import { CheckCircle, Loader2, Coins, Sparkles } from 'lucide-react';
import { createAuthenticatedClient } from '@/lib/api-client';
import confetti from 'canvas-confetti';

interface CreditBalanceData {
  credits: number;
  has_subscription: boolean;
  subscription_tier: string | null;
  monthly_credits: number | null;
}

interface TransactionData {
  id: string;
  credits_amount: number;
  previous_balance: number;
  new_balance: number;
  transaction_type: string;
  description: string;
}

export default function SubscriptionSuccessPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { getToken } = useAuth();
  const [loading, setLoading] = useState(true);
  const [creditData, setCreditData] = useState<CreditBalanceData | null>(null);
  const [transactionData, setTransactionData] = useState<TransactionData | null>(null);
  const [countdown, setCountdown] = useState(5);

  // Trigger confetti animation
  useEffect(() => {
    // Initial burst
    const duration = 3000;
    const animationEnd = Date.now() + duration;
    const defaults = { startVelocity: 30, spread: 360, ticks: 60, zIndex: 9999 };

    function randomInRange(min: number, max: number) {
      return Math.random() * (max - min) + min;
    }

    const interval: any = setInterval(function() {
      const timeLeft = animationEnd - Date.now();

      if (timeLeft <= 0) {
        return clearInterval(interval);
      }

      const particleCount = 50 * (timeLeft / duration);

      // Confetti from left side
      confetti({
        ...defaults,
        particleCount,
        origin: { x: randomInRange(0.1, 0.3), y: Math.random() - 0.2 }
      });

      // Confetti from right side
      confetti({
        ...defaults,
        particleCount,
        origin: { x: randomInRange(0.7, 0.9), y: Math.random() - 0.2 }
      });
    }, 250);

    return () => clearInterval(interval);
  }, []);

  // Fetch credit balance and transaction details
  useEffect(() => {
    const fetchData = async () => {
      try {
        const token = await getToken();
        if (!token) {
          setLoading(false);
          return;
        }

        const sessionId = searchParams.get('session_id');
        const api = createAuthenticatedClient(async () => token);

        // Fetch current credit balance
        const balanceData = await api.get<CreditBalanceData>('/credits/balance');
        setCreditData(balanceData);

        // If session_id is present, try to fetch transaction details
        if (sessionId) {
          try {
            const txData = await api.get<TransactionData>(`/credits/transaction/session/${sessionId}`);
            setTransactionData(txData);
          } catch (err) {
            console.error('Failed to fetch transaction details:', err);
            // Not critical - we can still show the balance
          }
        }
      } catch (err) {
        console.error('Failed to fetch credit data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [getToken, searchParams]);

  // Countdown timer
  useEffect(() => {
    if (loading) return;

    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [loading]);

  // Handle redirect when countdown reaches 0
  useEffect(() => {
    if (countdown === 0 && !loading) {
      router.push('/');
    }
  }, [countdown, loading, router]);

  const sessionId = searchParams.get('session_id');

  return (
    <div className="flex-1 flex items-center justify-center p-8 bg-gradient-to-br from-primary/5 via-background to-background">
      <Card className="max-w-lg w-full p-8 text-center shadow-2xl border-2 border-primary/20">
        {/* Success Icon */}
        <div className="relative inline-flex items-center justify-center mb-6">
          <div className="absolute inset-0 bg-green-500/20 rounded-full blur-xl animate-pulse"></div>
          <CheckCircle className="w-20 h-20 text-green-500 relative z-10" />
        </div>

        {/* Heading */}
        <h1 className="text-3xl font-bold mb-3 flex items-center justify-center gap-2">
          <Sparkles className="w-6 h-6 text-primary" />
          Subscription Active!
          <Sparkles className="w-6 h-6 text-primary" />
        </h1>

        <p className="text-muted-foreground mb-8">
          Your payment was successful and your credits are ready to use.
        </p>

        {/* Credit Balance */}
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-6">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            <span className="text-sm text-muted-foreground">Loading your credits...</span>
          </div>
        ) : creditData ? (
          <div className="bg-gradient-to-br from-primary/10 to-primary/5 rounded-lg p-6 mb-6 border border-primary/20">
            <div className="flex items-center justify-center gap-3 mb-2">
              <Coins className="w-8 h-8 text-primary" />
              <div className="flex items-baseline gap-2">
                <span className="text-5xl font-bold text-primary">
                  {creditData.credits.toLocaleString()}
                </span>
                {transactionData && transactionData.credits_amount > 0 && (
                  <span className="text-2xl font-semibold text-green-500">
                    (+{transactionData.credits_amount.toLocaleString()})
                  </span>
                )}
              </div>
            </div>
            <p className="text-sm font-semibold text-muted-foreground">
              {creditData.subscription_tier && (
                <span className="capitalize">{creditData.subscription_tier} Plan</span>
              )}
              {creditData.monthly_credits && (
                <span> • {creditData.monthly_credits} credits/month</span>
              )}
            </p>
            {transactionData && (
              <p className="text-xs text-muted-foreground mt-2">
                {transactionData.description}
              </p>
            )}
          </div>
        ) : (
          <div className="py-6 text-sm text-muted-foreground">
            Credits available! Check your account for details.
          </div>
        )}

        {/* Session ID (for reference) */}
        {sessionId && (
          <div className="mb-6 p-3 bg-muted rounded text-xs font-mono text-muted-foreground break-all">
            Session: {sessionId}
          </div>
        )}

        {/* Redirect Countdown */}
        <div className="text-sm text-muted-foreground">
          Redirecting to home in {countdown} second{countdown !== 1 ? 's' : ''}...
        </div>

        {/* Manual redirect button */}
        <button
          onClick={() => router.push('/')}
          className="mt-4 text-sm text-primary hover:underline"
        >
          Go to Home Now →
        </button>
      </Card>
    </div>
  );
}
