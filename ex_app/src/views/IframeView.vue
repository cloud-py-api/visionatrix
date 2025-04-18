<template>
	<div class="iframe-ui-viewer">
		<iframe
			v-show="!error && !loading"
			id="visionatrix-iframe"
			ref="iframe"
			:name="'visionatrix-iframe'"
			class="visionatrix__iframe"
			allow="clipboard-read *; clipboard-write *"
			:src="iframeSrc" />
		<NcLoadingIcon v-if="loading" :size="48" />
		<NcEmptyContent
			v-if="error && !loading"
			:name="t('visionatrix', 'Failed to load service iframe')"
			:description="t('visionatrix', 'Please try again.')">
			<template #icon>
				<AlertCircleIcon :size="20" />
			</template>
		</NcEmptyContent>
	</div>
</template>

<script>
import { generateUrl } from '@nextcloud/router'

import NcEmptyContent from '@nextcloud/vue/dist/Components/NcEmptyContent.js'
import AlertCircleIcon from 'vue-material-design-icons/AlertCircle.vue'
import NcLoadingIcon from '@nextcloud/vue/dist/Components/NcLoadingIcon.js'

import { APP_API_PROXY_URL_PREFIX, EX_APP_ID } from '../constants/AppAPI.js'

import { getFilePickerBuilder } from '@nextcloud/dialogs'
import '@nextcloud/dialogs/style.css'

export default {
	name: 'IframeView',
	components: {
		NcEmptyContent,
		AlertCircleIcon,
		NcLoadingIcon,
	},
	data() {
		const baseUrl = generateUrl(`${APP_API_PROXY_URL_PREFIX}/${EX_APP_ID}/`, {}, { noRewrite: true })
		const iframeSrcUrl = process.env.HARP_ENABLED ? baseUrl.replace('/index.php', '') : baseUrl
		return {
			error: null,
			loading: true,
			iframeSrc: iframeSrcUrl,
		}
	},
	mounted() {
		const timeout = setTimeout(() => {
			this.error = true
			this.loading = false
		}, 10000)
		this.$refs.iframe.addEventListener('load', (event) => {
			console.debug('iframe service loaded', event)
			this.loading = false
			clearTimeout(timeout)
		})
		this.$refs.iframe.addEventListener('error', (event) => {
			console.debug('iframe service error', event)
			this.error = true
			this.loading = false
		})
		window.addEventListener('message', (event) => {
			if (event.data.type === 'openNextcloudFilePicker') {
				this.showFilePicker(event)
			}
		})
	},
	methods: {
		showFilePicker(event) {
			if (!event.data.inputParamName) {
				return
			}
			const inputParamName = event.data.inputParamName
			getFilePickerBuilder(t('visionatrix', 'Select a file'))
				.setMultiSelect(false)
				.allowDirectories(false)
				.addMimeTypeFilter('image/*')
				.addButton({
					label: t('visionatrix', 'Select'),
					callback: (nodes) => {
						this.sendSelectedFilesToIframe(nodes, inputParamName)
					},
				})
				.build().pick().catch(() => {})
		},
		sendSelectedFilesToIframe(nodes, inputParamName) {
			const files = nodes.map((node) => {
				return {
					...node?._data,
				}
			})
			this.$refs.iframe.contentWindow.postMessage({ files, inputParamName }, '*')
		},
	},
}
</script>

<style>
.iframe-ui-viewer {
	display: flex;
	justify-content: center;
	align-items: center;
	height: 100%;
}

.visionatrix__iframe {
	width: 100%;
	height: 100%;
	flex-grow: 1;
	background-color: #1c1b22;
}
</style>
