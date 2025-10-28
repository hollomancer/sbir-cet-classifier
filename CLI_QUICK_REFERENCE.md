# SBIR CET Classifier - CLI Quick Reference

> Quick reference for the reorganized CLI structure

## Command Structure

```
sbir <command-group> <command> [options]
```

---

## Available Command Groups

| Group | Description | Commands |
|-------|-------------|----------|
| `ingest` | Data ingestion | `refresh`, `single` |
| `classify` | Classification | `run` |
| `summary` | Reporting | `show` |
| `review-queue` | Manual review | `list`, `escalate`, `approve`, `stats` |
| `awards` | Award management | `list`, `show`, `cet-detail` |
| `enrich` | Data enrichment | `solicitation`, `batch-solicitations`, `status` |
| `export` | Data export | Various export commands |
| `config` | Configuration | Config management commands |
| `rules` | Rule management | Rule management commands |

---

## Common Commands

### Ingest Data

```bash
# Single fiscal year
sbir ingest single 2023

# Multiple years
sbir ingest refresh --fiscal-year-start 2020 --fiscal-year-end 2023

# Custom source URL
sbir ingest single 2023 --source-url https://custom.url/awards.zip
```

### Run Classification

```bash
# Basic classification
sbir classify run --awards-path data/awards.csv --sample-size 100

# With rule-based scoring
sbir classify run \
  --awards-path data/awards.csv \
  --sample-size 500 \
  --rule-score

# With hybrid scoring (ML + rules)
sbir classify run \
  --awards-path data/awards.csv \
  --sample-size 500 \
  --hybrid-score \
  --hybrid-weight 0.6

# Don't save outputs
sbir classify run \
  --awards-path data/awards.csv \
  --no-save
```

### View Summaries

```bash
# Basic summary
sbir summary show 2020 2023

# Filter by agency
sbir summary show 2020 2023 --agency DOD --agency NASA
```

### List Awards

```bash
# Basic listing
sbir awards list \
  --fiscal-year-start 2020 \
  --fiscal-year-end 2023

# With filters
sbir awards list \
  --fiscal-year-start 2020 \
  --fiscal-year-end 2023 \
  --agency DOD \
  --phase "Phase II" \
  --state CA \
  --page 1 \
  --page-size 50
```

### Award Details

```bash
# Show specific award
sbir awards show --award-id AWARD-12345

# CET area details
sbir awards cet-detail \
  --cet-id CET-001 \
  --fiscal-year-start 2020 \
  --fiscal-year-end 2023
```

### Data Enrichment

```bash
# Enrich single solicitation
sbir enrich solicitation SOL-2024-001 --verbose

# Batch enrichment
sbir enrich batch-solicitations \
  input.csv \
  --output-dir data/processed \
  --batch-size 10 \
  --max-concurrent 3

# Check enrichment status
sbir enrich status --verbose
```

### Review Queue (Stubs - Implementation Pending)

```bash
# List pending items
sbir review-queue list --limit 100

# List by agency
sbir review-queue list --agency DOD

# Escalate item
sbir review-queue escalate Q12345 \
  --reason "Requires SME review"

# Approve item
sbir review-queue approve Q12345 \
  --applicable \
  --notes "Dual-use technology confirmed"

# View statistics
sbir review-queue stats --fiscal-year 2023
```

---

## Global Options

All commands support:

```bash
--help, -h       Show help message
--verbose, -v    Verbose output (where supported)
--quiet, -q      Minimal output (where supported)
```

---

## Getting Help

```bash
# Main help
sbir --help

# Command group help
sbir ingest --help
sbir classify --help
sbir summary --help

# Specific command help
sbir ingest single --help
sbir classify run --help
sbir awards list --help
```

---

## Environment Variables

- `SBIR_CONFIG_PATH` - Path to configuration file
- `SBIR_DATA_DIR` - Override data directory
- `SAM_API_KEY` - SAM.gov API key for enrichment

---

## Output Formats

Most commands output JSON by default. Use formatters for cleaner output:

- **Success messages**: Green text
- **Error messages**: Red text (stderr)
- **Warnings**: Yellow text
- **Info messages**: Standard output
- **JSON data**: Formatted with 2-space indentation

---

## Common Patterns

### Piping Output

```bash
# Save to file
sbir summary show 2020 2023 > summary.json

# Filter with jq
sbir awards list --fiscal-year-start 2020 --fiscal-year-end 2023 | jq '.awards[0]'
```

### Batch Processing

```bash
# Process multiple years
for year in {2020..2023}; do
  sbir ingest single $year
done

# Classify multiple files
for file in data/awards_*.csv; do
  sbir classify run --awards-path "$file" --sample-size 100
done
```

---

## Migration from Old Commands

| Old | New |
|-----|-----|
| `sbir refresh ...` | `sbir ingest refresh ...` |
| `sbir ingest <year>` | `sbir ingest single <year>` |
| `sbir classify ...` | `sbir classify run ...` |
| `sbir summary ...` | `sbir summary show ...` |

---

## Tips

1. **Use tab completion** (if configured) for command discovery
2. **Check help first**: `sbir <group> <command> --help`
3. **Start small**: Test with small samples before large datasets
4. **Save outputs**: Use `--save` flag for classification results
5. **Monitor progress**: Use `--verbose` for detailed logging

---

## Examples by Use Case

### Initial Setup & Data Loading

```bash
# 1. Ingest historical data
sbir ingest refresh --fiscal-year-start 2015 --fiscal-year-end 2023

# 2. Verify data loaded
sbir summary show 2015 2023

# 3. Check specific agency
sbir summary show 2015 2023 --agency DOD
```

### Running Analysis

```bash
# 1. Export recent awards
sbir awards list --fiscal-year-start 2023 --fiscal-year-end 2023 > awards_2023.json

# 2. Run classification
sbir classify run --awards-path awards_2023.csv --sample-size 1000 --hybrid-score

# 3. View results
cat data/artifacts/classifications/2023/manifest.json | jq
```

### Data Quality & Enrichment

```bash
# 1. Check enrichment status
sbir enrich status --verbose

# 2. Enrich missing solicitations
sbir enrich batch-solicitations awards.csv --skip-existing

# 3. Verify enrichment
sbir enrich status --verbose
```

---

## Troubleshooting

### Command not found
- Ensure package is installed: `pip install -e .`
- Check entry point: `which sbir`

### Import errors
- Verify installation: `python -m sbir_cet_classifier.cli.app --help`
- Check dependencies: `pip install -r requirements.txt`

### Data not found
- Check config: `sbir config show`
- Verify paths exist
- Run ingest first

### API errors (enrichment)
- Check API key: `echo $SAM_API_KEY`
- Verify network connectivity
- Check rate limits

---

## Further Reading

- **Full Documentation**: `CLI_REORGANIZATION.md`
- **Week 1 Status**: `WEEK1_TASK2_CLI_REORGANIZATION.md`
- **Refactoring Plan**: `REFACTORING_QUICK_START.md`

---

**Last Updated**: January 2024  
**Version**: Post-CLI Reorganization (Week 1, Task 2)