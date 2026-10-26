import { useId } from 'react';

// The app icon (assets/logo.svg) cropped to its rounded square, for use inside the window.
// The --brand-* tokens are identical in both themes: the mark looks the same in light and dark,
// just like the icon in the Dock.
const LOGO_PATH =
  'M325 280 L695 280 L695 385 L671 385 L659 324 L423 324 L570 512 L407 700 L663 700 ' +
  'L675 640 L699 640 L699 744 L325 744 L325 724 L500 512 L325 300 Z';

export function Logo({ size }: { size: number }) {
  const gradient = useId();
  return (
    <svg width={size} height={size} viewBox="100 100 824 824" aria-hidden className="shrink-0">
      <defs>
        <linearGradient id={gradient} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="var(--brand-ink-top)" />
          <stop offset="1" stopColor="var(--brand-ink-bottom)" />
        </linearGradient>
      </defs>
      <rect x="100" y="100" width="824" height="824" rx="185" fill={`url(#${gradient})`} />
      <rect
        x="106"
        y="106"
        width="812"
        height="812"
        rx="180"
        fill="none"
        stroke="white"
        strokeOpacity="0.12"
        strokeWidth="12"
      />
      <path d={LOGO_PATH} fill="var(--brand-mark)" />
    </svg>
  );
}
