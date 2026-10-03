import React from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  XCircle,
  Clock,
  CheckCheck,
  Edit3,
  Ban,
  ShieldCheck,
  ShieldAlert,
} from 'lucide-react';
import { MappingStatus, ReviewerDecision } from '../types';

export const StatusBadge: React.FC<{ status: MappingStatus | string; size?: 'sm' | 'md' }> = ({
  status,
  size = 'md',
}) => {
  const s = (status || '').toUpperCase();
  const px = size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs';

  if (s === 'SUPPORTED') {
    return (
      <span className={`inline-flex items-center gap-1 font-bold rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200/80 ${px}`}>
        <CheckCircle2 className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />
        SUPPORTED
      </span>
    );
  }
  if (s === 'WEAK') {
    return (
      <span className={`inline-flex items-center gap-1 font-bold rounded-md bg-amber-50 text-amber-700 border border-amber-200/80 ${px}`}>
        <AlertTriangle className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />
        WEAK EVIDENCE
      </span>
    );
  }
  if (s === 'AMBIGUOUS') {
    return (
      <span className={`inline-flex items-center gap-1 font-bold rounded-md bg-purple-50 text-purple-700 border border-purple-200/80 ${px}`}>
        <HelpCircle className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />
        AMBIGUOUS
      </span>
    );
  }
  return (
    <span className={`inline-flex items-center gap-1 font-bold rounded-md bg-rose-50 text-rose-700 border border-rose-200/80 ${px}`}>
      <XCircle className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />
      MISSING EVIDENCE
    </span>
  );
};

export const ReviewDecisionBadge: React.FC<{ decision: ReviewerDecision | string; size?: 'sm' | 'md' }> = ({
  decision,
  size = 'md',
}) => {
  const d = (decision || 'PENDING').toUpperCase();
  const px = size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs';

  if (d === 'CONFIRMED') {
    return (
      <span className={`inline-flex items-center gap-1 font-bold rounded-md bg-teal-50 text-teal-800 border border-teal-300 ${px}`}>
        <CheckCheck className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />
        HUMAN CONFIRMED
      </span>
    );
  }
  if (d === 'CORRECTED') {
    return (
      <span className={`inline-flex items-center gap-1 font-bold rounded-md bg-blue-50 text-blue-800 border border-blue-300 ${px}`}>
        <Edit3 className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />
        HUMAN CORRECTED
      </span>
    );
  }
  if (d === 'REJECTED') {
    return (
      <span className={`inline-flex items-center gap-1 font-bold rounded-md bg-rose-50 text-rose-800 border border-rose-300 ${px}`}>
        <Ban className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />
        HUMAN REJECTED
      </span>
    );
  }
  return (
    <span className={`inline-flex items-center gap-1 font-medium rounded-md bg-slate-100 text-slate-600 border border-slate-200 ${px}`}>
      <Clock className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />
      PENDING REVIEW
    </span>
  );
};

export const FinalAssessmentBadge: React.FC<{ isComplete: boolean; effectiveStatus: string; size?: 'sm' | 'md' }> = ({
  isComplete,
  effectiveStatus,
  size = 'md',
}) => {
  const px = size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs';

  if (isComplete) {
    return (
      <span className={`inline-flex items-center gap-1 font-black tracking-wide rounded-md bg-emerald-600 text-white shadow-xs ${px}`}>
        <ShieldCheck className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />
        FINAL: COMPLETE
      </span>
    );
  }
  return (
    <span className={`inline-flex items-center gap-1 font-black tracking-wide rounded-md bg-rose-600 text-white shadow-xs ${px}`}>
      <ShieldAlert className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />
      FINAL: INCOMPLETE ({effectiveStatus})
    </span>
  );
};

export const RequirementTypeBadge: React.FC<{ mandatory: boolean; typeStr: string }> = ({
  mandatory,
  typeStr,
}) => {
  if (mandatory) {
    return (
      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200 uppercase tracking-wider">
        MANDATORY
      </span>
    );
  }
  return (
    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200 uppercase tracking-wider">
      RECOMMENDATION
    </span>
  );
};
