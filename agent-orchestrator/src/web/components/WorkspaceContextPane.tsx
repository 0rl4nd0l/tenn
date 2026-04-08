import { ProjectSnapshot } from "../../shared/types";

interface WorkspaceContextPaneProps {
  snapshot: ProjectSnapshot | null;
}

export function WorkspaceContextPane({ snapshot }: WorkspaceContextPaneProps) {
  if (!snapshot) {
    return (
      <section className="panel workspace-panel">
        <div className="panel-header compact-header">
          <div>
            <p className="eyebrow">Repo Context</p>
            <h2>Strategist Grounding</h2>
          </div>
        </div>
        <p className="activity-copy">
          The strategist has not grounded itself in the repo yet. Ask a question or submit a goal to build a snapshot.
        </p>
      </section>
    );
  }

  return (
    <section className="panel workspace-panel">
      <div className="panel-header compact-header">
        <div>
          <p className="eyebrow">Repo Context</p>
          <h2>Strategist Grounding</h2>
        </div>
        <span className="badge neutral">{formatSnapshotTime(snapshot.generatedAt)}</span>
      </div>

      <div className="workspace-summary-grid">
        <div className="summary-card">
          <span>Active Root</span>
          <strong>{snapshot.activeRoot?.name ?? "unknown"}</strong>
          <p>{snapshot.activeRoot ? `${Math.round(snapshot.activeRoot.confidence * 100)}% confidence` : "no active root yet"}</p>
        </div>
        <div className="summary-card">
          <span>Working Tree</span>
          <strong>{snapshot.dirtyFiles.length > 0 ? `${snapshot.dirtyFiles.length} dirty` : "clean"}</strong>
          <p>{snapshot.dirtyFiles.length > 0 ? "Local changes exist in the active workspace." : "No dirty paths detected right now."}</p>
        </div>
      </div>

      <div className="workspace-section">
        <div className="summary-card">
          <span>Verification</span>
          <strong>{snapshot.verificationFreshness?.freshnessBand ?? "unknown"}</strong>
          <p>{snapshot.verificationFreshness?.summary ?? "no verification data yet"}</p>
        </div>
      </div>

      <div className="workspace-section">
        <h3>Project Roots</h3>
        <div className="root-list">
          {snapshot.projects.slice(0, 3).map((project) => (
            <div key={project.path} className="root-row">
              <div>
                <strong>{project.name}</strong>
                <p>{project.path}</p>
              </div>
              <span className="badge neutral">{project.kind}</span>
            </div>
          ))}
        </div>
        {snapshot.projects.length > 3 ? <p className="activity-copy detail-note">{snapshot.projects.length - 3} more roots available.</p> : null}
      </div>

      {snapshot.evidenceMatches.length > 0 ? (
        <div className="workspace-section">
          <h3>Latest Evidence</h3>
          <div className="workspace-chip-row">
          {snapshot.evidenceMatches.slice(0, 4).map((match) => (
            <span key={`${match.term}:${match.path}`} className="badge neutral">
              {match.term}: {match.path}
            </span>
          ))}
        </div>
          {snapshot.evidenceMatches.length > 4 ? (
            <p className="activity-copy detail-note">{snapshot.evidenceMatches.length - 4} more evidence matches hidden.</p>
          ) : null}
        </div>
      ) : null}

      {snapshot.workspaceLexicon?.length ? (
        <div className="workspace-section">
          <h3>Repo Lexicon</h3>
          <div className="workspace-chip-row">
            {snapshot.workspaceLexicon.slice(0, 8).map((entry) => (
              <span key={entry} className="badge neutral">
                {entry}
              </span>
            ))}
          </div>
          {snapshot.workspaceLexicon.length > 8 ? (
            <p className="activity-copy detail-note">{snapshot.workspaceLexicon.length - 8} more terms available.</p>
          ) : null}
        </div>
      ) : null}

      <div className="workspace-section">
        <h3>Dirty Paths</h3>
        {snapshot.dirtyFiles.length > 0 ? (
          <ul className="detail-list compact-list">
            {snapshot.dirtyFiles.slice(0, 4).map((filePath) => (
              <li key={filePath}>{filePath}</li>
            ))}
          </ul>
        ) : (
          <p className="activity-copy">Working tree looks clean.</p>
        )}
        {snapshot.dirtyFiles.length > 4 ? <p className="activity-copy detail-note">{snapshot.dirtyFiles.length - 4} more changed paths hidden.</p> : null}
      </div>
    </section>
  );
}

function formatSnapshotTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit"
  }).format(date);
}
