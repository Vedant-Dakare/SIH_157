import {
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  Minus,
  ShieldAlert,
  ShieldCheck,
  ShieldQuestion,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { ConfidenceLevel, RiskBand, SignalFamily, TrendStatus } from '@/types/api';

export interface BandStyle {
  bg: string;
  text: string;
  border: string;
  dot: string;
}

/** Risk band colours per Section C (Tailwind classes, never hex). */
export const RISK_BAND_STYLES: Record<RiskBand, BandStyle> = {
  HIGH: {
    bg: 'bg-risk-high-bg',
    text: 'text-red-500',
    border: 'border-red-500',
    dot: 'bg-red-500',
  },
  ELEVATED: {
    bg: 'bg-risk-elevated-bg',
    text: 'text-orange-500',
    border: 'border-orange-500',
    dot: 'bg-orange-500',
  },
  MODERATE: {
    bg: 'bg-risk-moderate-bg',
    text: 'text-yellow-500',
    border: 'border-yellow-500',
    dot: 'bg-yellow-500',
  },
  LOW: {
    bg: 'bg-risk-low-bg',
    text: 'text-green-500',
    border: 'border-green-500',
    dot: 'bg-green-500',
  },
};

export interface ConfidenceStyle {
  bg: string;
  text: string;
  icon: LucideIcon;
}

/** Confidence badge colours per Section C. */
export const CONFIDENCE_STYLES: Record<ConfidenceLevel, ConfidenceStyle> = {
  HIGH: { bg: 'bg-emerald-950', text: 'text-emerald-400', icon: ShieldCheck },
  MEDIUM: { bg: 'bg-yellow-950', text: 'text-yellow-400', icon: ShieldAlert },
  LOW: { bg: 'bg-red-950', text: 'text-red-400', icon: ShieldQuestion },
};

export interface SignalFamilyStyle {
  bg: string;
  text: string;
  label: string;
}

/** Signal family colours per Section C. */
export const SIGNAL_FAMILY_STYLES: Record<SignalFamily, SignalFamilyStyle> = {
  execution_gap: { bg: 'bg-violet-950', text: 'text-violet-400', label: 'Execution Gap' },
  negative_space: { bg: 'bg-cyan-950', text: 'text-cyan-400', label: 'Negative Space' },
  peer: { bg: 'bg-blue-950', text: 'text-blue-400', label: 'Peer' },
  anomaly: { bg: 'bg-orange-950', text: 'text-orange-400', label: 'Anomaly' },
  composite: { bg: 'bg-pink-950', text: 'text-pink-400', label: 'Composite' },
};

export interface TrendStyle {
  icon: LucideIcon;
  text: string;
  colour: string;
}

/** Portfolio trend indicators. */
export const TREND_STYLES: Record<TrendStatus, TrendStyle> = {
  IMPROVING: { icon: ArrowDown, text: 'Improving', colour: 'text-green-500' },
  STABLE: { icon: Minus, text: 'Stable', colour: 'text-slate-400' },
  DETERIORATING: { icon: ArrowUp, text: 'Deteriorating', colour: 'text-red-500' },
  INSUFFICIENT_HISTORY: {
    icon: AlertTriangle,
    text: 'Insufficient history',
    colour: 'text-slate-500',
  },
};

export const BAND_DESCRIPTIONS: Record<RiskBand, string> = {
  HIGH: 'Score ≥ 75. Immediate supervisory review recommended.',
  ELEVATED: 'Score 50–74. Review this window.',
  MODERATE: 'Score 25–49. Monitor for persistence.',
  LOW: 'Score below 25. No action required.',
};
