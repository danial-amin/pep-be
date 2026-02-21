# Persona Evaluation Plan — Beyond Cosine Similarity

A comprehensive evaluation framework for PEP (Persona Extraction Pipeline) that supplements and extends the current cosine-similarity-based metrics with richer, more interpretable dimensions.

---

## 1. Current State (What We Have)

| Dimension | Method | Output |
|-----------|--------|--------|
| **Diversity** | RQE via pairwise cosine similarity of persona embeddings | 0–1 score (higher = more diverse) |
| **Validation** | Persona text vs. interview chunks (cosine similarity) | avg/min/max similarity per persona |
| **Attribute verification** | Per-attribute reverse RAG + direct/indirect similarity | verified/flagged per attribute |

**Limitations of cosine similarity alone:**
- Semantic similarity ≠ factual grounding
- No claim-level verification
- No coverage of source topics
- No human-likeness or coherence assessment
- No explicit fairness or stereotype checks

---

## 2. Evaluation Dimensions (Proposed)

### 2.1 Groundedness (Source Attribution)

**Goal:** Ensure persona attributes are factually supported by source data, not just semantically similar.

| Metric | Description | Method | Output |
|--------|-------------|--------|--------|
| **Claim extraction + NLI** | Extract atomic claims from each persona attribute; verify each against source chunks | Use NLI model (e.g., DeBERTa-NLI) to check entailment/contradiction | % of claims entailed by source |
| **Citation coverage** | For each attribute, count how many source chunks support it | RAG retrieval + NLI filtering | Support count per attribute |
| **Hallucination rate** | Claims that contradict or are unsupported by source | NLI: contradiction or neutral | % unsupported/contradicted |

**Implementation sketch:**
```
For each persona attribute:
  1. Extract claims (e.g., via LLM or rule-based)
  2. Retrieve top-k source chunks per claim
  3. Run NLI: entailment / neutral / contradiction
  4. Aggregate: grounded_ratio = entailed / total
```

---

### 2.2 Coverage (Source Representation)

**Goal:** Measure how well the persona set represents the breadth of the source data.

| Metric | Description | Method | Output |
|--------|-------------|--------|--------|
| **Topic coverage** | Overlap between topics in personas vs. topics in interviews | Topic modeling (LDA/NMF) or keyword extraction on both; compute Jaccard or % overlap | Coverage score 0–1 |
| **Segment coverage** | Whether different interview segments (e.g., by participant, theme) are represented | Cluster interviews; map personas to clusters; count unique clusters covered | # segments covered, coverage % |
| **Demographic coverage** | Spread of demographics in personas vs. source | Extract demographics from both; compare distributions (e.g., KL divergence or histogram overlap) | Distribution similarity score |

**Implementation sketch:**
```
1. Extract topics/key themes from interviews (LDA or keyword extraction)
2. Extract topics from persona attributes
3. Coverage = |topics_in_personas ∩ topics_in_source| / |topics_in_source|
4. Optional: weight by importance (e.g., topic frequency in source)
```

---

### 2.3 Diversity (Beyond Pairwise Similarity)

**Goal:** Capture diversity along multiple axes, not just embedding similarity.

| Metric | Description | Method | Output |
|--------|-------------|--------|--------|
| **RQE (existing)** | Pairwise dissimilarity in embedding space | Keep current implementation | 0–1 score |
| **Demographic diversity** | Spread across age, gender, occupation, location | Categorical entropy or Simpson index per dimension | Per-dimension diversity scores |
| **Attitudinal diversity** | Spread of goals, frustrations, motivations | Embed goals/frustrations; compute pairwise distances; aggregate | Attitudinal spread score |
| **Cluster separation** | Are personas in distinct clusters? | K-means or hierarchical clustering on persona embeddings; silhouette score | Silhouette score |
| **Attribute uniqueness** | How unique is each persona’s attribute set? | Jaccard distance between attribute sets; avg pairwise uniqueness | Uniqueness score |

**Implementation sketch:**
```
Demographic diversity:
  - For each dimension (age, gender, occupation): compute entropy
  - Aggregate: weighted average of entropies

Attitudinal diversity:
  - Embed goals + frustrations per persona
  - Pairwise cosine distance matrix
  - Use min/mean distance as spread indicator
```

---

### 2.4 Internal Coherence

**Goal:** Ensure persona attributes are logically consistent with each other.

| Metric | Description | Method | Output |
|--------|-------------|--------|--------|
| **Goals–frustrations alignment** | Goals and frustrations should be related (e.g., frustration blocks goal) | LLM-as-judge or NLI: "Does this frustration relate to this goal?" | Alignment score per persona |
| **Demographic–background consistency** | Background should match stated demographics | LLM-as-judge: "Is the background consistent with demographics?" | Consistency score |
| **Contradiction detection** | No attribute contradicts another | NLI pairwise between attributes | Contradiction count |

**Implementation sketch:**
```
LLM-as-judge prompt:
  "Given persona: [demographics, background, goals, frustrations]
   Rate 1-5: How internally consistent is this persona? (1=contradictory, 5=fully coherent)"
```

---

### 2.5 Simulation Consistency (In-Character Behavior)

**Goal:** Ensure simulated responses stay in character and align with persona attributes.

| Metric | Description | Method | Output |
|--------|-------------|--------|--------|
| **Persona adherence** | Does each simulation message align with the persona? | LLM-as-judge: "Does this response match the persona?" | Per-message score |
| **Attribute reference** | Do responses reference persona attributes (goals, frustrations)? | Keyword/embedding overlap between response and attributes | Reference rate |
| **Drift detection** | Do later turns drift from persona? | Compare early vs. late turn adherence scores | Drift score |

**Implementation sketch:**
```
For each simulation message:
  1. Concatenate persona attributes
  2. LLM-as-judge: "Given persona [X], rate 1-5 how well this response [Y] fits"
  3. Aggregate: mean adherence per persona, per simulation
```

---

### 2.6 Realism & Human-Likeness

**Goal:** Assess whether personas and their responses feel like real people.

| Metric | Description | Method | Output |
|--------|-------------|--------|--------|
| **Turing-style rating** | Would a human think this is a real person? | Human or LLM-as-judge survey | Mean rating 1–5 |
| **Stereotype check** | Avoid obvious stereotypes (e.g., gender–occupation) | LLM-as-judge: "Does this persona rely on stereotypes?" | Stereotype flag |
| **Plausibility** | Are goals/frustrations plausible for the stated demographics? | LLM-as-judge | Plausibility score |

**Implementation sketch:**
```
LLM-as-judge:
  "Rate 1-5: How plausible is this persona as a real person?
   Consider: demographics, goals, frustrations, background."
```

---

### 2.7 Representational Fairness

**Goal:** Avoid over/under-representation and harmful stereotypes.

| Metric | Description | Method | Output |
|--------|-------------|--------|--------|
| **Demographic balance** | Distribution of personas vs. source | Compare persona demographic distribution to source | Balance score |
| **Stereotype detection** | Flag personas that reinforce stereotypes | LLM-as-judge or stereotype lexicon | Flagged personas |
| **Minority representation** | Are minority views in source represented? | Compare persona attitudes to source attitude distribution | Representation score |

---

## 3. Evaluation Workflow

### Phase 1: Persona-Level (Static)

Run when personas are generated or updated:

1. **Groundedness** — Claim extraction + NLI
2. **Coverage** — Topic/segment overlap
3. **Diversity** — RQE + demographic + attitudinal
4. **Internal coherence** — LLM-as-judge
5. **Realism** — LLM-as-judge plausibility
6. **Fairness** — Stereotype check, demographic balance

### Phase 2: Simulation-Level (Dynamic)

Run when simulations complete:

1. **Persona adherence** — Per-message LLM-as-judge
2. **Attribute reference** — Overlap analysis
3. **Drift detection** — Early vs. late turn comparison

### Phase 3: Human Evaluation (Optional, Periodic)

1. Sample personas and simulation transcripts
2. Human raters score: groundedness, coherence, realism
3. Use for calibration and validation of automated metrics

---

## 4. Metric Aggregation & Reporting

### Per-Persona Scorecard

| Dimension | Score | Details |
|-----------|-------|---------|
| Groundedness | 0–1 | % claims entailed |
| Coverage contribution | 0–1 | Topics this persona adds |
| Diversity contribution | 0–1 | How distinct from others |
| Coherence | 1–5 | Internal consistency |
| Realism | 1–5 | Plausibility |
| Fairness | Pass/Fail | Stereotype check |

### Per-Persona-Set Summary

| Dimension | Aggregate | Method |
|-----------|-----------|--------|
| Groundedness | Mean per persona | Mean of per-persona groundedness |
| Coverage | Set-level | Topics covered by any persona / total topics |
| Diversity | RQE + attitudinal | Existing RQE + new attitudinal spread |
| Coherence | Mean per persona | Mean of per-persona coherence |
| Realism | Mean per persona | Mean of per-persona realism |
| Fairness | Worst-case | Any persona flagged? |

### Per-Simulation Summary

| Dimension | Aggregate | Method |
|-----------|-----------|--------|
| Adherence | Mean per message | Mean LLM-as-judge score |
| Drift | Early vs. late | Difference in adherence by turn |

---

## 5. Implementation Priority

| Priority | Dimension | Effort | Impact |
|----------|-----------|--------|--------|
| **P0** | Groundedness (NLI) | Medium | High — addresses main weakness of cosine |
| **P0** | Coverage | Medium | High — ensures source representation |
| **P1** | Internal coherence (LLM-as-judge) | Low | Medium |
| **P1** | Simulation adherence (LLM-as-judge) | Low | Medium |
| **P2** | Demographic/attitudinal diversity | Low | Medium |
| **P2** | Realism (LLM-as-judge) | Low | Medium |
| **P3** | Fairness / stereotype check | Low | High for ethics |
| **P3** | Drift detection | Low | Lower priority |

---

## 6. Dependencies & Tools

| Dimension | Suggested Tools |
|-----------|-----------------|
| NLI (groundedness) | `transformers` + `microsoft/deberta-v3-base-mnli` or `facebook/bart-large-mnli` |
| Topic extraction | `scikit-learn` LDA/NMF, or `keybert` |
| LLM-as-judge | Existing `llm_service` (OpenAI) with structured prompts |
| Demographics | Rule-based extraction or LLM extraction from persona_data |

---

## 7. Example Report Output

```json
{
  "persona_set_id": 14,
  "evaluation_timestamp": "2026-02-21T12:00:00Z",
  "summary": {
    "overall_groundedness": 0.82,
    "topic_coverage": 0.71,
    "diversity_rqe": 0.77,
    "diversity_attitudinal": 0.68,
    "mean_coherence": 4.2,
    "mean_realism": 4.0,
    "fairness_flags": 0
  },
  "per_persona": [
    {
      "persona_id": 90,
      "name": "Alpha_Seeker_0x",
      "groundedness": 0.85,
      "coverage_contribution": 0.22,
      "coherence": 4,
      "realism": 4,
      "fairness_flag": false,
      "attribute_details": {
        "background": {"entailed": 0.9, "claims_checked": 5},
        "goals": {"entailed": 0.8, "claims_checked": 5},
        "frustrations": {"entailed": 0.85, "claims_checked": 5}
      }
    }
  ],
  "simulation_metrics": {
    "mean_adherence": 4.1,
    "drift_score": 0.2
  }
}
```

---

## 8. Next Steps

1. **Design NLI pipeline** — Claim extraction + entailment checks for groundedness.
2. **Add topic extraction** — LDA or keyword-based coverage.
3. **Implement LLM-as-judge prompts** — Coherence, realism, adherence.
4. **Extend analytics service** — New endpoints and data models for these metrics.
5. **Update reports UI** — Display new dimensions alongside existing RQE/validation.
