.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "Welcome to Vix. Please use \`make <target>\` where <target> is one of"
	@echo " "
	@echo "  Next commands are only for dev environment with nextcloud-docker-dev!"
	@echo "  They should run from the host you are developing on(with activated venv) and not in the container with Nextcloud!"
	@echo "  "
	@echo "  build-push        build image and upload to ghcr.io"
	@echo "  "
	@echo "  run28             install Visionatrix for Nextcloud 28"
	@echo "  run29             install Visionatrix for Nextcloud 29"
	@echo "  run               install Visionatrix for Nextcloud Last"
	@echo "  "
	@echo "  For development of this example use PyCharm run configurations. Development is always set for last Nextcloud."
	@echo "  First run 'UiExample' and then 'make registerXX', after that you can use/debug/develop it and easy test."
	@echo "  "
	@echo "  register28        perform registration of running Visionatrix into the 'manual_install' deploy daemon."
	@echo "  register29        perform registration of running Visionatrix into the 'manual_install' deploy daemon."
	@echo "  register          perform registration of running Visionatrix into the 'manual_install' deploy daemon."
	@echo "  "
	@echo "  L10N (for manual translation):"
	@echo "  translation_templates      extract translation strings from sources"
	@echo "  convert_translations_nc    convert translations to Nextcloud format files (json, js)"
	@echo "  convert_to_locale    		copy translations to the common locale/<lang>/LC_MESSAGES/<appid>.(po|mo)"

.PHONY: build-push
build-push:
	docker login ghcr.io
	docker buildx build --push --platform linux/arm64/v8,linux/amd64 --tag ghcr.io/cloud-py-api/vix:latest .

.PHONY: run28
run28:
	docker exec master-stable28-1 sudo -u www-data php occ app_api:app:unregister vix --silent --force || true
	docker exec master-stable28-1 sudo -u www-data php occ app_api:app:register vix --force-scopes \
		--info-xml https://raw.githubusercontent.com/cloud-py-api/vix/main/appinfo/info.xml

.PHONY: run29
run29:
	docker exec master-stable29-1 sudo -u www-data php occ app_api:app:unregister vix --silent --force || true
	docker exec master-stable29-1 sudo -u www-data php occ app_api:app:register vix --force-scopes \
		--info-xml /info.xml
# --info-xml https://raw.githubusercontent.com/cloud-py-api/vix/main/appinfo/info.xml
.PHONY: run
run:
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:unregister vix --silent --force || true
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:register vix --force-scopes \
		--info-xml https://raw.githubusercontent.com/cloud-py-api/vix/main/appinfo/info.xml

.PHONY: register28
register28:
	docker exec master-stable28-1 sudo -u www-data php occ app_api:app:unregister vix --silent --force || true
	docker exec master-stable28-1 rm -rf /tmp/vix_l10n && docker cp l10n master-stable28-1:/tmp/vix_l10n
	docker exec master-stable28-1 sudo -u www-data php occ app_api:app:register vix manual_install --json-info \
  "{\"id\":\"vix\",\"name\":\"Visionatrix\",\"daemon_config_name\":\"manual_install\",\"version\":\"1.0.0\",\"secret\":\"12345\",\"port\":9045,\"scopes\":[\"OCC_COMMAND\", \"NOTIFICATIONS\"],\"system_app\":0, \"translations_folder\":\"\/tmp\/vix_l10n\"}" \
  --force-scopes --wait-finish

.PHONY: register29
register29:
	docker exec master-stable29-1 sudo -u www-data php occ app_api:app:unregister vix --silent --force || true
	docker exec master-stable29-1 rm -rf /tmp/vix_l10n && docker cp l10n master-stable29-1:/tmp/vix_l10n
	docker exec master-stable29-1 sudo -u www-data php occ app_api:app:register vix manual_install --json-info \
  "{\"id\":\"vix\",\"name\":\"Visionatrix\",\"daemon_config_name\":\"manual_install\",\"version\":\"1.0.0\",\"secret\":\"12345\",\"port\":9045,\"scopes\":[\"OCC_COMMAND\", \"NOTIFICATIONS\"],\"system_app\":0, \"translations_folder\":\"\/tmp\/vix_l10n\"}" \
  --force-scopes --wait-finish

.PHONY: register
register:
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:unregister vix --silent --force || true
	docker exec master-nextcloud-1 rm -rf /tmp/vix_l10n && docker cp l10n master-nextcloud-1:/tmp/vix_l10n
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:register vix manual_install --json-info \
  "{\"id\":\"vix\",\"name\":\"Visionatrix\",\"daemon_config_name\":\"manual_install\",\"version\":\"1.0.0\",\"secret\":\"12345\",\"port\":9045,\"scopes\":[\"OCC_COMMAND\", \"NOTIFICATIONS\"],\"system_app\":0, \"translations_folder\":\"\/tmp\/vix_l10n\"}" \
  --force-scopes --wait-finish

.PHONY: translation_templates
translation_templates:
	./translationtool.phar create-pot-files

.PHONY: convert_translations_nc
convert_translations_nc:
	./translationtool.phar convert-po-files

.PHONY: convert_to_locale
convert_to_locale:
	./scripts/convert_to_locale.sh
