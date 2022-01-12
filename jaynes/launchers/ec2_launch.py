import base64

from jaynes.helpers import snake2camel
from jaynes.launchers.base_launcher import Launcher, make_launch_script


# "image_id instance_type key_name security_group spot_price iam_instance_profile_arn "
# "verbose region availability_zone dry name tags"


class EC2(Launcher):
    _instance_plan = None

    @property
    def instance_plan(self):
        if self._instance_plan is None:
            self._instance_plan = []
        return self._instance_plan

    def add_runner(self, runner):
        super().add_runner(runner)
        runner.launch_config = self.config.copy()

    def plan_instance(self, verbose=None):
        launch_script = make_launch_script(runners=self.runners, mounts=self.all_mounts,
                                           unpack_on_host=True, **self.config)
        launch_config = self.runners[0].launch_config
        self.runners.clear()

        if verbose:
            print(launch_script)

        self.instance_plan.append(dict(launch_script=launch_script, **launch_config))

    def execute(self, verbose=None):
        self.plan_instance(verbose=verbose)

        ids = []
        for instance_config in self.instance_plan:
            request_id = launch_ec2(**instance_config, verbose=verbose)
            ids.append(request_id)

        self.instance_plan.clear()
        return ids


def launch_ec2(launch_script, image_id, instance_type, key_name, security_group, spot_price=None,
               iam_instance_profile_arn=None, region=None, availability_zone=None,
               dry=False, name=None, tags={}, verbose=False, **_):
    from termcolor import cprint
    import boto3
    if verbose:
        print('Using the default AWS Profile')

    instance_config = dict(ImageId=image_id, KeyName=key_name, InstanceType=instance_type,
                           SecurityGroups=(security_group,),
                           IamInstanceProfile={'Arn': iam_instance_profile_arn})
    if availability_zone:
        instance_config['Placement'] = dict(AvailabilityZone=availability_zone)

    tags = {snake2camel(k): v for k, v in tags.items()}
    if name:
        tags["Name"] = name
    tag_str = [dict(Key=k, Value=v) for k, v in tags.items()]

    # note: region needs to agree with availability_zone.
    ec2 = boto3.client("ec2", region_name=region)
    if spot_price:
        # for detailed settings see:
        #     http://boto3.readthedocs.io/en/latest/reference/services/ec2.html#EC2.Client.request_spot_instances
        # issue here: https://github.com/boto/boto3/issues/368
        instance_config.update(UserData=base64.b64encode(launch_script.encode()).decode("utf-8"))
        if verbose:
            print(instance_config)
        response = ec2.request_spot_instances(
            InstanceCount=1, LaunchSpecification=instance_config,
            SpotPrice=str(spot_price), DryRun=dry)
        spot_request_id = response['SpotInstanceRequests'][0]['SpotInstanceRequestId']
        if verbose:
            import yaml
            print(yaml.dump(response))
        if tags:
            ec2.create_tags(DryRun=dry, Resources=[spot_request_id], Tags=tag_str)
        cprint(f'made instance request {spot_request_id}', 'blue')
        return spot_request_id
    else:
        instance_config.update(UserData=launch_script)
        if verbose:
            print(instance_config)
        response = ec2.run_instances(MaxCount=1, MinCount=1, **instance_config, DryRun=dry)
        instance_id = response['Instances'][0]['InstanceId']
        if verbose:
            print(response)
        if tags:
            ec2.create_tags(DryRun=dry, Resources=[instance_id], Tags=tag_str)
        cprint(f'launched instance {instance_id}', 'green')
        return instance_id
