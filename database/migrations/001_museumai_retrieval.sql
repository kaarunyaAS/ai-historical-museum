-- MuseumAI additive migration
-- Inspected schema on 13 November 2026:
--   knowledge_chunks.embedding is already public.vector(768)
--   knowledge_chunks was empty
--   knowledge_documents already contained four Tipu Sultan rows (ids 1-4)
--   artifacts ART001-ART010 already existed
--
-- This script does not DROP tables, DELETE rows, or rewrite unrelated data.
-- Run it in the Supabase SQL Editor if the backend cannot open a direct
-- Postgres connection (SUPABASE_DB_URL is optional).

create extension if not exists vector;

alter table public.knowledge_chunks
  add column if not exists chunk_key text,
  add column if not exists section_id text,
  add column if not exists source_ids jsonb not null default '[]'::jsonb;

create unique index if not exists knowledge_chunks_chunk_key_unique
  on public.knowledge_chunks (chunk_key)
  where chunk_key is not null;

create index if not exists knowledge_chunks_document_idx
  on public.knowledge_chunks (document_id);

create index if not exists knowledge_documents_artifact_type_idx
  on public.knowledge_documents (artifact_id, document_type);

-- 768 dimensions are within the pgvector HNSW limit of 2000.
create index if not exists knowledge_chunks_embedding_hnsw
  on public.knowledge_chunks
  using hnsw (embedding vector_cosine_ops);

create or replace function public.match_knowledge_chunks(
  query_embedding vector(768),
  match_count integer,
  filter_artifact_ids text[] default null,
  similarity_threshold double precision default 0.5
)
returns table (
  chunk_id bigint,
  document_id bigint,
  artifact_id text,
  chunk_index integer,
  chunk_text text,
  section_id text,
  source_ids jsonb,
  similarity double precision
)
language sql
stable
as $$
  select
    c.id as chunk_id,
    c.document_id,
    d.artifact_id,
    c.chunk_index,
    c.chunk_text,
    c.section_id,
    c.source_ids,
    (1 - (c.embedding <=> query_embedding))::double precision as similarity
  from public.knowledge_chunks c
  join public.knowledge_documents d on d.id = c.document_id
  where c.embedding is not null
    and d.document_type = 'museumai_rag'
    and (
      filter_artifact_ids is null
      or cardinality(filter_artifact_ids) = 0
      or d.artifact_id = any (filter_artifact_ids)
    )
    and (1 - (c.embedding <=> query_embedding)) >= similarity_threshold
  order by c.embedding <=> query_embedding
  limit greatest(match_count, 1);
$$;

revoke all on function public.match_knowledge_chunks(vector, integer, text[], double precision) from public;
grant execute on function public.match_knowledge_chunks(vector, integer, text[], double precision) to service_role;
