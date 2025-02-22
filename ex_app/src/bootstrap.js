import Vue from 'vue'
import { translate, translatePlural } from '@nextcloud/l10n'
import { getCSPNonce } from '@nextcloud/auth'

Vue.prototype.t = translate
Vue.prototype.n = translatePlural
Vue.prototype.OC = window.OC
Vue.prototype.OCA = window.OCA

__webpack_nonce__ = getCSPNonce() // eslint-disable-line
