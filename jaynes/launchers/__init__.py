from .ec2_launch import EC2
from .gcp_launch import GCE
from .ssh_launch import SSH
from .manager_launch import Manager
from .kube_launch import Kube

ec2 = EC2
gce = GCE
ssh = SSH
manager = Manager
kube = Kube
