from datetime import datetime
from uuid import uuid4

import jaynes
from jaynes.helpers import memoize
from jaynes.launchers.base_launcher import Launcher, make_launch_script
from jaynes.runners import Runner


def launch_gcp(launch_scripts, **kws):
    import googleapiclient.discovery

    compute = googleapiclient.discovery.build('compute', 'v1')
    # todo: there is a way to do this in batch mode that is a lot faster.

    batch_request = compute.new_batch_http_request()
    for ls in launch_scripts:
        instance_config = gce_instance_config(ls, **kws)
        batch_request.instances().insert(**instance_config)

    batch_request.execute()['id']


@memoize
def get_image_id(image_project, image_family):
    import googleapiclient.discovery

    compute = googleapiclient.discovery.build('compute', 'v1')

    image_response = compute.images().getFromFamily(project=image_project, family=image_family).execute()
    image_id = image_response['selfLink']
    return image_id


def gce_instance_config(launch_script, project_id, zone, instance_type, image_id=None,
                        image_project='deeplearning-platform-release', image_family='pytorch-latest-gpu',
                        accelerator_type=None, accelerator_count=None,
                        preemptible=False, boot_size=60,
                        verbose=False, name=f"jaynes-job-{uuid4()}", tags={}, **_):
    if verbose:
        print('Using the default GCLoud Profile')

    image_id = image_id or get_image_id(image_project, image_family)

    import re
    normalized_name = re.sub('([^a-z0-9]+)', ' ', name.lower()).strip().replace(' ', '-')
    instance_config = {
        # todo: use regex to replace all non- [a-z0-9] chars with '-'
        'name': normalized_name[-63:],
        'machineType': f"zones/{zone}/machineTypes/{instance_type}",
        # 'preemptible': preemptible,
        'scheduling': {
            'preemptible': preemptible,
            # for accelerator enabled instances such as a2-highgpu-*, this needs to be set
            'onHostMaintenance': 'TERMINATE',
            'automaticRestart': False,
        },

        # Specify the boot disk and the image to use as a source.
        'disks': [
            {
                'boot': True,
                'autoDelete': True,
                'initializeParams': {
                    'sourceImage': image_id,
                    'diskSizeGb': boot_size
                }
            }
        ],

        # Specify a network interface with NAT to access the public
        # internet.
        'networkInterfaces': [{
            'network': 'global/networks/default',
            'accessConfigs': [
                {'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}
            ]
        }],

        # Allow the instance to access cloud storage and logging.
        'serviceAccounts': [{
            'email': 'default',
            'scopes': [
                'https://www.googleapis.com/auth/devstorage.read_write',
                'https://www.googleapis.com/auth/logging.write',
                # for self-termination, full compute read and write
                'https://www.googleapis.com/auth/compute'
            ]
        }],

        # Metadata is readable from the instance and allows you to
        # pass configuration from deployment scripts to instances.
        'metadata': {
            'items': [
                dict(key='startup-script', value=launch_script),
                # Cast True to 'True'. Tag values are string types.
                *(dict(key=k, value=str(v)) for k, v in tags.items())
            ]
        },
    }
    # todo: need to add option for multiple
    if accelerator_type:
        instance_config['guestAccelerators'] = [{
            'acceleratorType': f"projects/{project_id}/zones/{zone}/acceleratorTypes/{accelerator_type}",
            'acceleratorCount': accelerator_count
        }]

    return dict(
        project=project_id,
        zone=zone,
        body=instance_config
    )


class GCE(Launcher):
    def __init__(self, project_id, zone, instance_type, image_id=None,
                 image_project='deeplearning-platform-release', image_family='pytorch-latest-gpu',
                 accelerator_type=None, accelerator_count=None, preemptible=False, boot_size=60,
                 verbose=False, name=None, tags={}, **_):
        super().__init__(project_id=project_id, zone=zone, instance_type=instance_type, image_id=image_id,
                         image_project=image_project, image_family=image_family,
                         accelerator_type=accelerator_type, accelerator_count=accelerator_count,
                         preemptible=preemptible, boot_size=boot_size,
                         verbose=verbose, name=name or f"jaynes-job-{datetime.utcnow():%H%M%S}-{jaynes.RUN.count}",
                         tags=tags, **_)

    def add_runner(self, runner: Runner):
        super().add_runner(runner)
        # cache the launch config
        runner.launch_config = self.config.copy()

    _gce_batch_request = None

    @property
    def gce_batch_request(self):
        if self._gce_batch_request is None:
            import googleapiclient.discovery

            compute = googleapiclient.discovery.build('compute', 'v1')
            # todo: there is a way to do this in batch mode that is a lot faster.
            self._gce_batch_request = compute.new_batch_http_request()

        return self._gce_batch_request

    def launch_instance(self, verbose=None):
        launch_script = make_launch_script(runners=self.runners, mounts=self.all_mounts,
                                           unpack_on_host=True, **self.config)
        launch_config = self.runners[0].launch_config
        self.runners.clear()

        if verbose:
            print(launch_script)

        import googleapiclient.discovery
        compute = googleapiclient.discovery.build('compute', 'v1')
        instance_config = gce_instance_config(launch_script, **launch_config)
        request = compute.instances().insert(**instance_config)

        return request.execute()['id']

    def plan_instance(self, verbose=None):
        launch_script = make_launch_script(runners=self.runners, mounts=self.all_mounts,
                                           unpack_on_host=True, **self.config)
        launch_config = self.runners[0].launch_config
        self.runners.clear()

        if verbose:
            print(launch_script)

        import googleapiclient.discovery
        compute = googleapiclient.discovery.build('compute', 'v1')
        instance_config = gce_instance_config(launch_script, **launch_config)
        self.gce_batch_request.add(compute.instances().insert(**instance_config))

    def execute(self, verbose=None):
        if self._gce_batch_request is None:
            return self.launch_instance(verbose=verbose)
        self.plan_instance(verbose=verbose)
        # todo: needs to return a list of request_ids.
        self.gce_batch_request.execute(verbose=verbose)
