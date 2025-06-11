# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [6.0.0] - 2025-06-11

### Added

- Using UV instead of poetry for env manager
- Using tables for the images in the description

## [5.6.0]

### Added

- Support for Anilist.
- `--version` option.

### Changed

- MAL-specific options generalized to work with multiple services.

## [5.5.1]

### Fixed

- Minor bug fix (unspecified).

## [5.5.0]

### Added

- Cookie-based authentication support.

## [5.4.0]

### Added

- Uncensored tag option.

### Changed

- `overwrite` and auto tag detection options are now enabled by default.

### Fixed

- Attempt to skip overly long MAL titles.

## [5.3.0]

### Added

- `advert` option to prevent interference when notes are unnecessary.

### Fixed

- Excessive newlines before image tags.

## [5.2.0]

### Added

- Watch directory support via config and CLI option.

### Changed

- Project now requires Poetry v2.

### Fixed

- False positive detection of multi-subs.
- Removal of unused dependencies.
- Accurate retrieval of subtitle and audio durations.

## [5.1.0]

### Added

- Support for `torrenttools`.

## [5.0.0]

### Changed

- Major file restructuring.
- Switched from `argparse` to `cloup`.
- Code modularization and typo fixes.

## [4.2.0]

### Fixed

- Issues with image uploading.
- Cookie verification with fallback to standard image upload.

## [4.1.0]

### Changed

- Switched to asynchronous image upload functions.

## [4.0.0]

### Added

- Optimized image uploading logic.

### Changed

- Configuration now prompts only for domain.
