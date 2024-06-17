.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "Welcome to Vix. Please use \`make <target>\` where <target> is one of"
	@echo " "
	@echo "  Next commands are only for dev environment with nextcloud-docker-dev!"
	@echo "  They should run from the host you are developing on(with activated venv) and not in the container with Nextcloud!"
	@echo "  "
	@echo "  build-push        build image and upload to ghcr.io"
	@echo "  build-push-dev    build image and upload to ghcr.io with 'dev' tag"
	@echo "  "
	@echo "  run               install Visionatrix for Nextcloud Last"
	@echo "  run               install Visionatrix for Nextcloud Last"
	@echo "  "
	@echo "  For development of this example use PyCharm run configurations. Development is always set for last Nextcloud."
	@echo "  First run 'Visionatrix', then run 'Vix' and then 'make registerXX', after that you can use/debug/develop it and easy test."
	@echo "  "
	@echo "  register          perform registration of running Visionatrix into the 'manual_install' deploy daemon."
	@echo "  "
	@echo "  L10N (for manual translation):"
	@echo "  translation_templates      extract translation strings from sources"
	@echo "  convert_translations_nc    convert translations to Nextcloud format files (json, js)"
	@echo "  convert_to_locale    		copy translations to the common locale/<lang>/LC_MESSAGES/<appid>.(po|mo)"

.PHONY: build-push
build-push:
	docker login ghcr.io
	docker buildx build --push --platform linux/arm64/v8,linux/amd64 --tag ghcr.io/cloud-py-api/vix:1.0.0 --build-arg BUILD_TYPE=cpu .
	docker buildx build --push --platform linux/arm64/v8,linux/amd64 --tag ghcr.io/cloud-py-api/vix:1.0.0 --build-arg BUILD_TYPE=cuda .
	docker buildx build --push --platform linux/arm64/v8,linux/amd64 --tag ghcr.io/cloud-py-api/vix:1.0.0 --build-arg BUILD_TYPE=rocm .

.PHONY: build-push-dev
build-push-dev:
	docker login ghcr.io
	docker buildx build --push --platform linux/arm64/v8,linux/amd64 --tag ghcr.io/cloud-py-api/vix:dev --build-arg BUILD_TYPE=cpu .
	docker buildx build --push --platform linux/arm64/v8,linux/amd64 --tag ghcr.io/cloud-py-api/vix:dev --build-arg BUILD_TYPE=cuda .
	docker buildx build --push --platform linux/arm64/v8,linux/amd64 --tag ghcr.io/cloud-py-api/vix:dev --build-arg BUILD_TYPE=rocm .

.PHONY: run
run:
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:unregister vix --silent --force || true
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:register vix --force-scopes \
		--info-xml https://raw.githubusercontent.com/cloud-py-api/vix/main/appinfo/info.xml

.PHONY: run-dev
run:
	docker cp ./appinfo/info.xml master-nextcloud-1:/info.xml
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:unregister vix --silent --force || true
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:register vix --force-scopes --info-xml /info.xml

.PHONY: register
register:
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:unregister vix --silent --force || true
	docker exec master-nextcloud-1 rm -rf /tmp/vix_l10n && docker cp l10n master-nextcloud-1:/tmp/vix_l10n
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:register vix manual_install --json-info \
  "{\"id\":\"vix\",\"name\":\"Visionatrix\",\"daemon_config_name\":\"manual_install\",\"version\":\"1.0.0\",\"secret\":\"12345\",\"port\":9100,\"scopes\":[\"AI_PROVIDERS\", \"FILES\", \"USER_INFO\"],\"system_app\":0, \"translations_folder\":\"\/tmp\/vix_l10n\"}" \
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
