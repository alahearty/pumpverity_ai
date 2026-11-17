import { cn } from '@/lib/utils'

interface BrandMarkProps {
  className?: string
}

function BrandMark({ className }: BrandMarkProps) {
  return (
    <svg
      viewBox="0 0 48 48"
      aria-hidden="true"
      className={cn('size-11 shrink-0', className)}
    >
      <rect width="48" height="48" rx="13" fill="#0B1F33" />
      <circle cx="24" cy="24" r="16" stroke="#00A6A6" strokeWidth="1.6" opacity="0.75" />
      <circle cx="24" cy="24" r="10.5" stroke="#E2E8F0" strokeWidth="1.3" opacity="0.4" />
      <g stroke="#E2E8F0" strokeWidth="2.2" strokeLinecap="round" opacity="0.9">
        <path d="M24 24L24 12.5" />
        <path d="M24 24L34 18.2" />
        <path d="M24 24L34 29.8" />
        <path d="M24 24L24 35.5" />
        <path d="M24 24L14 29.8" />
        <path d="M24 24L14 18.2" />
      </g>
      <circle cx="24" cy="24" r="3.1" fill="#00A6A6" />
    </svg>
  )
}

export { BrandMark }
