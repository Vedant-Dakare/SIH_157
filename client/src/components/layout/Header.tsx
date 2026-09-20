import { Search } from 'lucide-react';

export function Header() {
  return (
    <header className="fixed left-0 right-0 top-0 z-40 h-[110px] bg-white">
      {/* Top utility bar */}
      <div className="flex h-8 items-center justify-end gap-4 bg-[#082b57] px-5 text-[11px] text-blue-50 sm:px-6">
        <span>Accessibility</span>
        <span>English</span>
        <span>A-</span>
        <span className="font-semibold">A</span>
        <span>A+</span>
        <span className="text-blue-300">|</span>
        <span>Help</span>
      </div>

      {/* Main header */}
      <div className="flex h-[78px] items-center justify-end gap-6 bg-white px-5 sm:px-6 lg:ml-[248px]">
        <div className="flex min-w-0 items-center gap-3">
          <div className="relative hidden w-[300px] xl:block">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
              aria-hidden="true"
            />

            <input
              type="search"
              aria-label="Search cases or entities"
              placeholder="Search cases or entities"
              className="h-10 w-full rounded-md border border-slate-300 bg-slate-50 pl-10 pr-3 text-sm text-slate-700 outline-none placeholder:text-slate-400 transition-colors focus:border-blue-400 focus:bg-white focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div className="hidden h-10 items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 text-xs text-slate-700 md:flex">
            <span
              className="h-2.5 w-2.5 rounded-full bg-emerald-500"
              aria-hidden="true"
            />
            <span>System operational</span>
          </div>
        </div>
      </div>
    </header>
  );
}