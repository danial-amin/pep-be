# Report Data Requirements

## Current Data Available

### RQE Scores
- **Current RQE**: 0.77 (77%)
- **Previous RQE**: 0.62 (62%)
- **Progress**: +15% improvement

### Validation Scores
- **Current Overall Validation**: 0.84 (84%)
- This represents the average cosine similarity between personas and interview transcripts

## Data Needed for Enhanced Reports

To create more detailed visualizations and clustering analysis, please provide:

### 1. RQE Score History (if available)
```json
{
  "rqe_scores": [
    {"cycle": 1, "rqe_score": 0.62, "timestamp": "2024-12-20"},
    {"cycle": 2, "rqe_score": 0.77, "timestamp": "2024-12-29"}
  ]
}
```

### 2. Individual Persona Validation Scores
For each persona, provide:
- Average similarity score
- Max similarity score
- Min similarity score
- Number of transcript matches
- Validation status (validated/pending)

### 3. Word Clustering Data (Optional)
If you want to cluster and map specific words:
- List of keywords/phrases to track
- Frequency of these words in personas vs transcripts
- Semantic similarity clusters
- Topic modeling results

### 4. Persona-Specific Metrics
For each persona:
- Demographics breakdown
- Technology usage patterns
- Interaction preferences
- Goals and frustrations alignment with transcripts

## Current Implementation

The system currently:
- ✅ Tracks RQE scores over cycles
- ✅ Calculates validation scores (cosine similarity)
- ✅ Shows progress from 0.62 to 0.77
- ✅ Displays overall validation at 0.84
- ✅ Visualizes persona-level validation scores

## Next Steps

1. **Load Default Personas**: Use the "Load Default Personas" button on the Personas page
2. **Measure Diversity**: Click "Measure Diversity" to calculate RQE scores
3. **Validate Personas**: Click "Validate" to calculate similarity scores
4. **View Reports**: Navigate to Reports page to see visualizations

## Data Format

The system expects data in the following format:

```json
{
  "persona_set_id": 1,
  "rqe_scores": [
    {"cycle": 1, "rqe_score": 0.62, "average_similarity": 0.38},
    {"cycle": 2, "rqe_score": 0.77, "average_similarity": 0.23}
  ],
  "validation_scores": [
    {
      "persona_id": 1,
      "persona_name": "Jameela Jamil",
      "average_similarity": 0.84,
      "max_similarity": 0.92,
      "min_similarity": 0.76,
      "validation_status": "validated"
    }
  ],
  "diversity_score": {
    "rqe_score": 0.77,
    "average_similarity": 0.23,
    "min_similarity": 0.15,
    "max_similarity": 0.35,
    "std_similarity": 0.08,
    "num_personas": 5
  }
}
```

## Word Clustering Feature (Future)

To enable word clustering and mapping:
1. Provide a list of keywords/phrases to track
2. System will extract these from persona descriptions and transcripts
3. Create similarity clusters
4. Visualize word frequency and semantic relationships

