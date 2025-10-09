# Getting Started with SBIR CET Classification

## Current Status

Your SBIR CET classification system is operational with:
- **997 awards** classified across **20 CET technology areas**
- **$742M** in total award funding analyzed
- Data from **5 major agencies** (DoD, HHS, NSF, DoE, EPA)

## Quick Commands

### View Summary Statistics
```bash
python -c "
import pandas as pd
awards = pd.read_parquet('data/processed/awards.parquet')
assessments = pd.read_parquet('data/processed/assessments.parquet')

print(f'Awards: {len(awards):,}')
print(f'Total Funding: \${awards[\"award_amount\"].sum()/1e6:.1f}M')
print(f'\\nTop 5 CET Areas:')
print(assessments['primary_cet_id'].value_counts().head())
"
```

### Explore Specific CET Areas
```bash
# View Artificial Intelligence awards
python -c "
import pandas as pd
assessments = pd.read_parquet('data/processed/assessments.parquet')
ai_awards = assessments[assessments['primary_cet_id'] == 'artificial_intelligence']
print(f'AI Awards: {len(ai_awards)}')
print(f'Score Distribution:')
print(ai_awards['classification'].value_counts())
"
```

### CLI Commands

```bash
# View portfolio summary
python -m sbir_cet_classifier.cli.app summary --fiscal-year-start 2023 --fiscal-year-end 2025

# List awards with filters
python -m sbir_cet_classifier.cli.app awards list \
  --fiscal-year-start 2023 --fiscal-year-end 2025 \
  --cet-areas artificial_intelligence \
  --page 1

# Export filtered data
python -m sbir_cet_classifier.cli.app export \
  --fiscal-year-start 2023 --fiscal-year-end 2025 \
  --format csv \
  --output-file ai_awards.csv
```

### API Server

```bash
# Start the API server
uvicorn sbir_cet_classifier.api.router:router --reload --port 8000

# Test endpoints
curl http://localhost:8000/summary?fiscal_year_start=2023&fiscal_year_end=2025
curl http://localhost:8000/awards?fiscal_year_start=2023&fiscal_year_end=2025&page=1
```

## Common Queries

### Find High-Value Awards in Specific CET Areas
```python
import pandas as pd

awards = pd.read_parquet('data/processed/awards.parquet')
assessments = pd.read_parquet('data/processed/assessments.parquet')

# Merge data
merged = awards.merge(assessments, on='award_id')

# High-value AI awards
ai_high_value = merged[
    (merged['primary_cet_id'] == 'artificial_intelligence') &
    (merged['award_amount'] > 1000000) &
    (merged['classification'] == 'High')
]

print(f"High-value AI awards: {len(ai_high_value)}")
print(f"Total funding: ${ai_high_value['award_amount'].sum()/1e6:.1f}M")
```

### Agency Distribution Analysis
```python
import pandas as pd

awards = pd.read_parquet('data/processed/awards.parquet')
assessments = pd.read_parquet('data/processed/assessments.parquet')

merged = awards.merge(assessments, on='award_id')

# Agency breakdown by CET area
agency_cet = merged.groupby(['agency', 'primary_cet_id']).agg({
    'award_id': 'count',
    'award_amount': 'sum'
}).round(2)

print(agency_cet.head(10))
```

## Data Files Location

- **Awards**: `data/processed/awards.parquet`
- **Assessments**: `data/processed/assessments.parquet`
- **Taxonomy**: `data/processed/taxonomy.parquet`

## Next Steps

1. **Explore the data** using the commands above
2. **Run your own analysis** with pandas/SQL queries
3. **Process new data** by running `python ingest_awards.py`
4. **Set up automated workflows** using the CLI commands
5. **Build custom reports** using the API endpoints

For detailed documentation, see:
- [README.md](README.md) - Full project overview
- [TESTING.md](TESTING.md) - Testing and development
- [specs/001-i-want-to/](specs/001-i-want-to/) - Technical specifications
taxonomy = pd.read_parquet('data/processed/taxonomy.parquet')

# Merge data
merged = awards.merge(assessments, on='award_id')
merged_with_tax = merged.merge(taxonomy, left_on='primary_cet_id', right_on='cet_id')

# Show summary by CET
summary = merged_with_tax.groupby('name').agg({
    'award_id': 'count',
    'award_amount': 'sum',
    'score': 'mean'
}).round(2)
summary.columns = ['Awards', 'Total_Amount', 'Avg_Score']
summary = summary.sort_values('Awards', ascending=False)

print(summary.to_string())
"
```

### Filter by Agency
```bash
python -c "
import sys
sys.path.insert(0, 'src')
import pandas as pd

awards = pd.read_parquet('data/processed/awards.parquet')
assessments = pd.read_parquet('data/processed/assessments.parquet')
taxonomy = pd.read_parquet('data/processed/taxonomy.parquet')

# Filter by agency
agency = 'National Science Foundation'
filtered = awards[awards['agency'] == agency]
merged = filtered.merge(assessments, on='award_id')

print(f'\\n{agency} Awards by CET:')
cet_counts = merged['primary_cet_id'].value_counts()
for cet_id, count in cet_counts.head(10).items():
    cet_name = taxonomy[taxonomy['cet_id'] == cet_id]['name'].iloc[0]
    print(f'  {cet_name:40s} {count:4d} awards')
"
```

### Explore Specific CET Area
```bash
python -c "
import sys
sys.path.insert(0, 'src')
import pandas as pd

awards = pd.read_parquet('data/processed/awards.parquet')
assessments = pd.read_parquet('data/processed/assessments.parquet')

# Filter by CET area
cet_area = 'quantum_computing'
filtered = assessments[assessments['primary_cet_id'] == cet_area]
merged = filtered.merge(awards, on='award_id')

print(f'\\nQuantum Computing Awards ({len(merged)} total):')
print(merged[['award_id', 'title', 'agency', 'award_amount', 'score']].head(10).to_string(index=False))
"
```

## 📁 Data Files

- **CET Taxonomy**: `data/taxonomy/cet_taxonomy_v1.csv` (20 technology areas)
- **Processed Awards**: `data/processed/awards.parquet` (997 awards)
- **Classifications**: `data/processed/assessments.parquet` (997 assessments)
- **Source Data**: `award_data-3.csv` (original SBIR data)

## 🔄 Re-running Classification

To process more data or update classifications:

```bash
# Edit ingest_awards.py to change nrows parameter (currently 1000)
# Then run:
python ingest_awards.py
```

## 📝 Classification Method

Currently using **keyword-based classification** with the following approach:
- Awards are matched against CET-specific keyword lists
- Scores are calculated based on keyword frequency
- Classification bands: High (≥80), Medium (60-79), Low (<60)

**Next Steps for Production:**
1. Train ML model on labeled data
2. Implement evidence extraction with spaCy
3. Add manual review workflow
4. Deploy API for interactive queries

## 🎯 Example Queries

### Find High-Scoring Quantum Awards
```python
import pandas as pd
awards = pd.read_parquet('data/processed/awards.parquet')
assessments = pd.read_parquet('data/processed/assessments.parquet')

quantum_high = assessments[
    (assessments['primary_cet_id'] == 'quantum_computing') &
    (assessments['score'] >= 80)
]
result = quantum_high.merge(awards, on='award_id')
print(result[['title', 'agency', 'score', 'award_amount']])
```

### Agency Spending by CET
```python
import pandas as pd
awards = pd.read_parquet('data/processed/awards.parquet')
assessments = pd.read_parquet('data/processed/assessments.parquet')

merged = awards.merge(assessments, on='award_id')
spending = merged.groupby(['agency', 'primary_cet_id'])['award_amount'].sum()
print(spending.sort_values(ascending=False).head(20))
```

## 🛠️ Need Help?

- View taxonomy: `cat data/taxonomy/cet_taxonomy_v1.csv`
- Check data: `python -c "import pandas as pd; print(pd.read_parquet('data/processed/awards.parquet').info())"`
- Run tests: `python -m pytest tests/ -v`
