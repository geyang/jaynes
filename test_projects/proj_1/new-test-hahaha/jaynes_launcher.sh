#!/bin/bash
mkdir -p /home/ubuntu/new-test-hahaha
{
    # clear main_log
    truncate -s 0 /home/ubuntu/new-test-hahaha/startup.log

    die() { status=$1; shift; echo "FATAL: $*"; exit $status; }

    curl "https://s3.amazonaws.com/aws-cli/awscli-bundle.zip" -o "awscli-bundle.zip"
    yes A | unzip awscli-bundle.zip
    echo "finished unziping the awscli bundle"
    sudo ./awscli-bundle/install -i /usr/local/aws -b /usr/local/bin/aws
    echo "aws cli is installed"


    export AWS_DEFAULT_REGION=us-west-1

    EC2_INSTANCE_ID="`wget -q -O - http://169.254.169.254/latest/meta-data/instance-id`"
    aws ec2 create-tags --resources $EC2_INSTANCE_ID --tags Key=Name,Value=jaynes-ssh-exec-test --region us-west-2
    aws ec2 create-tags --resources $EC2_INSTANCE_ID --tags Key=exp_prefix,Value=jaynes-ssh-exec-test --region us-west-2



    aws s3 cp s3://ge-bair/jaynes-ssh-exec-test/tmpimiv1g5a.tar /tmp/tmpimiv1g5a.tar
    mkdir -p /tmp/tmpimiv1g5a
    tar -zxf /tmp/tmpimiv1g5a.tar -C /tmp/tmpimiv1g5a

    aws s3 cp s3://ge-bair/jaynes-ssh-exec-test/tmp_suuk09z.tar /tmp/tmp_suuk09z.tar
    mkdir -p /tmp/tmp_suuk09z
    tar -zxf /tmp/tmp_suuk09z.tar -C /tmp/tmp_suuk09z

    echo "making main_log directory /home/ubuntu/new-test-hahaha"
    mkdir -p /home/ubuntu/new-test-hahaha
    echo "made main_log directory" 
    while true; do
        echo "uploading..." 
        aws s3 cp --recursive /home/ubuntu/new-test-hahaha s3://ge-bair/jaynes-ssh-exec-test/new-test-hahaha 
        sleep 15
    done & echo "sync /home/ubuntu/new-test-hahaha initiated" 
    while true; do
        if [ -z $(curl -Is http://169.254.169.254/latest/meta-data/spot/termination-time | head -1 | grep 404 | cut -d \  -f 2) ]
        then
            logger "Running shutdown hook." 
        aws s3 cp --recursive /home/ubuntu/new-test-hahaha s3://ge-bair/jaynes-ssh-exec-test/new-test-hahaha 
            break
        else
            # Spot instance not yet marked for termination. This is hoping that there's at least 3 seconds
            # between when the spot instance gets marked for termination and when it actually terminates.
            sleep 3
        fi
    done & echo main_log sync initiated


    # sudo service docker start
    # pull docker
    docker pull thanard/matplotlib


        aws s3 cp --recursive /home/ubuntu/new-test-hahaha s3://ge-bair/jaynes-ssh-exec-test/new-test-hahaha 


    echo 'Testing nvidia-smi inside docker'
    nvidia-docker run --rm thanard/matplotlib nvidia-smi


    echo 'Now run docker'
    nvidia-docker run  -v '/tmp/tmpimiv1g5a':'/tmp/tmpimiv1g5a' -v '/tmp/tmp_suuk09z':'/tmp/tmp_suuk09z' -v '/home/ubuntu/new-test-hahaha':'/Users/ge/machine_learning/berkeley-playground/packages/jaynes/test_projects/proj_1/new-test-hahaha' --name fb4d2488-99ab-4f33-b49e-e9818e1ead2f \
    thanard/matplotlib /bin/bash -c 'echo "Running in docker (gpu)";pip install cloudpickle;export PYTHONPATH=$PYTHONPATH:/tmp/tmpimiv1g5a:/tmp/tmp_suuk09z;cd '/Users/ge/machine_learning/berkeley-playground/packages/jaynes/test_projects/proj_1';JAYNES_PARAMS_KEY=gAJ9cQAoWAUAAAB0aHVua3EBY21haW4KdHJhaW4KcQJYBAAAAGFyZ3NxAylYBgAAAGt3YXJnc3EEfXEFKFgBAAAAYXEGWAMAAABoZXlxB1gBAAAAYnEIXXEJKEsASwFLAmVYBwAAAGxvZ19kaXJxClgPAAAAbmV3LXRlc3QtaGFoYWhhcQtYAwAAAGRyeXEMiHV1Lg== python -u -m jaynes.entry'


} >> /home/ubuntu/new-test-hahaha/startup.log