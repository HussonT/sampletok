'use client';

import { useEffect, useState } from 'react';
import { useClerk } from '@clerk/nextjs';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';

/**
 * Authentication Prompt Modal
 *
 * A conversion-optimized modal that encourages guest users to create accounts
 * after they've experienced the product value. Shows after 7 video views to
 * maximize conversion while respecting user experience.
 *
 * Key Features:
 * - Sample the Internet branding with gradient design for visual appeal
 * - Smooth Framer Motion animations (spring physics for natural feel)
 * - Three clear benefit cards explaining value proposition
 * - Multiple CTAs: Sign Up (primary), Sign In (secondary), Continue as Guest (tertiary)
 * - Dismissible via X button or backdrop click
 * - Returns user to exact same page after authentication
 *
 * Design Philosophy:
 * - Show value before asking for commitment (7 videos = user understands product)
 * - Clear benefits (emotional + practical + FOMO)
 * - Low friction (Clerk handles auth, no forms to fill)
 * - Respect user choice (dismissible, non-blocking)
 *
 * @example
 * ```tsx
 * const { shouldShowModal, dismissModal, closeModal } = useAuthPrompt();
 *
 * <AuthPromptModal
 *   isOpen={shouldShowModal}
 *   onClose={closeModal}        // Close without marking as dismissed (can show again later)
 *   onDismiss={dismissModal}    // User actively chose to continue as guest
 * />
 * ```
 */
interface AuthPromptModalProps {
  /** Controls modal visibility */
  isOpen: boolean;
  /** Called when modal should close (without marking as dismissed) */
  onClose: () => void;
  /** Called when user actively dismisses modal ("Continue as guest" clicked) */
  onDismiss: () => void;
}

export function AuthPromptModal({ isOpen, onClose, onDismiss }: AuthPromptModalProps) {
  const { openSignUp, openSignIn } = useClerk();
  const [mounted, setMounted] = useState(false);

  // Prevent hydration mismatch by only rendering after client mount
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  /**
   * Opens Clerk sign-up modal and preserves current URL
   * Returns user to exact same page after authentication completes
   */
  const handleSignUp = () => {
    const currentUrl = window.location.pathname + window.location.search;
    openSignUp({
      redirectUrl: currentUrl,
      afterSignUpUrl: currentUrl,
    });
    onClose();
  };

  /**
   * Opens Clerk sign-in modal and preserves current URL
   * Returns user to exact same page after authentication completes
   */
  const handleSignIn = () => {
    const currentUrl = window.location.pathname + window.location.search;
    openSignIn({
      redirectUrl: currentUrl,
      afterSignInUrl: currentUrl,
    });
    onClose();
  };

  /**
   * User actively chose to dismiss modal and continue as guest
   * Calls onDismiss to mark as dismissed (won't show again this session)
   */
  const handleDismiss = () => {
    onDismiss();
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop - semi-transparent with blur for focus */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleDismiss}
            className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50"
          />

          {/* Modal - spring animation for natural feel */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none"
          >
            <div className="w-full max-w-sm bg-gradient-to-b from-[hsl(0,0%,20%)] to-[hsl(0,0%,15%)] rounded-xl shadow-2xl border border-white/10 overflow-hidden pointer-events-auto">
              {/* Close button */}
              <button
                onClick={handleDismiss}
                className="absolute top-3 right-3 p-1.5 rounded-full bg-white/5 hover:bg-white/10 transition-colors z-10"
                aria-label="Close"
              >
                <X className="w-4 h-4 text-gray-400" />
              </button>

              {/* Header - compact */}
              <div className="px-5 pt-6 pb-4 text-center">
                <h2 className="text-xl font-bold text-white mb-1">
                  Sign in to continue
                </h2>
                <p className="text-sm text-gray-400">
                  Create a free account to save favorites and download samples
                </p>
              </div>

              {/* CTA Buttons - compact */}
              <div className="px-5 pb-5 space-y-2.5">
                {/* Primary CTA */}
                <Button
                  onClick={handleSignUp}
                  className="w-full bg-gradient-to-r from-[hsl(338,82%,65%)] to-[hsl(338,82%,55%)] hover:from-[hsl(338,82%,70%)] hover:to-[hsl(338,82%,60%)] text-white font-semibold py-3 rounded-lg shadow-lg shadow-[hsl(338,82%,65%)]/20 transition-all"
                >
                  Create Account
                </Button>
                {/* Secondary CTA */}
                <Button
                  onClick={handleSignIn}
                  variant="ghost"
                  className="w-full text-gray-300 hover:text-white hover:bg-white/5 py-3 rounded-lg text-sm"
                >
                  Sign In
                </Button>
              </div>

              {/* Dismiss option */}
              <div className="px-5 pb-4">
                <button
                  onClick={handleDismiss}
                  className="w-full text-xs text-gray-500 hover:text-gray-400 transition-colors"
                >
                  Not now
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
