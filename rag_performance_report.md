# MuseumAI RAG Performance Report

**Evaluation date:** 2026-11-14<br>
**System evaluated:** MuseumAI historical knowledge retrieval through Supabase PostgreSQL, pgvector, and `match_knowledge_chunks`

## Executive summary

The live Supabase retrieval path was exercised with five artifact-scoped test queries using Gemini query embeddings. All five RPC calls returned chunks. The eligible retrieval corpus contained 32 chunks across 10 `museumai_rag` documents. The five queries returned 17 chunks in total, with observed pgvector cosine-similarity scores from **0.853343** to **0.906483** and a mean of **0.882543**.

These are similarity scores, not relevance judgments. The repository and inspected database did not provide a labeled query-to-relevant-chunk benchmark or reference answers. Therefore **Precision@5, Recall@5, MRR, faithfulness, and answer relevance cannot be calculated from the available ground truth**. No accuracy percentages are inferred from the similarity scores.

## Evaluation methodology

1. Inspected the retrieval implementation, migration, artifact catalog, and existing evaluation artifacts. The available evaluation JSON files contain project/schema checks, not labeled queries, relevant chunk IDs, or reference answers.
2. Read database counts through Supabase's REST API without modifying records:
   - 10 documents with `document_type = 'museumai_rag'`.
   - 32 chunks associated with those eligible documents, out of 35 rows in `knowledge_chunks`.
   - The RPC itself filters to `museumai_rag` documents.
3. Issued five manually selected historical questions, each scoped to its named artifact. Generated real query embeddings with `gemini-embedding-001` and called the existing `RAGService.retrieve` path, which invokes `match_knowledge_chunks`.
4. Used `top_k = 5` and the retrieval path's explicit similarity threshold of `0.15`. The artifact filter was set to the expected artifact ID for each query. Similarity values below are those returned by the database function.
5. Summarized the returned cosine-similarity values. No answers were generated or graded because there are no reference answers or faithfulness annotations.

The test queries were exploratory probes, not a labeled benchmark. Their artifact scope is not treated as chunk-level ground truth.

## Results

### Performance summary

| Measure | Result | Interpretation |
|---|---:|---|
| Test queries | 5 | Five artifact-scoped retrieval calls completed |
| Eligible documents | 10 | `document_type = 'museumai_rag'` |
| Eligible chunks | 32 | Associated with the eligible documents |
| Chunks returned | 17 | Across the five queries; 3–4 returned per query |
| Precision@5 | Not calculable | No judged relevant chunk IDs per query |
| Recall@5 | Not calculable | No complete set of relevant chunks per query |
| MRR | Not calculable | No relevance labels to identify the first relevant result |
| Mean similarity of returned chunks | 0.882543 | Arithmetic mean of all 17 RPC similarity scores |
| Median similarity of returned chunks | 0.883788 | Median of all 17 RPC similarity scores |
| Similarity range | 0.853343–0.906483 | Minimum and maximum among returned chunks |
| Faithfulness | Not evaluated | No generated answers were compared with reference facts |
| Answer relevance | Not evaluated | No reference answers or answer-level judgments available |

### Query-level retrieval results

| Test query | Artifact filter | Chunks returned | Similarity scores, rank order |
|---|---|---:|---|
| What do the ring of flames and Shiva's dance represent in the Nataraja bronze? | `ART001` | 4 | 0.898112, 0.887108, 0.876137, 0.862536 |
| What material was the Dancing Girl of Mohenjo-daro made from, and where was it found? | `ART002` | 4 | 0.906483, 0.891278, 0.890647, 0.870699 |
| What do the lions on Ashoka's Lion Capital symbolize and where is it from? | `ART003` | 3 | 0.901383, 0.883788, 0.866100 |
| How did the Konark temple wheel function as a sundial? | `ART004` | 3 | 0.887755, 0.872873, 0.853343 |
| When and why was Tipu Sultan's sword taken from his palace? | `ART008` | 3 | 0.903052, 0.876463, 0.875472 |

The scoped result count is below five where the artifact has only three eligible chunks. Across the eligible corpus, artifact chunk counts were: `ART001` 4, `ART002` 4, `ART003` 3, `ART004` 3, `ART005` 3, `ART006` 3, `ART007` 3, `ART008` 3, `ART009` 3, and `ART010` 3.

### Retrieved chunk examples

These examples show retrieval output and similarity only; they are not independently judged as relevant or correct.

| Query | Rank | Retrieved chunk | Similarity | Retrieved content example |
|---|---:|---|---:|---|
| Nataraja symbolism | 1 | `museumai-ART001-iconography-000` (`iconography`) | 0.898112 | Describes Shiva dancing with multiple arms, a ring of flames, and a raised left leg or balanced posture. |
| Dancing Girl material and provenance | 1 | `museumai-ART002-overview-000` (`overview`) | 0.906483 | Identifies the figure as a small bronze from the mature Indus Valley civilization and notes its discovery during excavations at Mohenjo-daro in the 1920s. |
| Lion Capital symbolism | 1 | `museumai-ART003-symbolism-000` (`symbolism`) | 0.901383 | Says the lions are often read as symbols of courage, sovereignty, and the message of dharma; also mentions the chakra. |
| Konark wheel sundial | 1 | `museumai-ART004-overview-000` (`overview`) | 0.887755 | Returns the overview of the stone wheels and the temple's chariot-like plan. |
| Tipu Sultan's sword history | 1 | `museumai-ART008-overview-000` (`overview`) | 0.903052 | Connects the sword with late-18th-century Mysore, Tipu Sultan, and the palace at Seringapatam. |

## Limitations

- There are no human-labeled relevant chunk IDs or graded relevance judgments, so ranked retrieval quality metrics cannot be computed without introducing new ground truth.
- The artifact catalog provides historical source sections, but not a mapping from these five questions to all relevant database chunks. Treating every chunk under the requested artifact as relevant would be an unvalidated proxy and could misstate precision or recall.
- The 17 observed similarity values are from a small, manually selected, artifact-scoped sample. They do not establish overall retrieval quality, coverage across query types, or behavior without artifact filters.
- Cosine similarity is embedding-space proximity, not a calibrated probability or a measure of factual correctness. A high score alone does not demonstrate that a retrieved chunk answers the question.
- Faithfulness and answer relevance are answer-generation measures. This run tested retrieval only; the available files provide no reference answers or answer-level labels.
- Three rows in `knowledge_chunks` were not associated with the ten eligible `museumai_rag` documents and are excluded by the retrieval function's document-type filter.

## Recommendations

1. Create a versioned evaluation set with representative queries, expected artifact scope, and human-judged relevant chunk IDs (including all relevant chunks, not only one preferred result). Use independent review for ambiguous historical questions.
2. Compute Precision@5, Recall@5, and MRR from those judgments; specify how fewer than five returned chunks are handled and report per-query results alongside aggregate values.
3. Add reference answers or claim-level evidence annotations to evaluate answer relevance and faithfulness. Keep retrieval and generation scores separate.
4. Expand the test set to include unscoped, multi-artifact, ambiguous, multilingual, and no-evidence questions, in addition to artifact-specific factual questions.
5. Evaluate thresholds and result counts against the labeled set. Do not select a threshold based solely on the high similarity values in this small sample.
6. Preserve query text, embedding model/version, artifact filter, threshold, retrieved chunk IDs, ranks, and judgments with each benchmark run so results are reproducible.
