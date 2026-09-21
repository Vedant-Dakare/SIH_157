import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';

import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1F5F8B] focus-visible:ring-offset-1 disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        default: 'bg-[#123B5D] text-white hover:bg-[#0E2F4B]',
        destructive: 'bg-[#B91C1C] text-white hover:bg-[#991B1B]',
        outline: 'border border-[#D9E2EC] bg-white text-[#123B5D] hover:bg-[#EAF3F8] hover:border-[#1F5F8B]',
        secondary: 'bg-[#EAF3F8] text-[#123B5D] hover:bg-[#D4E8F4]',
        ghost: 'text-[#52606D] hover:bg-[#F8FAFC] hover:text-[#1F2933]',
        link: 'text-[#1F5F8B] underline-offset-4 hover:underline hover:text-[#123B5D]',
      },
      size: {
        default: 'h-9 px-4 py-2',
        sm: 'h-8 rounded-md px-3 text-xs',
        lg: 'h-10 rounded-md px-8',
        icon: 'h-9 w-9',
      },
    },
    defaultVariants: { variant: 'default', size: 'default' },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  },
);
Button.displayName = 'Button';

export { Button, buttonVariants };
