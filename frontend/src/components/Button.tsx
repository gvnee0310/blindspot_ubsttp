import type { ButtonHTMLAttributes, ReactNode } from 'react';

type Variant = 'primary' | 'secondary' | 'ghost';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  children: ReactNode;
}

const styles: Record<Variant, string> = {
  primary:
    'bg-teal-600 text-white hover:bg-teal-700 disabled:bg-ink-line disabled:text-ink-faint shadow-sm',
  secondary:
    'bg-paper-raised text-ink border border-ink-line hover:border-teal-400 hover:text-teal-700',
  ghost: 'text-ink-soft hover:text-ink bg-transparent',
};

export default function Button({ variant = 'primary', className = '', children, ...rest }: Props) {
  return (
    <button
      {...rest}
      className={`inline-flex items-center justify-center rounded-full px-5 py-2.5 text-sm font-semibold transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-400 focus-visible:ring-offset-2 focus-visible:ring-offset-paper disabled:cursor-not-allowed active:scale-[0.98] ${styles[variant]} ${className}`}
    >
      {children}
    </button>
  );
}
