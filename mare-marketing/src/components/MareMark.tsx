interface MareMarkProps {
  className?: string;
  shapeColor?: string;
  dotColor?: string;
}

export default function MareMark({ className, shapeColor = 'currentColor', dotColor = '#FF5C35' }: MareMarkProps) {
  return (
    <svg viewBox="0 0 40 40" className={className} fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M20 4L36 20L20 36L4 20L20 4Z" stroke={shapeColor} strokeWidth="2" />
      <circle cx="20" cy="4" r="3.5" fill={dotColor} />
    </svg>
  );
}
