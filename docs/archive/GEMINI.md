# SBIR CET Classifier

## Project Overview

This project is a Python application designed to analyze Small Business Innovation Research (SBIR) awards and align them with Critical and Emerging Technology (CET) areas. It provides a command-line interface (CLI) for data ingestion and a FastAPI-based web API for serving analysis results.

The project uses a modular structure, with code organized into `data`, `features`, `models`, `evaluation`, `common`, `cli`, and `api` modules. It leverages popular Python libraries such as `pandas` for data manipulation, `scikit-learn` for machine learning, `spacy` for natural language processing, and `fastapi` for the web API.

## Building and Running

### Setup

1.  Create a virtual environment:
    ```bash
    python -m venv .venv
    ```
2.  Activate the virtual environment:
    ```bash
    source .venv/bin/activate
    ```
3.  Install dependencies:
    ```bash
    pip install -e .[dev]
    ```
4.  Download the `spacy` model:
    ```bash
    python -m spacy download en_core_web_md
    ```

### Running the Application

*   **CLI:** The main entry point for the CLI is `src/sbir_cet_classifier/cli/app.py`. You can run it using:
    ```bash
    python -m sbir_cet_classifier.cli.app --help
    ```
*   **API:** The API is built with FastAPI. To run the API server, you can use `uvicorn`:
    ```bash
    uvicorn sbir_cet_classifier.api.router:router --reload
    ```

### Testing

The project uses `pytest` for testing. To run the tests, use the following command:

```bash
pytest -m "not slow"
```

## Development Conventions

*   **Code Style:** The project uses `ruff` for linting and formatting.
*   **Type Hinting:** The codebase uses type hints for better code quality and maintainability.
*   **Testing:** Features should be accompanied by tests.
*   **Modularity:** The code is organized into modules to promote separation of concerns.
*   **Feature Development:** The development workflow is guided by the specification in `specs/001-i-want-to/`.
