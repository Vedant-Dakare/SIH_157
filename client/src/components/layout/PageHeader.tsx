import type { ReactNode } from 'react';

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="mb-6">
      <div className="gov-card overflow-hidden">
        <div className="h-[3px] bg-[#123B5D]" aria-hidden="true" />

        <div className="flex flex-wrap items-center justify-between gap-4 px-5 py-5 sm:px-6">
          <div className="min-w-0 flex-1">
            <div className="mb-1 text-[10px] font-bold uppercase tracking-[0.15em] text-[#52606D]">
              Government of India · Security Operations Supervision
            </div>

            <h1 className="text-2xl font-bold tracking-tight text-[#1F2933] sm:text-[26px]">
              {title}
            </h1>

            {description ? (
              <p className="mt-1.5 max-w-4xl text-sm leading-relaxed text-[#52606D]">
                {description}
              </p>
            ) : null}
          </div>

          {actions ? (
            <div className="flex flex-wrap items-center gap-2.5 shrink-0">
              {actions}
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}