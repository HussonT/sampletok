'use client';

import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Loader2, Layers } from 'lucide-react';
import { Sample } from '@/types/api';
import { toast } from 'sonner';
import { useAuth } from '@clerk/nextjs';
import { analytics } from '@/lib/analytics';

interface StemSeparationModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  sample: Sample;
  userCredits?: number;
  onSuccess?: () => void;
}

// Available stem types from La La AI Phoenix model
const STEM_TYPES = [
  { value: 'vocal', label: 'Vocals' },
  { value: 'drum', label: 'Drums' },
  { value: 'bass', label: 'Bass' },
  { value: 'piano', label: 'Piano' },
  { value: 'electric_guitar', label: 'Electric Guitar' },
  { value: 'acoustic_guitar', label: 'Acoustic Guitar' },
  { value: 'synthesizer', label: 'Synthesizer' },
  { value: 'strings', label: 'Strings' },
  { value: 'wind', label: 'Wind Instruments' },
];

const CREDITS_PER_STEM = 2;

export function StemSeparationModal({
  open,
  onOpenChange,
  sample,
  userCredits = 0,
  onSuccess
}: StemSeparationModalProps) {
  const { getToken } = useAuth();
  const [selectedStems, setSelectedStems] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const totalCredits = selectedStems.length * CREDITS_PER_STEM;
  const hasEnoughCredits = userCredits >= totalCredits;

  const handleStemToggle = (stemValue: string) => {
    setSelectedStems(prev =>
      prev.includes(stemValue)
        ? prev.filter(s => s !== stemValue)
        : [...prev, stemValue]
    );
  };

  const handleSubmit = async () => {
    if (selectedStems.length === 0) {
      toast.error('Please select at least one stem to separate');
      return;
    }

    if (!hasEnoughCredits) {
      toast.error('Insufficient credits');
      return;
    }

    setIsSubmitting(true);

    try {
      const token = await getToken();
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/stems/${sample.id}/separate-stems`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          stems: selectedStems
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        const errorMessage = error.detail || 'Failed to submit stem separation';

        // Handle specific error cases
        if (response.status === 400 && errorMessage.includes('already exist')) {
          toast.error('Stems Already Processing', {
            description: errorMessage
          });
        } else if (response.status === 402) {
          toast.error('Insufficient Credits', {
            description: errorMessage
          });
        } else {
          toast.error('Failed to Start Stem Separation', {
            description: errorMessage
          });
        }
        return;
      }

      const data = await response.json();

      // Track stem separation started
      analytics.stemSeparationRequested(sample.id, selectedStems, totalCredits);

      toast.success(`Stem separation started! ${data.message}`, {
        description: `Estimated time: ${Math.round(data.estimated_time_seconds / 60)} minutes`
      });

      // Reset and close
      setSelectedStems([]);
      onOpenChange(false);

      // Callback to refresh stems list
      if (onSuccess) {
        onSuccess();
      }
    } catch (error) {
      console.error('Error submitting stem separation:', error);
      toast.error('Request Failed', {
        description: error instanceof Error ? error.message : 'Failed to start stem separation'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Layers className="h-5 w-5" />
            Separate Stems
          </DialogTitle>
          <DialogDescription>
            Select which stems you want to extract from this sample.
            Each stem costs {CREDITS_PER_STEM} credits.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Disclaimer */}
          <div className="rounded-lg bg-muted/50 p-3 text-sm text-muted-foreground">
            <p className="leading-relaxed">
              💡 <span className="font-medium">Pro tip:</span> Results aren&apos;t always perfect! Start with the stems you really need,
              then come back to grab more based on how the first ones turn out.
            </p>
          </div>

          {/* Stem selection */}
          <div className="grid grid-cols-2 gap-3">
            {STEM_TYPES.map((stem) => (
              <div key={stem.value} className="flex items-center space-x-2">
                <Checkbox
                  id={stem.value}
                  checked={selectedStems.includes(stem.value)}
                  onCheckedChange={() => handleStemToggle(stem.value)}
                />
                <Label
                  htmlFor={stem.value}
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                >
                  {stem.label}
                </Label>
              </div>
            ))}
          </div>

          {/* Credit calculation */}
          <div className="rounded-lg border p-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Selected stems:</span>
              <span className="font-medium">{selectedStems.length}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Credits per stem:</span>
              <span className="font-medium">{CREDITS_PER_STEM}</span>
            </div>
            <div className="flex justify-between text-sm font-semibold border-t pt-2">
              <span>Total cost:</span>
              <span className={!hasEnoughCredits && selectedStems.length > 0 ? 'text-destructive' : ''}>
                {totalCredits} credits
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Your balance:</span>
              <span className={hasEnoughCredits ? 'text-green-600' : 'text-destructive'}>
                {userCredits} credits
              </span>
            </div>
          </div>

          {!hasEnoughCredits && selectedStems.length > 0 && (
            <div className="text-sm text-destructive">
              You need {totalCredits - userCredits} more credits to process this request.
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={selectedStems.length === 0 || !hasEnoughCredits || isSubmitting}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Processing...
              </>
            ) : (
              `Confirm (${totalCredits} credits)`
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
