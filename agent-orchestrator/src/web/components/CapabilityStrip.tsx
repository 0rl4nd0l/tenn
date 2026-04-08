import { useEffect, useState } from "react";
import { ProviderCapabilitySnapshot } from "../../shared/types";

interface CapabilityStripProps {
  capabilities: ProviderCapabilitySnapshot[];
}

export function CapabilityStrip({ capabilities }: CapabilityStripProps) {
  const readyCount = capabilities.filter(
    (capability) => capability.installStatus === "installed" && capability.authStatus === "authenticated"
  ).length;
  const needsAttention = capabilities.length - readyCount;
  const degradedRuntimes = capabilities
    .filter((capability) => capability.installStatus !== "installed" || capability.authStatus !== "authenticated")
    .slice(0, 2);
  const [expanded, setExpanded] = useState(needsAttention > 0);

  useEffect(() => {
    if (needsAttention > 0) {
      setExpanded(true);
    }
  }, [needsAttention]);

  return (
    <details className="panel capability-panel" open={expanded} onToggle={(event) => setExpanded(event.currentTarget.open)}>
      <summary className="fold-header">
        <span className="fold-copy">
          <span className="eyebrow">Runtimes</span>
          <strong className="fold-title">Runtime Health</strong>
          <span className="activity-copy">Expand to inspect auth, locality, and context limits.</span>
        </span>
        <span className="fold-meta">
          <span className="badge neutral">{readyCount} ready</span>
          {needsAttention > 0 ? <span className="badge warn">{needsAttention} need setup</span> : null}
        </span>
      </summary>

      {degradedRuntimes.length > 0 ? (
        <div className="workspace-chip-row runtime-alert-row">
          {degradedRuntimes.map((capability) => (
            <span key={capability.runtime} className="badge warn">
              {capability.runtime}: {capability.installStatus === "installed" ? capability.authStatus : capability.installStatus}
            </span>
          ))}
        </div>
      ) : null}

      <div className="runtime-list">
        {capabilities.map((capability) => {
          const healthy = capability.installStatus === "installed" && capability.authStatus === "authenticated";
          return (
            <article key={capability.runtime} className="runtime-row">
              <div>
                <strong>{capability.title}</strong>
                <p>
                  {capability.runtime} · {capability.costTier} · {capability.maxContextWindow.toLocaleString()} ctx
                </p>
              </div>
              <div className="runtime-meta">
                <span className={`badge ${healthy ? "ok" : "warn"}`}>
                  {capability.installStatus === "installed" ? capability.authStatus : capability.installStatus}
                </span>
                <span className="badge neutral">{capability.supportsCloud ? "cloud/local" : "local"}</span>
              </div>
            </article>
          );
        })}
      </div>
    </details>
  );
}
