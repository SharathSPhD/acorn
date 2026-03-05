CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE problems (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    description TEXT,
    problem_class TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','assembling','active','complete','failed')),
    source TEXT NOT NULL DEFAULT 'user',
    solution_url TEXT,
    data_manifest JSONB DEFAULT '{}',
    input_manifest JSONB DEFAULT '{}',
    output_format TEXT,
    worktree_path TEXT,
    idempotency_key TEXT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    problem_id UUID NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    task_type TEXT NOT NULL CHECK (task_type IN ('ingest','analyse','model','synthesise','validate')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','claimed','complete','failed')),
    assigned_to TEXT,
    blocked_by UUID[] DEFAULT '{}',
    result JSONB,
    reasoning_steps INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE mailbox (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    problem_id UUID NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    from_agent TEXT NOT NULL,
    to_agent TEXT NOT NULL,
    subject TEXT,
    body TEXT NOT NULL,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE episodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    problem_id UUID REFERENCES problems(id) ON DELETE SET NULL,
    agent_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),
    importance FLOAT DEFAULT 0.5,
    retrieved_count INTEGER DEFAULT 0,
    last_retrieved_at TIMESTAMPTZ,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON episodes USING hnsw (embedding vector_cosine_ops);

CREATE TABLE kernels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    version TEXT,
    category TEXT NOT NULL CHECK (category IN ('etl','analysis','ml','ui','infra','sales','pricing','marketing','supply_chain','customer','finance','operations','human_capital','product','general')),
    status TEXT NOT NULL DEFAULT 'probationary' CHECK (status IN ('probationary','permanent','deprecated')),
    description TEXT NOT NULL,
    trigger_keywords TEXT[] NOT NULL DEFAULT '{}',
    implementation TEXT,
    test_suite TEXT,
    benchmark TEXT,
    use_count INTEGER NOT NULL DEFAULT 0,
    embedding vector(768),
    verified_on_problems UUID[] DEFAULT '{}',
    filesystem_path TEXT,
    deprecated_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    promoted_at TIMESTAMPTZ,
    deprecated_at TIMESTAMPTZ
);
CREATE INDEX ON kernels USING hnsw (embedding vector_cosine_ops);

CREATE TABLE agent_telemetry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    problem_id UUID REFERENCES problems(id) ON DELETE SET NULL,
    agent_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    tool_name TEXT,
    tool_input JSONB,
    tool_response JSONB,
    duration_ms INTEGER,
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    model_used TEXT,
    escalated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON agent_telemetry (agent_id, created_at DESC);
CREATE INDEX ON agent_telemetry (problem_id, created_at DESC);

CREATE TABLE judge_verdicts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    problem_id UUID REFERENCES problems(id) ON DELETE CASCADE,
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    agent_id TEXT,
    verdict TEXT NOT NULL CHECK (verdict IN ('pass','fail')),
    reasoning TEXT,
    checks JSONB NOT NULL DEFAULT '{}',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON judge_verdicts (task_id, created_at DESC);
CREATE INDEX ON judge_verdicts (problem_id, created_at DESC);

CREATE TABLE IF NOT EXISTS reasoning_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    problem_id UUID NOT NULL REFERENCES problems(id),
    agent_id TEXT NOT NULL,
    step_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    confidence FLOAT,
    sources JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_reasoning_steps_problem ON reasoning_steps(problem_id);

CREATE TABLE IF NOT EXISTS research_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_hash TEXT NOT NULL,
    query_text TEXT NOT NULL,
    results JSONB DEFAULT '[]',
    source_urls TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_research_cache_hash ON research_cache(query_hash);

CREATE TABLE IF NOT EXISTS domain_knowledge (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),
    source_url TEXT,
    source_type TEXT DEFAULT 'web' CHECK (source_type IN ('web','paper','hf_model','manual','episode')),
    chunk_index INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON domain_knowledge USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON domain_knowledge (domain, created_at DESC);
