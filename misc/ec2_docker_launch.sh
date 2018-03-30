#!/bin/bash
truncate -s 0 /home/ubuntu/user_data.log
{
die() { status=$1; shift; echo "FATAL: $*"; exit $status; }
EC2_INSTANCE_ID="`wget -q -O - http://169.254.169.254/latest/meta-data/instance-id`"

aws ec2 create-tags --resources $EC2_INSTANCE_ID --tags Key=Name,Value=infogan-rope-2018-03-28-10-18-16-000 --region us-west-2
aws ec2 create-tags --resources $EC2_INSTANCE_ID --tags Key=exp_prefix,Value=infogan-rope --region us-west-2

sudo service docker start
docker --config /home/ubuntu/.docker pull thanard/matplotlib:latest
export AWS_DEFAULT_REGION=us-west-1

curl "https://s3.amazonaws.com/aws-cli/awscli-bundle.zip" -o "awscli-bundle.zip"
yes A | unzip awscli-bundle.zip
sudo ./awscli-bundle/install -i /usr/local/aws -b /usr/local/bin/aws
echo "aws cli is installed"

aws s3 cp s3://ge-bair/jaynes/mount/b57f05bfff0397f91f5a7c3b0b71766c.tar /tmp/b57f05bfff0397f91f5a7c3b0b71766c.tar
mkdir -p /tmp/b57f05bfff0397f91f5a7c3b0b71766c
tar -xvf /tmp/b57f05bfff0397f91f5a7c3b0b71766c.tar -C /tmp/b57f05bfff0397f91f5a7c3b0b71766c
aws s3 cp s3://ge-bair/jaynes/mount/6eded1ede08c6e323527417195f48431.tar /tmp/6eded1ede08c6e323527417195f48431.tar
mkdir -p /tmp/6eded1ede08c6e323527417195f48431
tar -xvf /tmp/6eded1ede08c6e323527417195f48431.tar -C /tmp/6eded1ede08c6e323527417195f48431
echo "code download complete"

mkdir -p /tmp/example/outputs
echo "make log direction complete"
while /bin/true; do
    aws s3 sync --exclude '*' --include '*.png' --include '*.log' /tmp/example/outputs s3://ge-bair/jaynes/logs/infogan-rope/infogan-rope-2018-03-28-10-18-16-000/
    aws s3 cp /home/ubuntu/user_data.log s3://ge-bair/jaynes/logs/infogan-rope/infogan-rope-2018-03-28-10-18-16-000/stdout.log
    sleep 15
done & echo "sync initiated"

while /bin/true; do
    if [ -z $(curl -Is http://169.254.169.254/latest/meta-data/spot/termination-time | head -1 | grep 404 | cut -d \  -f 2) ]
    then
        logger "Running shutdown hook."
        aws s3 cp --recursive /tmp/example/outputs s3://ge-bair/jaynes/logs/infogan-rope/infogan-rope-2018-03-28-10-18-16-000/
        break
    else
        # Spot instance not yet marked for termination.
        # This is hoping that there's at least 3 seconds
        # between when the spot instance gets marked for
        # termination and when it actually terminates.
        sleep 3
    fi
done & echo log sync initiated

aws s3 cp s3://ge-bair/jaynes/mount/6eded1ede08c6e323527417195f48431.tar /tmp/6eded1ede08c6e323527417195f48431.tar
mkdir -p /tmp/6eded1ede08c6e323527417195f48431
tar -xvf /tmp/6eded1ede08c6e323527417195f48431.tar -C /tmp/6eded1ede08c6e323527417195f48431
aws ec2 create-tags --resources $EC2_INSTANCE_ID --tags Key=Name,Value=infogan-rope-2018-03-28-10-18-16-000 --region us-west-2

echo "Trying to start nvidia-docker..."
for i in {1..800}; do
    sudo su -c "nvidia-modprobe -u -c=0" ubuntu && break || sleep 3;
done
echo "nvidia-docker started"
sudo systemctl start nvidia-docker
echo 'Testing nvidia-smi'
nvidia-smi
echo 'Testing nvidia-smi inside docker'
nvidia-docker run --rm thanard/matplotlib:latest nvidia-smi
nvidia-docker run  -v /tmp/b57f05bfff0397f91f5a7c3b0b71766c/jaynes:/root/code/jaynes \
    -v /tmp/6eded1ede08c6e323527417195f48431/infoGAN-pytorch-rope:/Users/ge/machine_learning/berkeley-playground/infoGAN-pytorch-rope \
    -v /home/ubuntu/machine_learning/datasets/rope/train:/Users/ge/machine_learning/datasets/rope/train \
    -v /tmp/example/outputs:/tmp/example/outputs \
    -v /tmp/6eded1ede08c6e323527417195f48431/infoGAN-pytorch-rope:/mounts/target/ \
    --name abeb8f48-f09a-4c85-b623 \
    thanard/matplotlib:latest /bin/bash -c 'echo "Running in docker (gpu)";export PYTHONPATH=$PYTHONPATH:/root/code/jaynes:/Users/ge/machine_learning/berkeley-playground/infoGAN-pytorch-rope;DOODAD_ARGS_DATA=gAN9cQAoWAgAAABkYXRhX2RpcnEBWC4AAAAvVXNlcnMvZ2UvbWFjaGluZV9sZWFybmluZy9kYXRhc2V0cy9yb3BlL3RyYWlucQJYCgAAAG91dHB1dF9kaXJxA1gQAAAAL2V4YW1wbGUvb3V0cHV0c3EEWAQAAABzZWVkcQVLAHUu DOODAD_USE_CLOUDPICKLE=0 DOODAD_CLOUDPICKLE_VERSION=n/a python /mounts/target/main.py'
aws s3 cp --recursive /tmp/example/outputs s3://ge-bair/jaynes/logs/infogan-rope/infogan-rope-2018-03-28-10-18-16-000/
aws s3 cp /home/ubuntu/user_data.log s3://ge-bair/jaynes/logs/infogan-rope/infogan-rope-2018-03-28-10-18-16-000/stdout.log
sleep 20

echo "Now terminate this instance"
EC2_INSTANCE_ID="`wget -q -O - http://169.254.169.254/latest/meta-data/instance-id || die "wget instance-id has failed: $?"`"
# aws ec2 terminate-instances --instance-ids $EC2_INSTANCE_ID --region us-west-2
} >> /home/ubuntu/user_data.log 2>&1
