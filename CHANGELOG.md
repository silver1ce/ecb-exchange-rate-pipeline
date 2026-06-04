# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-04

### Added

- Initial ECB exchange rate ingestion pipeline (extract, transform, load)
- Normalized PostgreSQL schema with Alembic migrations
- FastAPI REST API for series, observations, and ingestion triggers
- Docker Compose local development stack
- GitHub Actions CI and scheduled data quality workflow
- Unit and integration test suite with sample ECB fixtures
- Architecture, schema, API, and runbook documentation
