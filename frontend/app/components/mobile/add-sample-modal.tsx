'use client';

import { useState, useEffect, useCallback } from 'react';
import { X, Link as LinkIcon, Loader2, CheckCircle, AlertCircle, Sparkles, Coins } from 'lucide-react';
import { useAuth } from '@clerk/nextjs';
import { createAuthenticatedClient } from '@/lib/api-client';
import { useHapticFeedback } from '@/hooks/use-haptics';

interface AddSampleModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type ProcessingState = 'idle' | 'submitting' | 'processing' | 'success' | 'error';

interface CreditBalanceData {
  credits: number;
  has_subscription: boolean;
  subscription_tier: string | null;
  monthly_credits: number | null;
  next_renewal: string | null;
}

export function AddSampleModal({ isOpen, onClose }: AddSampleModalProps) {
  const { isSignedIn, getToken } = useAuth();
  const { onMedium, onSuccess, onError } = useHapticFeedback();

  const [url, setUrl] = useState('');
  const [state, setState] = useState<ProcessingState>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [sampleId, setSampleId] = useState<string | null>(null);
  const [creditBalance, setCreditBalance] = useState<number | null>(null);
  const [loadingCredits, setLoadingCredits] = useState(true);

  // Fetch credit balance when modal opens
  useEffect(() => {
    if (isOpen && isSignedIn) {
      setLoadingCredits(true);
      const fetchCredits = async () => {
        try {
          const token = await getToken();
          if (!token) {
            setLoadingCredits(false);
            return;
          }

          const apiClient = createAuthenticatedClient(async () => token);
          const data = await apiClient.get<CreditBalanceData>('/credits/balance');
          setCreditBalance(data.credits);
        } catch (err) {
          console.error('Failed to fetch credit balance:', err);
          setCreditBalance(null);
        } finally {
          setLoadingCredits(false);
        }
      };

      fetchCredits();
    }
  }, [isOpen, isSignedIn, getToken]);

  // Auto-read clipboard when modal opens
  useEffect(() => {
    if (isOpen && navigator.clipboard) {
      navigator.clipboard.readText()
        .then((text) => {
          // Check if it's a TikTok or Instagram URL
          if (text.includes('tiktok.com') || text.includes('instagram.com')) {
            setUrl(text);
          }
        })
        .catch(() => {
          // Clipboard permission denied or not available
          console.log('Could not read clipboard');
        });
    }
  }, [isOpen]);

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setTimeout(() => {
        setUrl('');
        setState('idle');
        setErrorMessage('');
        setSampleId(null);
      }, 300); // Wait for animation
    }
  }, [isOpen]);

  const handleSubmit = useCallback(async () => {
    if (!url.trim()) {
      onError();
      setErrorMessage('Please paste a TikTok or Instagram URL');
      return;
    }

    if (!isSignedIn) {
      onError();
      setErrorMessage('Please sign in to add samples');
      return;
    }

    setState('submitting');
    onMedium();

    try {
      const apiClient = createAuthenticatedClient(getToken);

      // Submit the URL for processing
      const response = await apiClient.post<{ sample_id: string; message: string; status: string }>('/process/submit', {
        url: url.trim(),
      });

      setSampleId(response.sample_id);
      setState('processing');

      // Immediately add to favorites (even if processing hasn't completed)
      try {
        await apiClient.post(`/samples/${response.sample_id}/favorite`, {});
        console.log('Sample added to favorites');
      } catch (favError) {
        // If favoriting fails, log but don't block the flow
        console.error('Failed to add to favorites (will be added when processing completes):', favError);
      }

      // Refresh credit balance after deduction
      try {
        const refreshedData = await apiClient.get<CreditBalanceData>('/credits/balance');
        setCreditBalance(refreshedData.credits);
      } catch (err) {
        console.error('Failed to refresh credit balance:', err);
      }

      // Show success immediately
      setTimeout(() => {
        setState('success');
        onSuccess();
      }, 1500);

    } catch (error) {
      console.error('Error submitting sample:', error);
      setState('error');
      onError();

      if (error instanceof Error) {
        // Handle insufficient credits error specifically
        if (error.message.includes('Insufficient credits') || error.message.includes('402')) {
          setErrorMessage('Insufficient credits. Please top up your account to add more samples.');
        } else {
          setErrorMessage(error.message);
        }
      } else {
        setErrorMessage('Failed to submit sample. Please try again.');
      }
    }
  }, [url, isSignedIn, getToken, onMedium, onSuccess, onError]);

  const handleClose = () => {
    onMedium();
    onClose();
  };

  const handleViewInFavorites = () => {
    onMedium();
    window.location.href = '/mobile/favorites';
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 animate-in fade-in duration-200"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="fixed inset-x-4 top-1/2 -translate-y-1/2 bg-[hsl(0,0%,12%)] rounded-2xl border border-white/10 z-50 animate-in zoom-in-95 slide-in-from-bottom-4 duration-200 max-w-md mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/10">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-[hsl(338,82%,65%)]" />
            <h2 className="text-lg font-semibold text-white">Add Sample</h2>
          </div>
          <button
            onClick={handleClose}
            className="w-8 h-8 flex items-center justify-center rounded-full bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition-all active:scale-95"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {state === 'idle' || state === 'submitting' ? (
            <>
              <p className="text-sm text-gray-400">
                Paste any TikTok or Instagram link. We&apos;ll extract the audio and save it to your favorites automatically!
              </p>

              {/* Credit Info Banner */}
              <div className="flex items-center justify-between p-3 bg-[hsl(338,82%,65%)]/10 border border-[hsl(338,82%,65%)]/20 rounded-lg">
                <div className="flex items-center gap-2">
                  <Coins className="w-4 h-4 text-[hsl(338,82%,65%)]" />
                  <div>
                    <p className="text-xs font-semibold text-white">1 Credit per Sample</p>
                    <p className="text-xs text-gray-400">
                      {loadingCredits ? (
                        'Loading balance...'
                      ) : creditBalance !== null ? (
                        <>You have <span className="font-semibold text-white">{creditBalance}</span> credits</>
                      ) : (
                        'Unable to load balance'
                      )}
                    </p>
                  </div>
                </div>
              </div>

              {/* URL Input */}
              <div className="relative">
                <LinkIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="Paste TikTok or Instagram URL..."
                  className="w-full h-12 pl-11 pr-4 bg-white/5 border border-white/10 rounded-lg text-white placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-[hsl(338,82%,65%)]/50 focus:border-[hsl(338,82%,65%)]"
                  disabled={state === 'submitting'}
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleSubmit();
                    }
                  }}
                />
              </div>

              {/* Error message */}
              {errorMessage && state !== 'submitting' && (
                <div className="flex items-start gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                  <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-400">{errorMessage}</p>
                </div>
              )}

              {/* Submit button */}
              <button
                onClick={handleSubmit}
                disabled={state === 'submitting' || !url.trim() || (creditBalance !== null && creditBalance < 1)}
                className="w-full h-12 bg-[hsl(338,82%,65%)] hover:bg-[hsl(338,82%,55%)] disabled:bg-gray-700 disabled:text-gray-500 text-white font-semibold rounded-lg transition-all active:scale-[0.98] disabled:active:scale-100 flex items-center justify-center gap-2"
              >
                {state === 'submitting' ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Submitting...</span>
                  </>
                ) : creditBalance !== null && creditBalance < 1 ? (
                  <span>Insufficient Credits</span>
                ) : (
                  <span>Add to Favorites</span>
                )}
              </button>
            </>
          ) : state === 'processing' ? (
            <div className="flex flex-col items-center justify-center py-8">
              <div className="relative">
                <div className="w-16 h-16 rounded-full border-4 border-[hsl(338,82%,65%)]/20 animate-pulse" />
                <Loader2 className="w-16 h-16 text-[hsl(338,82%,65%)] animate-spin absolute inset-0" />
              </div>
              <h3 className="text-lg font-semibold text-white mt-4">Processing Sample</h3>
              <p className="text-sm text-gray-400 text-center mt-2">
                We&apos;re downloading and processing your sample. This usually takes 10-30 seconds.
              </p>
              <p className="text-xs text-gray-500 text-center mt-2">
                You can close this and check your favorites later!
              </p>
            </div>
          ) : state === 'success' ? (
            <div className="flex flex-col items-center justify-center py-8">
              <div className="w-16 h-16 rounded-full bg-[hsl(338,82%,65%)]/20 flex items-center justify-center">
                <CheckCircle className="w-10 h-10 text-[hsl(338,82%,65%)]" />
              </div>
              <h3 className="text-lg font-semibold text-white mt-4">Added to Favorites!</h3>
              <p className="text-sm text-gray-400 text-center mt-2">
                Your sample is in your favorites and will be ready to play in 10-30 seconds.
              </p>
              <p className="text-xs text-gray-500 text-center mt-1">
                We&apos;re downloading and processing the audio for you.
              </p>
              <div className="flex gap-2 w-full mt-6">
                <button
                  onClick={handleClose}
                  className="flex-1 h-11 bg-white/5 hover:bg-white/10 text-white font-medium rounded-lg transition-all active:scale-[0.98]"
                >
                  Close
                </button>
                <button
                  onClick={handleViewInFavorites}
                  className="flex-1 h-11 bg-[hsl(338,82%,65%)] hover:bg-[hsl(338,82%,55%)] text-white font-semibold rounded-lg transition-all active:scale-[0.98]"
                >
                  View Favorites
                </button>
              </div>
            </div>
          ) : state === 'error' ? (
            <div className="flex flex-col items-center justify-center py-8">
              <div className="w-16 h-16 rounded-full bg-red-500/20 flex items-center justify-center">
                <AlertCircle className="w-10 h-10 text-red-500" />
              </div>
              <h3 className="text-lg font-semibold text-white mt-4">Something Went Wrong</h3>
              <p className="text-sm text-gray-400 text-center mt-2">
                {errorMessage || 'Failed to submit sample. Please try again.'}
              </p>
              <button
                onClick={() => {
                  setState('idle');
                  setErrorMessage('');
                }}
                className="w-full h-11 bg-[hsl(338,82%,65%)] hover:bg-[hsl(338,82%,55%)] text-white font-semibold rounded-lg transition-all active:scale-[0.98] mt-6"
              >
                Try Again
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </>
  );
}
