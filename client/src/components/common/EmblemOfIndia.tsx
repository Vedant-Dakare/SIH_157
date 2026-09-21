export function EmblemOfIndia({ className = 'h-11 w-auto' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 100 135"
      className={className}
      fill="currentColor"
      aria-label="State Emblem of India"
      role="img"
    >
      {/* Central Lion Head & Mane */}
      <path d="M50 12 C44 12 40 16 39 21 C36 21 34 23 34 26 C34 28 35 30 37 31 C36 33 36 36 37 38 C38 41 40 43 43 44 C41 46 40 49 41 52 C42 55 45 57 48 57 L52 57 C55 57 58 55 59 52 C60 49 59 46 57 44 C60 43 62 41 63 38 C64 36 64 33 63 31 C65 30 66 28 66 26 C66 23 64 21 61 21 C60 16 56 12 50 12 Z" />
      {/* Left Lion Head & Mane */}
      <path d="M34 23 C30 23 27 26 26 30 C24 30 22 32 22 35 C22 37 23 39 25 40 C24 42 24 45 25 47 C26 50 28 52 31 53 C29 55 28 58 29 61 C30 64 33 66 36 66 L38 66 C39 63 41 61 43 59 C40 58 38 56 37 53 C36 51 36 48 37 46 C35 45 34 43 34 41 C34 38 36 36 38 35 C38 32 37 29 36 26 C36 24 35 23 34 23 Z" />
      {/* Right Lion Head & Mane */}
      <path d="M66 23 C65 23 64 24 64 26 C63 29 62 32 62 35 C64 36 66 38 66 41 C66 43 65 45 63 46 C64 48 64 51 63 53 C62 56 60 58 57 59 C59 61 61 63 62 66 L64 66 C67 66 70 64 71 61 C72 58 71 55 69 53 C72 52 74 50 75 47 C76 45 76 42 75 40 C77 39 78 37 78 35 C78 32 76 30 74 30 C73 26 70 23 66 23 Z" />
      {/* Pillar & Lion Bodies */}
      <path d="M36 67 L64 67 L67 86 L33 86 Z" />
      {/* Capital Abacus Base */}
      <rect x="22" y="87" width="56" height="5" rx="1" />
      {/* Ashoka Chakra in Abacus */}
      <circle cx="50" cy="98" r="7" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <circle cx="50" cy="98" r="1.5" />
      <line x1="50" y1="91" x2="50" y2="105" stroke="currentColor" strokeWidth="0.8" />
      <line x1="43" y1="98" x2="57" y2="98" stroke="currentColor" strokeWidth="0.8" />
      <line x1="45" y1="93" x2="55" y2="103" stroke="currentColor" strokeWidth="0.8" />
      <line x1="45" y1="103" x2="55" y2="93" stroke="currentColor" strokeWidth="0.8" />
      {/* Bull on left, Horse on right */}
      <ellipse cx="32" cy="98" rx="5" ry="3" />
      <ellipse cx="68" cy="98" rx="5" ry="3" />
      {/* Lower Abacus Base */}
      <rect x="18" y="106" width="64" height="4" rx="1" />
      {/* Lotus Bell Inverted Base */}
      <path d="M24 110 C24 110 32 119 50 119 C68 119 76 110 76 110 L78 122 L22 122 Z" />
      <rect x="16" y="123" width="68" height="3" rx="1" />
      {/* Satyameva Jayate (सत्यमेव जयते) Text representation */}
      <text
        x="50"
        y="133"
        textAnchor="middle"
        fontSize="7.5"
        fontWeight="bold"
        fontFamily="sans-serif"
        letterSpacing="0.8"
      >
        सत्यमेव जयते
      </text>
    </svg>
  );
}
