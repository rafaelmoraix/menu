interface DotProps {
  className?: string;
  color?: string;
}

export default function Dot({ className, color = '#FF5C35' }: DotProps) {
  return <span className={`inline-block rounded-full ${className ?? ''}`} style={{ backgroundColor: color }} aria-hidden="true" />;
}
