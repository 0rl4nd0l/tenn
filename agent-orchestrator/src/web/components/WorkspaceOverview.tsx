import { ProjectSnapshot } from "../../shared/types";

interface WorkspaceOverviewProps {
  snapshot: ProjectSnapshot | null;
}

export function WorkspaceOverview({ snapshot }: WorkspaceOverviewProps) {
  if (!snapshot) {
    return (
      <section className="panel workspace-panel empty-state">
        <p>Workspace intelligence is still loading.</p>
      </section>
    );
  }

  return (
    <section className="panel workspace-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Workspace</p>
          <h2>Repo Intelligence</h2>
        </div>
        <span className="badge neutral">{snapshot.projects.length} detected roots</span>
      </div>

      <p className="workspace-copy">
        {snapshot.projects[0]?.summary ?? "No active runtime summary was detected from workspace docs."}
      </p>

      <div className="workspace-grid">
        {snapshot.projects.map((project) => (
          <article key={`${project.path}-${project.name}`} className="workspace-card">
            <div className="workspace-card-top">
              <strong>{project.name}</strong>
              <span className="badge neutral">{project.kind}</span>
            </div>
            <p>{project.summary}</p>
            <ul className="detail-list">
              <li>Path: {project.path}</li>
              <li>Key files: {project.keyFiles.slice(0, 3).join(", ")}</li>
            </ul>
          </article>
        ))}
      </div>

      <div className="workspace-meta">
        <div className="workspace-meta-card">
          <span>Authenticated runtimes</span>
          <strong>{snapshot.operationalHealth.authenticatedRuntimes.join(", ") || "none"}</strong>
        </div>
        <div className="workspace-meta-card">
          <span>Degraded runtimes</span>
          <strong>{snapshot.operationalHealth.degradedRuntimes.join(", ") || "none"}</strong>
        </div>
        <div className="workspace-meta-card">
          <span>Dirty files</span>
          <strong>{snapshot.dirtyFiles.length}</strong>
        </div>
      </div>
    </section>
  );
}
