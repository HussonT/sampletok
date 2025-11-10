'use client';

import { useEffect, useState } from 'react';
import { useClerk } from '@clerk/nextjs';
import { motion, AnimatePresence } from 'framer-motion';
import { Heart, Music2, Sparkles, X, Monitor } from 'lucide-react';
import { Button } from '@/components/ui/button';

/**
 * Authentication Prompt Modal
 *
 * A conversion-optimized modal that encourages guest users to create accounts
 * after they've experienced the product value. Shows after 7 video views to
 * maximize conversion while respecting user experience.
 *
 * Key Features:
 * - SampleTok pink branding with gradient design for visual appeal
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
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div className="w-full max-w-md bg-gradient-to-b from-[hsl(0,0%,20%)] to-[hsl(0,0%,15%)] rounded-2xl shadow-2xl border border-white/10 overflow-hidden">
              {/* Close button */}
              <button
                onClick={handleDismiss}
                className="absolute top-4 right-4 p-2 rounded-full bg-white/5 hover:bg-white/10 transition-colors z-10"
                aria-label="Close"
              >
                <X className="w-5 h-5 text-gray-400" />
              </button>

              {/* Header with pink gradient and sparkle icon */}
              <div className="relative px-6 pt-8 pb-6 bg-gradient-to-br from-[hsl(338,82%,65%)]/20 to-transparent">
                <div className="flex items-center justify-center mb-4">
                  {/* Sparkle icon with glow effect for visual appeal */}
                  <div className="relative">
                    <div className="absolute inset-0 bg-[hsl(338,82%,65%)] blur-xl opacity-50" />
                    <div className="relative bg-gradient-to-br from-[hsl(338,82%,65%)] to-[hsl(338,82%,55%)] p-4 rounded-2xl">
                      <Sparkles className="w-8 h-8 text-white" />
                    </div>
                  </div>
                </div>
                <h2 className="text-2xl font-bold text-center text-white mb-2">
                  Unlock Full Access
                </h2>
                <p className="text-center text-gray-300 text-sm">
                  Create a free account to save your favorites and never lose track of amazing samples
                </p>
              </div>

              {/* Benefits section - four value propositions */}
              <div className="px-6 py-4 space-y-3">
                {/* Emotional appeal - don't lose what you love */}
                <BenefitItem
                  icon={<Heart className="w-5 h-5 text-[hsl(338,82%,65%)]" />}
                  title="Save Favorites"
                  description="Keep all your favorite samples in one place"
                />
                {/* Desktop experience - full production workflow */}
                <BenefitItem
                  icon={<Monitor className="w-5 h-5 text-[hsl(338,82%,65%)]" />}
                  title="Desktop Experience"
                  description="Access full studio features when you're making music"
                />
                {/* Practical appeal - unlimited access */}
                <BenefitItem
                  icon={<Music2 className="w-5 h-5 text-[hsl(338,82%,65%)]" />}
                  title="Unlimited Downloads"
                  description="Download samples directly to your DAW"
                />
                {/* FOMO appeal - exclusive features */}
                <BenefitItem
                  icon={<Sparkles className="w-5 h-5 text-[hsl(338,82%,65%)]" />}
                  title="Premium Features"
                  description="Stem separation, collections, and more"
                />
              </div>

              {/* CTA Buttons - clear hierarchy */}
              <div className="px-6 pb-6 space-y-3">
                {/* Primary CTA - bright gradient for maximum attention */}
                <Button
                  onClick={handleSignUp}
                  className="w-full bg-gradient-to-r from-[hsl(338,82%,65%)] to-[hsl(338,82%,55%)] hover:from-[hsl(338,82%,70%)] hover:to-[hsl(338,82%,60%)] text-white font-semibold py-6 rounded-xl shadow-lg shadow-[hsl(338,82%,65%)]/25 transition-all"
                >
                  Create Free Account
                </Button>
                {/* Secondary CTA - ghost style for existing users */}
                <Button
                  onClick={handleSignIn}
                  variant="ghost"
                  className="w-full text-gray-300 hover:text-white hover:bg-white/5 py-6 rounded-xl"
                >
                  Already have an account? Sign in
                </Button>
              </div>

              {/* Tertiary option - dismissible, low emphasis */}
              <div className="px-6 pb-6">
                <button
                  onClick={handleDismiss}
                  className="w-full text-sm text-gray-500 hover:text-gray-400 transition-colors"
                >
                  Continue browsing as guest
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

/**
 * Benefit Item Component
 *
 * Displays a single benefit card with icon, title, and description.
 * Used in the auth modal to communicate value propositions.
 *
 * Design: Icon + text layout with subtle background for scannability
 */
interface BenefitItemProps {
  /** Icon component (Lucide icon with SampleTok pink color) */
  icon: React.ReactNode;
  /** Short benefit title (2-3 words) */
  title: string;
  /** Brief description explaining the benefit */
  description: string;
}

function BenefitItem({ icon, title, description }: BenefitItemProps) {
  return (
    <div className="flex items-start gap-3 p-3 rounded-lg bg-white/5 border border-white/5">
      <div className="flex-shrink-0 mt-0.5">
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="font-semibold text-white text-sm mb-0.5">{title}</h3>
        <p className="text-xs text-gray-400">{description}</p>
      </div>
    </div>
  );
}
