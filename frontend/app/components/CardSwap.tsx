'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';

interface CardSwapProps {
  images: string[];
  alt: string;
  className?: string;
  cycleInterval?: number;
}

export default function CardSwap({
  images,
  alt,
  className = '',
  cycleInterval = 1000
}: CardSwapProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isHovering, setIsHovering] = useState(false);

  // Ensure we have at least 3 cards by repeating images if needed
  const displayImages = images.length < 3
    ? [...images, ...images, ...images].slice(0, 3)
    : images;

  useEffect(() => {
    if (isHovering && displayImages.length > 1) {
      const interval = setInterval(() => {
        setCurrentIndex((prev) => (prev + 1) % displayImages.length);
      }, cycleInterval);

      return () => clearInterval(interval);
    }
  }, [isHovering, displayImages.length, cycleInterval]);

  if (!images || images.length === 0) {
    return null;
  }

  // Show up to 5 cards in the stack
  const stackSize = Math.min(5, displayImages.length);
  const visibleCards = Array.from({ length: stackSize }, (_, i) =>
    (currentIndex + i) % displayImages.length
  );

  return (
    <div
      className={`relative ${className}`}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
      style={{ perspective: '1000px' }}
    >
      {visibleCards.map((imageIndex, stackPosition) => {
        const isTopCard = stackPosition === 0;

        return (
          <div
            key={`${imageIndex}-${stackPosition}`}
            className="absolute inset-0 rounded-lg overflow-hidden shadow-2xl border-2 border-white/40 transition-all duration-500 ease-out"
            style={{
              transform: `translateX(${stackPosition * 8}px) translateY(${stackPosition * -8}px) rotate(${stackPosition * 4}deg) scale(${1 - stackPosition * 0.1})`,
              zIndex: stackSize - stackPosition,
              opacity: isTopCard ? 1 : 0.9,
              boxShadow: '0 15px 40px rgba(0,0,0,0.5)',
              transformStyle: 'preserve-3d',
            }}
          >
            <Image
              src={displayImages[imageIndex]}
              alt={`${alt} ${imageIndex + 1}`}
              fill
              className="object-cover"
              sizes="(max-width: 768px) 96px, 96px"
              priority={stackPosition < 3}
            />
          </div>
        );
      })}
    </div>
  );
}
