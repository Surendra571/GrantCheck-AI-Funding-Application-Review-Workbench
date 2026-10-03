import React from 'react';
import { AlertCircle } from 'lucide-react';

interface Props {
  className?: string;
}

export const DisclaimerBanner: React.FC<Props> = ({ className = '' }) => {
  return (
    <div
      className={`flex items-start sm:items-center gap-3 p-3.5 bg-amber-50/90 border border-amber-200/80 rounded-lg text-amber-900 text-xs sm:text-sm font-medium shadow-xs ${className}`}
      role="alert"
    >
      <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5 sm:mt-0" />
      <div>
        <span className="font-semibold uppercase tracking-wider text-[11px] bg-amber-200/60 text-amber-900 px-1.5 py-0.5 rounded mr-2">
          Regulatory Notice
        </span>
        This application is an AI-assisted completeness and evidence-review workbench. It does <strong>NOT</strong> make an authoritative legal, regulatory, or funding-eligibility decision.
      </div>
    </div>
  );
};
