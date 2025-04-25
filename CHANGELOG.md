# Changelog

All notable changes to this project will be documented in this file.

## [1.4.0 - 2025-04-25]

This is a version with fixes for bugs we've discovered over the past month.

## Changes

- Visionatrix service has been [updated](https://github.com/Visionatrix/Visionatrix/blob/main/CHANGELOG.md#220---2025-04-21) from version `2.1.0` to `2.2.0`.

## Fixed

- UI: Visionatrix UI is now synced with Nextcloud theme, dark theme appearance fixed.
- UI: Refreshing the page does not redirect you back to the Visionatrix homepage.

## [1.3.0 - 2025-03-30]

This release contains breaking changes, first you need to uninstall old app **with its data removal** and after that install this version.

## Added

- Many flows were updated, some new flows were added.
- **Optional** remote token decoding using HuggingFace for some flows were added.
- `Surprise Me` - new feature to use LLM to create a random prompt.
- Many useful small UI additions(`Export flow`, `Editing flow` actions).
- Added support for `HaRP` deploy type - successor of `DockerSocketProxy`(Nextcloud 32+ only).

## Changes

- Visionatrix service has been updated from version `1.11.1` to `2.1.0`.
- Now Visionatrix **correctly stores all models and configs** in the configured ExApp storage and no more breaking changes expected.

## Fixes

- Fixed broken flows **Mad Scientist** and **PhotoStickers 2**.

## [1.2.1 - 2025-02-23]

The Visionatrix service has been updated from version `1.11.0` to `1.11.1`.

## Added

- Support for `File Picker` to select media files from a Nextcloud instance.

### Fixed

- Now works correctly on fresh installations with no flows installed.
- Prompt translations using **Gemini** now works correctly.

## [1.2.0 - 2025-02-17]

The Visionatrix service has been updated from version `1.9.0` to `1.11.0`.

### Added

- Many new Flows with `Pencil Sketch Portrait`, `Animal Clothing`, `SD3.5-Large`, `SD3.5-Medium`, `PixArt E`, `Aura Flow` models.
- New `gemini-2.0-flash-001` model available for selection in settings.
- Dynamic `LoRAs` support. For most basic Flows you can now easy add new loras from the `CivitAI`!
- UI: Added a filter for `supported` flows and memory requirements for each flow.
- UI: Displays required storage size for each model and for all models in a flow.
- UI: Settings: For `Ollama` now dropdown list with available models displayed.
- UI: Orphan models are now accessible in `Settings -> ComfyUI`.

### Changed

- All `Remove background` flows now use the new `ComfyUI_BiRefNet_ll` node with new models.

## [1.1.0 - 2024-12-18]

The [Visionatrix](https://github.com/Visionatrix/Visionatrix) service has been updated from version `1.4.1` to `1.9.0`.

**Please remove docker volume named `nc_app_visionatrix_data` or uninstall previous version of Visionatrix with `Delete data on remove` checkbox ticked.**

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
