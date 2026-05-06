import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { TrustLevel } from '@/types/cockpit-home';

interface EvidenceBadgeProps {
  level: TrustLevel;
  className?: string;
}

export function EvidenceBadge({ level, className }: EvidenceBadgeProps) {
  const getColors = (l: TrustLevel) => {
    switch (l) {
      case 'CLAIM-VERIFIED':
      case 'EVIDENCE-READY':
        return 'bg-green-500/10 text-green-500 border-green-500/20';
      case 'DEGRADED-RUNTIME':
      case 'STALE':
      case 'MISSING-EVIDENCE':
        return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
      case 'NO-HIT':
        return 'bg-red-500/10 text-red-500 border-red-500/20';
      default:
        return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
    }
  };

  return (
    <Badge
      variant="outline"
      className={cn(
        'font-mono text-[10px] uppercase tracking-wider px-1.5 py-0 rounded-sm',
        getColors(level),
        className
      )}
    >
      {level.replace('-', ' ')}
    </Badge>
  );
}
