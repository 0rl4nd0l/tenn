export const SCHEMA_STATEMENTS = [
  `
    CREATE TABLE IF NOT EXISTS tasks (
      id TEXT PRIMARY KEY,
      goal_id TEXT NOT NULL,
      parent_id TEXT,
      title TEXT NOT NULL,
      description TEXT NOT NULL,
      status TEXT NOT NULL,
      role TEXT NOT NULL,
      task_type TEXT NOT NULL,
      agent_mode TEXT NOT NULL,
      delegation_policy TEXT NOT NULL,
      locality TEXT NOT NULL,
      runtime_candidates TEXT NOT NULL,
      provider_candidates TEXT NOT NULL,
      preferred_runtime TEXT,
      preferred_provider TEXT,
      chosen_runtime TEXT,
      chosen_provider TEXT,
      chosen_model TEXT,
      owned_files TEXT NOT NULL,
      read_only_paths TEXT NOT NULL,
      verification_policy TEXT NOT NULL,
      token_budget TEXT NOT NULL,
      dependencies TEXT NOT NULL,
      attempts INTEGER NOT NULL,
      max_attempts INTEGER NOT NULL,
      routing_rationale TEXT,
      constraints TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
  `,
  `
    CREATE TABLE IF NOT EXISTS sessions (
      id TEXT PRIMARY KEY,
      task_id TEXT NOT NULL,
      runtime TEXT NOT NULL,
      provider TEXT NOT NULL,
      model TEXT NOT NULL,
      mode TEXT NOT NULL,
      local_or_cloud TEXT NOT NULL,
      native_stats_supported INTEGER NOT NULL,
      exact_usage_supported INTEGER NOT NULL,
      compaction_supported INTEGER NOT NULL,
      context_window INTEGER NOT NULL,
      max_output_tokens INTEGER NOT NULL,
      estimated_context_used INTEGER NOT NULL,
      native_context_used INTEGER,
      headroom REAL NOT NULL,
      quota_state TEXT NOT NULL,
      status TEXT NOT NULL,
      external_session_id TEXT,
      started_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
  `,
  `
    CREATE TABLE IF NOT EXISTS runs (
      id TEXT PRIMARY KEY,
      task_id TEXT NOT NULL,
      session_id TEXT,
      attempt INTEGER NOT NULL,
      status TEXT NOT NULL,
      started_at TEXT NOT NULL,
      ended_at TEXT,
      exit_code INTEGER,
      summary TEXT NOT NULL
    )
  `,
  `
    CREATE TABLE IF NOT EXISTS events (
      id TEXT PRIMARY KEY,
      entity_type TEXT NOT NULL,
      entity_id TEXT NOT NULL,
      event_type TEXT NOT NULL,
      payload TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
  `,
  `
    CREATE TABLE IF NOT EXISTS logs (
      id TEXT PRIMARY KEY,
      run_id TEXT NOT NULL,
      stream TEXT NOT NULL,
      message TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
  `,
  `
    CREATE TABLE IF NOT EXISTS janitor_results (
      id TEXT PRIMARY KEY,
      task_id TEXT NOT NULL,
      run_id TEXT,
      status TEXT NOT NULL,
      checks TEXT NOT NULL,
      diff_summary TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
  `,
  `
    CREATE TABLE IF NOT EXISTS reviews (
      id TEXT PRIMARY KEY,
      task_id TEXT NOT NULL,
      decision TEXT NOT NULL,
      reviewer TEXT NOT NULL,
      summary TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
  `,
  `
    CREATE TABLE IF NOT EXISTS ownership_locks (
      id TEXT PRIMARY KEY,
      task_id TEXT NOT NULL,
      path_glob TEXT NOT NULL,
      mode TEXT NOT NULL,
      status TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
  `,
  `
    CREATE TABLE IF NOT EXISTS worktrees (
      id TEXT PRIMARY KEY,
      task_id TEXT NOT NULL,
      branch_name TEXT NOT NULL,
      path TEXT NOT NULL,
      base_ref TEXT NOT NULL,
      status TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
  `,
  `
    CREATE TABLE IF NOT EXISTS capabilities (
      runtime TEXT PRIMARY KEY,
      provider TEXT NOT NULL,
      snapshot TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
  `,
  `
    CREATE TABLE IF NOT EXISTS conversation_messages (
      id TEXT PRIMARY KEY,
      goal_id TEXT NOT NULL,
      role TEXT NOT NULL,
      content TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
  `
];
