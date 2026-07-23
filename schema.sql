-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create table for book_chunks with id TEXT and matching column names
CREATE TABLE IF NOT EXISTS book_chunks (
    id TEXT PRIMARY KEY, -- String chunk_id (e.g. rich_dad_poor_dad_ch1_c0)
    book_id TEXT NOT NULL,
    chapter_number INT,
    chapter_index INT,
    chunk_index INT,
    content TEXT NOT NULL,
    summary TEXT,
    embedding vector(384), -- 384 dims for paraphrase-multilingual-MiniLM-L12-v2
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Create HNSW Index for fast vector similarity search
CREATE INDEX IF NOT EXISTS idx_book_chunks_embedding 
ON book_chunks 
USING hnsw (embedding vector_cosine_ops);

-- 4. Index on book_id for fast filtering
CREATE INDEX IF NOT EXISTS idx_book_chunks_book_id 
ON book_chunks (book_id);

-- 5. RPC function for matching book chunks
CREATE OR REPLACE FUNCTION match_book_chunks (
  query_embedding vector(384),
  filter_book_id TEXT,
  match_count INT DEFAULT 6
)
RETURNS TABLE (
  id TEXT,
  book_id TEXT,
  chapter_number INT,
  chunk_index INT,
  content TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    book_chunks.id,
    book_chunks.book_id,
    book_chunks.chapter_number,
    book_chunks.chunk_index,
    book_chunks.content,
    1 - (book_chunks.embedding <=> query_embedding) AS similarity
  FROM book_chunks
  WHERE book_chunks.book_id = filter_book_id
  ORDER BY book_chunks.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- 6. Table for chapter summaries
CREATE TABLE IF NOT EXISTS book_chapter_summaries (
    id TEXT PRIMARY KEY, -- e.g. "1Z1qhCE0N3UAee2nLbeY_ch1"
    book_id TEXT NOT NULL,
    chapter_number INT NOT NULL,
    chapter_title TEXT DEFAULT '',
    summary TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_summaries_book_id 
ON book_chapter_summaries (book_id);

-- 7. Table for book metadata (optional/backup)
CREATE TABLE IF NOT EXISTS books (
    id TEXT PRIMARY KEY, -- e.g. "1Z1qhCE0N3UAee2nLbeY"
    title TEXT,
    author TEXT,
    description TEXT,
    cover_url TEXT,
    audio_link TEXT,
    genre TEXT,
    genres JSONB,
    rating FLOAT,
    pages INT,
    duration TEXT,
    chapters JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
