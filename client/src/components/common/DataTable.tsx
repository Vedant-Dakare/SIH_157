import * as React from 'react';
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
  type VisibilityState,
} from '@tanstack/react-table';
import { ArrowDown, ArrowUp, ChevronsUpDown, Columns3 } from 'lucide-react';

import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingState } from '@/components/common/LoadingState';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { cn } from '@/lib/utils';

export interface DataTableProps<TData> {
  columns: ColumnDef<TData>[];
  data: TData[];
  isLoading: boolean;
  error: Error | null;
  pagination?: boolean;
  filtering?: boolean;
  filterPlaceholder?: string;
  emptyTitle?: string;
  emptyDescription?: string;
  onRowClick?: (row: TData) => void;
  onRetry?: () => void;
  getRowClassName?: (row: TData) => string | undefined;
}

const PAGE_SIZES = [25, 50, 100] as const;

/** TanStack Table wrapper: sort, filter, pagination, visibility, all states. */
export function DataTable<TData>({
  columns,
  data,
  isLoading,
  error,
  pagination = true,
  filtering = true,
  filterPlaceholder = 'Filter rows…',
  emptyTitle = 'No results',
  emptyDescription = 'Nothing matches the current filters.',
  onRowClick,
  onRetry,
  getRowClassName,
}: DataTableProps<TData>) {
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = React.useState('');
  const [columnVisibility, setColumnVisibility] = React.useState<VisibilityState>({});
  const [pageSize, setPageSize] = React.useState<number>(PAGE_SIZES[0]);

  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter, columnVisibility, pagination: { pageIndex: 0, pageSize } },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });

  // Keep page size in sync without recreating the table.
  React.useEffect(() => {
    table.setPageSize(pageSize);
  }, [pageSize, table]);

  if (isLoading) {
    return <LoadingState rows={6} message="Loading table…" />;
  }
  if (error) {
    return <ErrorState error={error} retry={onRetry} />;
  }
  if (data.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }

  return (
    <div className="w-full space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {filtering ? (
          <Input
            type="search"
            aria-label="Filter table rows"
            placeholder={filterPlaceholder}
            value={globalFilter}
            onChange={(event) => setGlobalFilter(event.target.value)}
            className="max-w-xs"
          />
        ) : null}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              type="button"
              variant="outline"
              size="sm"
              aria-label="Toggle column visibility"
            >
              <Columns3 className="h-4 w-4" aria-hidden="true" />
              Columns
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" aria-label="Column visibility options">
            {table
              .getAllColumns()
              .filter((column) => column.getCanHide())
              .map((column) => (
                <DropdownMenuCheckboxItem
                  key={column.id}
                  checked={column.getIsVisible()}
                  onCheckedChange={(value) => column.toggleVisibility(Boolean(value))}
                >
                  {column.id}
                </DropdownMenuCheckboxItem>
              ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <div className="rounded-md border border-[#D9E2EC] bg-white shadow-xs overflow-x-auto">
        <Table aria-label="Data table">
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder ? null : (
                      <button
                        type="button"
                        aria-label={`Sort by ${String(header.column.id)}`}
                        onClick={header.column.getToggleSortingHandler()}
                        className="inline-flex items-center gap-1 rounded-sm focus:outline-none focus:ring-2 focus:ring-blue-200"
                      >
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {header.column.getIsSorted() === 'asc' ? (
                          <ArrowUp className="h-3 w-3" aria-hidden="true" />
                        ) : header.column.getIsSorted() === 'desc' ? (
                          <ArrowDown className="h-3 w-3" aria-hidden="true" />
                        ) : (
                          <ChevronsUpDown className="h-3 w-3 text-slate-500" aria-hidden="true" />
                        )}
                      </button>
                    )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="text-center text-slate-500">
                  No rows match the current filter.
                </TableCell>
              </TableRow>
            ) : (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() ? 'selected' : undefined}
                  onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                  onKeyDown={
                    onRowClick
                      ? (event) => {
                          if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault();
                            onRowClick(row.original);
                          }
                        }
                      : undefined
                  }
                  tabIndex={onRowClick ? 0 : undefined}
                  className={
                    cn(onRowClick && 'cursor-pointer', getRowClassName?.(row.original)) || undefined
                  }
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
      {pagination ? (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <label htmlFor="page-size-select">Rows per page</label>
            <Select
              value={String(pageSize)}
              onValueChange={(value) => setPageSize(Number(value))}
            >
              <SelectTrigger id="page-size-select" className="h-8 w-20" aria-label="Rows per page">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PAGE_SIZES.map((size) => (
                  <SelectItem key={size} value={String(size)}>
                    {size}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              aria-label="Previous page"
              disabled={!table.getCanPreviousPage()}
              onClick={() => table.previousPage()}
            >
              Previous
            </Button>
            <span aria-live="polite" className="text-sm text-slate-600">
              Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
            </span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              aria-label="Next page"
              disabled={!table.getCanNextPage()}
              onClick={() => table.nextPage()}
            >
              Next
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
