from base import Base
from logger_agent import logger
from openstack import Openstack


class Glance(Base, Openstack):

    def __init__(self, tc, auth, **kwargs):
        super().__init__(tc, auth, **kwargs)
        self.extra_args = kwargs.get("extra_args", None)

    def get(self):
        (tc_status, message) = self.gc.GET(self.url, self.headers,
                                           data=self.data)
        return tc_status, message, self.tc

    def post(self):
        self.data['input']['import_from'] = self.extra_args['import_from']
        response = self.gc.POST(self.url, self.headers, data=self.data)
        if response.status_code >= 200 and response.status_code < 400:
            task_id = response.json()['id']
            image_id = None
            url = "{}/{}".format(self.url, task_id)
            logger.info(
                'Waiting for task {} to be completed'.format(
                    task_id
                ))
            result = self.gc.check_resource_status(url, self.headers)
            tc_status = 'PASS'
            while result.json()['status'] != "success":
                result = self.gc.check_resource_status(url, self.headers)
                image_result = result.json().get('result', None)
                if image_result:
                    image_id = image_result.get('image_id', None)
                if result.json()['status'] == "killed":
                    tc_status = 'FAIL'
                    message = result.text
                    break
            logger.info('Deleting the created image: {}'.format(image_id))
            images_url = self.url.replace('tasks', 'images')
            delete_url = "{}/{}".format(images_url, image_id)
            result = self.gc.DELETE(delete_url, self.headers)
            if result.status_code >= 200 and result.status_code < 400:
                tc_status = 'PASS'
                message = 'stripped not printing'
            else:
                tc_status = 'FAIL'
                message = result.text
        return tc_status, message, self.tc
