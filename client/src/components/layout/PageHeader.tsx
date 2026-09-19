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
    <div className="mb-6">
      <div className="gov-card overflow-hidden">
        <div className="h-1 bg-[#123d73]" />

        <div className="flex flex-wrap items-center justify-between gap-4 px-5 py-5 sm:px-6">
          <div>
            <div className="mb-1 text-[10px] font-bold uppercase tracking-[0.16em] text-[#7b8798]">
              Security Operations Supervision
            </div>

            <h1 className="text-2xl font-bold tracking-tight text-[#102a56]">
              {title}
            </h1>

            {description ? (
              <p className="mt-1.5 text-sm text-[#66758a]">
                {description}
              </p>
            ) : null}
          </div>

          {actions ? (
            <div className="flex flex-wrap items-center gap-2">
              {actions}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}