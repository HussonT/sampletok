'use client';

import { useEffect, useState } from 'react';

/**
 * Mobile Settings Hook
 *
 * Manages mobile-specific settings stored in localStorage.
 * Used across the mobile PWA to control app behavior.
 *
 * Settings:
 * - autoPlayVideos: Auto-play videos in feed when scrolled into view (default: true)
 * - hapticFeedback: Enable haptic/vibration feedback on interactions (default: true)
 * - dataSaverMode: Reduce data usage by lowering quality/preloading (default: false)
 *
 * Usage:
 * ```tsx
 * const { settings, updateSetting, resetSettings } = useMobileSettings();
 *
 * <Switch
 *   checked={settings.autoPlayVideos}
 *   onCheckedChange={(checked) => updateSetting('autoPlayVideos', checked)}
 * />
 * ```
 */

export interface MobileSettings {
  autoPlayVideos: boolean;
  hapticFeedback: boolean;
  dataSaverMode: boolean;
}

const DEFAULT_SETTINGS: MobileSettings = {
  autoPlayVideos: true,
  hapticFeedback: true,
  dataSaverMode: false,
};

const STORAGE_KEY = 'sampletok_mobile_settings';

/**
 * Load settings from localStorage
 */
function loadSettings(): MobileSettings {
  if (typeof window === 'undefined') {
    return DEFAULT_SETTINGS;
  }

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return { ...DEFAULT_SETTINGS, ...parsed };
    }
  } catch (error) {
    console.error('Failed to load mobile settings:', error);
  }

  return DEFAULT_SETTINGS;
}

/**
 * Save settings to localStorage
 */
function saveSettings(settings: MobileSettings): void {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch (error) {
    console.error('Failed to save mobile settings:', error);
  }
}

export function useMobileSettings() {
  const [settings, setSettings] = useState<MobileSettings>(DEFAULT_SETTINGS);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load settings on mount
  useEffect(() => {
    const loaded = loadSettings();
    setSettings(loaded);
    setIsLoaded(true);
  }, []);

  // Update a single setting
  const updateSetting = <K extends keyof MobileSettings>(
    key: K,
    value: MobileSettings[K]
  ) => {
    setSettings((prev) => {
      const updated = { ...prev, [key]: value };
      saveSettings(updated);
      return updated;
    });
  };

  // Reset all settings to defaults
  const resetSettings = () => {
    setSettings(DEFAULT_SETTINGS);
    saveSettings(DEFAULT_SETTINGS);
  };

  return {
    settings,
    updateSetting,
    resetSettings,
    isLoaded,
  };
}
