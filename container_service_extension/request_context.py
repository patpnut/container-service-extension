import pyvcloud.vcd.client as vcd_client

import container_service_extension.cloudapi.cloudapi_client as cloudApiClient
import container_service_extension.logger as logger
import container_service_extension.pyvcloud_utils as vcd_utils
import container_service_extension.user_context as user_context
import container_service_extension.utils as utils


class RequestContext:
    def __init__(self, auth_token, is_jwt=True, request_id=None):
        self._auth_token: str = auth_token
        self._is_jwt: bool = is_jwt

        # vCD API client from user auth token
        self._client: vcd_client.Client = None

        # vCD CloudAPI client from user client
        self._cloudapi_client: cloudApiClient.CloudApiClient = None

        # User context
        self._user: user_context.UserContext = None

        # async operations should call end() when they are finished
        self.is_async: bool = False

        # Request ID; may be None if RequestContext is initialized outside of
        # request_processor.py
        self.request_id: str = request_id

    @property
    def client(self):
        if self._client is None:
            self._client = vcd_utils.connect_vcd_user_via_token(
                tenant_auth_token=self._auth_token,
                is_jwt_token=self._is_jwt)
        return self._client

    @property
    def cloudapi_client(self):
        if self._cloudapi_client is None:
            log_wire = utils.get_server_runtime_config() \
                            .get('service', {}).get('log_wire', False)
            logger_wire = logger.NULL_LOGGER
            if log_wire:
                logger_wire = logger.SERVER_CLOUDAPI_WIRE_LOGGER
            token = self.client.get_access_token()
            is_jwt_token = True
            if not token:
                token = self.client.get_xvcloud_authorization_token()
                is_jwt_token = False
            self._cloudapi_client = cloudApiClient.CloudApiClient(
                self.client.get_cloudapi_uri(),
                token=token,
                is_jwt_token=is_jwt_token,
                api_version=self.client.get_api_version(),
                logger_debug=logger.SERVER_LOGGER,
                logger_wire=logger_wire,
                verify_ssl=self.client._verify_ssl_certs,
                is_sys_admin=self.client.is_sysadmin())
        return self._cloudapi_client

    @property
    def user(self):
        if self._user is None:
            self._user = user_context.UserContext(self.client,
                                                  self.cloudapi_client)
        return self._user

    @property
    def sysadmin_client(self):
        return self.user.sysadmin_client

    @property
    def sysadmin_cloudapi_client(self):
        return self.user.sysadmin_cloudapi_client

    def end(self):
        self.user.end()
