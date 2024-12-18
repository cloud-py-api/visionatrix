# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0 - 2024-12-18]

The [Visionatrix](https://github.com/Visionatrix/Visionatrix) service has been updated from version `1.4.1` to `1.9.0`.
The main changes are summarized below:

### Added

- Support for flows that produce `video` files as output.
- `OpenAPI` specs support, enabling easier development of Nextcloud Apps that can seamlessly use Visionatrix flows.
- Many new `flows` with updated models.
- Parallel installation of `flows` and `models`.

### Changed

- Online `flows` and `models` storage has been separated, ensuring the integration remains stable.
- Added support for both `Ollama` and `Gemini` as providers for `Vision` and `Prompt translation`.

### Fixed

- Numerous bug fixes and significant performance improvements.

## [1.0.1 - 2024-10-18]

### Changed

- Updated the bundled Visionatrix from version `1.3.0` to `1.4.1`. The changelog for this update can be found [here](https://github.com/Visionatrix/Visionatrix/releases/tag/v1.4.0).

### Fixed

- Resolved the warning "sudo: unable to resolve host" during container startup.

## [1.0.0 - 2024-09-25]

### Added

- Initial release with the bundled Visionatrix version `1.3.0`.
