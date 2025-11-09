/**
 * Generate PWA icons placeholder script
 * This creates simple placeholder icons with the SampleTok branding
 *
 * For production, replace these with professionally designed icons
 * using tools like: https://www.pwabuilder.com/imageGenerator
 */

import { createCanvas } from 'canvas';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const iconsDir = path.join(__dirname, '../public/icons');

// Ensure icons directory exists
if (!fs.existsSync(iconsDir)) {
  fs.mkdirSync(iconsDir, { recursive: true });
}

function generateIcon(size, filename, isMaskable = false) {
  const canvas = createCanvas(size, size);
  const ctx = canvas.getContext('2d');

  // Background - green gradient
  const gradient = ctx.createLinearGradient(0, 0, size, size);
  gradient.addColorStop(0, '#10b981'); // emerald-500
  gradient.addColorStop(1, '#059669'); // emerald-600
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);

  // If maskable, add safe zone padding (20% on all sides)
  const safeZone = isMaskable ? size * 0.2 : 0;
  const contentSize = size - (safeZone * 2);
  const contentX = safeZone;
  const contentY = safeZone;

  // Draw musical note icon (simple representation)
  ctx.fillStyle = '#ffffff';

  // Note stem
  const stemWidth = contentSize * 0.12;
  const stemHeight = contentSize * 0.6;
  const stemX = contentX + contentSize * 0.55;
  const stemY = contentY + contentSize * 0.2;
  ctx.fillRect(stemX, stemY, stemWidth, stemHeight);

  // Note head
  const headRadius = contentSize * 0.15;
  const headX = stemX + stemWidth / 2;
  const headY = stemY + stemHeight;

  ctx.beginPath();
  ctx.ellipse(headX, headY, headRadius, headRadius * 0.7, Math.PI * 0.25, 0, Math.PI * 2);
  ctx.fill();

  // Wave accent (represents audio waveform)
  ctx.strokeStyle = '#ffffff';
  ctx.lineWidth = contentSize * 0.08;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  ctx.beginPath();
  const waveY = contentY + contentSize * 0.7;
  const wavePoints = 5;
  const waveWidth = contentSize * 0.4;
  const waveHeight = contentSize * 0.15;

  for (let i = 0; i <= wavePoints; i++) {
    const x = contentX + contentSize * 0.1 + (waveWidth / wavePoints) * i;
    const y = waveY + (i % 2 === 0 ? -waveHeight / 2 : waveHeight / 2);
    if (i === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  }
  ctx.stroke();

  // Save to file
  const buffer = canvas.toBuffer('image/png');
  fs.writeFileSync(path.join(iconsDir, filename), buffer);
  console.log(`✓ Generated ${filename}`);
}

// Generate all required icon sizes
console.log('Generating PWA icons...\n');

generateIcon(192, 'icon-192x192.png', false);
generateIcon(512, 'icon-512x512.png', false);
generateIcon(192, 'icon-192x192-maskable.png', true);
generateIcon(512, 'icon-512x512-maskable.png', true);

// Also generate apple-touch-icon
generateIcon(180, 'apple-touch-icon.png', false);

// Generate favicon
generateIcon(32, 'favicon-32x32.png', false);
generateIcon(16, 'favicon-16x16.png', false);

console.log('\n✅ All icons generated successfully!');
console.log('\n📝 Note: These are placeholder icons. For production, use professionally designed icons.');
console.log('   Recommended tool: https://www.pwabuilder.com/imageGenerator\n');
