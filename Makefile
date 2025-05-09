.DEFAULT_GOAL := help

APP_ID := visionatrix
APP_NAME := Visionatrix
APP_VERSION := $$(xmlstarlet sel -t -v "//version" appinfo/info.xml)
VISIONATRIX_VERSION := $$(xmlstarlet sel -t -v "//image-tag" appinfo/info.xml)
JSON_INFO := "{\"id\":\"$(APP_ID)\",\"name\":\"$(APP_NAME)\",\"daemon_config_name\":\"manual_install\",\"version\":\"$(APP_VERSION)\",\"secret\":\"12345\",\"port\":23700, \"routes\": [{\"url\":\".*\",\"verb\":\"GET, POST, PUT, DELETE\",\"access_level\":1,\"headers_to_exclude\":[]}], \"translations_folder\":\"\/tmp\/vix_l10n\"}"
JSON_INFO_HARP := "{\"id\":\"$(APP_ID)\",\"name\":\"$(APP_NAME)\",\"daemon_config_name\":\"manual_install_harp\",\"version\":\"$(APP_VERSION)\",\"secret\":\"12345\",\"port\":23700, \"routes\": [{\"url\":\".*\",\"verb\":\"GET, POST, PUT, DELETE\",\"access_level\":1,\"headers_to_exclude\":[]}], \"translations_folder\":\"\/tmp\/vix_l10n\"}"


.PHONY: help
help:
	@echo "  Welcome to $(APP_NAME) $(APP_VERSION)!"
	@echo " "
	@echo "  Please use \`make <target>\` where <target> is one of"
	@echo " "
	@echo "  build-push-cpu    builds CPU images and uploads them to ghcr.io"
	@echo "  build-push-cuda   builds CUDA image and uploads it to ghcr.io"
	@echo "  build-push-rocm   builds ROCM image and uploads it to ghcr.io"
	@echo " "
	@echo "  > Next commands are only for the dev environment with nextcloud-docker-dev!"
	@echo "  > They must be run from the host you are developing on, not in a Nextcloud container!"
	@echo " "
	@echo "  run30             installs $(APP_NAME) for Nextcloud 30"
	@echo "  run               installs $(APP_NAME) for Nextcloud Latest"
	@echo " "
	@echo "  > Commands for manual registration of ExApp($(APP_NAME) should be running!):"
	@echo " "
	@echo "  register30        performs registration of running $(APP_NAME) into the 'manual_install' deploy daemon."
	@echo "  register          performs registration of running $(APP_NAME) into the 'manual_install' deploy daemon."
	@echo "  register_harp     performs registration of running $(APP_NAME) into the 'manual_install_harp' deploy daemon."
	@echo " "
	@echo "  L10N (for manual translation):"
	@echo "  translation_templates      extract translation strings from sources"
	@echo "  convert_translations_nc    convert translations to Nextcloud format files (json, js)"
	@echo "  convert_to_locale          copy translations to the common locale/<lang>/LC_MESSAGES/<appid>.(po|mo)"

.PHONY: build-push-cpu
build-push-cpu:
	DOCKER_BUILDKIT=1 docker buildx build --progress=plain --push --platform linux/amd64 --tag ghcr.io/cloud-py-api/$(APP_ID):$(VISIONATRIX_VERSION) --build-arg BUILD_TYPE=cpu .

.PHONY: build-push-cuda
build-push-cuda:
	DOCKER_BUILDKIT=1 docker buildx build --progress=plain --push --platform linux/amd64 --tag ghcr.io/cloud-py-api/$(APP_ID):$(VISIONATRIX_VERSION)-cuda --build-arg BUILD_TYPE=cuda .

.PHONY: build-push-rocm
build-push-rocm:
	DOCKER_BUILDKIT=1 docker buildx build --progress=plain --push --platform linux/amd64 --tag ghcr.io/cloud-py-api/$(APP_ID):$(VISIONATRIX_VERSION)-rocm --build-arg BUILD_TYPE=rocm .

.PHONY: run30
run30:
	docker exec master-stable30-1 sudo -u www-data php occ app_api:app:unregister $(APP_ID) --silent --force || true
	docker exec master-stable30-1 sudo -u www-data php occ app_api:app:register $(APP_ID) \
		--info-xml https://raw.githubusercontent.com/cloud-py-api/$(APP_ID)/main/appinfo/info.xml

.PHONY: run
run:
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:unregister $(APP_ID) --silent --force || true
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:register $(APP_ID) \
		--info-xml https://raw.githubusercontent.com/cloud-py-api/$(APP_ID)/main/appinfo/info.xml

.PHONY: register30
register30:
	docker exec master-stable30-1 sudo -u www-data php occ app_api:app:unregister $(APP_ID) --silent --force || true
	docker exec master-stable30-1 rm -rf /tmp/vix_l10n && docker cp ex_app/l10n master-stable30-1:/tmp/vix_l10n
	docker exec master-stable30-1 sudo -u www-data php occ app_api:app:register $(APP_ID) manual_install --json-info $(JSON_INFO) --wait-finish

.PHONY: register
register:
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:unregister $(APP_ID) --silent --force || true
	docker exec master-nextcloud-1 rm -rf /tmp/vix_l10n && docker cp ex_app/l10n master-nextcloud-1:/tmp/vix_l10n
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:register $(APP_ID) manual_install --json-info $(JSON_INFO) --wait-finish

.PHONY: register_harp
register_harp:
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:unregister $(APP_ID) --silent --force || true
	docker exec master-nextcloud-1 rm -rf /tmp/vix_l10n && docker cp ex_app/l10n master-nextcloud-1:/tmp/vix_l10n
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:register $(APP_ID) manual_install_harp --json-info $(JSON_INFO_HARP) --wait-finish

.PHONY: translation_templates
translation_templates:
	./translationtool.phar create-pot-files

.PHONY: convert_translations_nc
convert_translations_nc:
	./translationtool.phar convert-po-files

.PHONY: convert_to_locale
convert_to_locale:
	./scripts/convert_to_locale.sh

.PHONY: js
js:
	rm -rf ex_app/js ex_app/js_harp
	HARP_ENABLED=1 npm run build && mv ex_app/js ex_app/js_harp
	npm run build
