# Nextcloud Vix

Introduce the scalable AI Media processing for Nextcloud.

![Nextcloud Vix](/screenshots/vix_1.jpg)
![Nextcloud Vix](/screenshots/vix_2.png)

Nextcloud Vix is a standalone [Visionatrix](https://github.com/Visionatrix/Visionatrix) service that allows you to process your media files right in your Nextcloud.

Each user authenticated using Nextcloud credentials and has their own tasks history.

## Installation

1. Install and configure [AppAPI](https://github.com/cloud-py-api/app_api)
2. After AppAPI is installed and Deploy daemon is configured, install Nextcloud Vix ExApp from the Nextcloud AppStore.
3. Enjoy Nextcloud Vix from the Top Menu.

> [!NOTE]
> The Deploy daemon with GPU 12GB+ VRAM is recommended to run all available Visionatrix flows.

## Workers Configuration

By default, Vix uses available hardware on daemon as the first worker.
Vix **supports scalability** by attaching additional workers.
You can even setup your home computer with GPU as a worker for your Nextcloud.

> [!NOTE]
> Worker Auth have to use Nextcloud credentials. If you have 2FA enabled, you have to use App Password.

For more information on that, please refer to the [Visionatrix workers documentation](https://visionatrix.github.io/VixFlowsDocs/).

## Questions

Do not hesitate to ask any questions or report issues.
