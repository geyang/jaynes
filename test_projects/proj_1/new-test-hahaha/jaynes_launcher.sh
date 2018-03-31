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



    aws s3 cp s3://ge-bair/jaynes-ssh-exec-test/tmpdnv5tdkc.tar /tmp/tmpdnv5tdkc.tar
    mkdir -p /tmp/tmpdnv5tdkc
    tar -zxf /tmp/tmpdnv5tdkc.tar -C /tmp/tmpdnv5tdkc

    aws s3 cp s3://ge-bair/jaynes-ssh-exec-test/tmpeghhceum.tar /tmp/tmpeghhceum.tar
    mkdir -p /tmp/tmpeghhceum
    tar -zxf /tmp/tmpeghhceum.tar -C /tmp/tmpeghhceum

    echo "making main_log directory /home/ubuntu/new-test-hahaha"
    mkdir -p /home/ubuntu/new-test-hahaha
    echo "made main_log directory" 

    # sudo service docker start
    # pull docker
    docker pull thanard/matplotlib


        aws s3 cp --recursive /home/ubuntu/new-test-hahaha s3://ge-bair/jaynes-ssh-exec-test/new-test-hahaha 


    echo 'Testing nvidia-smi inside docker'
    nvidia-docker run --rm thanard/matplotlib nvidia-smi


    echo 'Now run docker'
    nvidia-docker run  -v '/tmp/tmpdnv5tdkc':'/tmp/tmpdnv5tdkc' -v '/tmp/tmpeghhceum':'/tmp/tmpeghhceum' -v '/home/ubuntu/new-test-hahaha':'/Users/ge/machine_learning/berkeley-playground/packages/jaynes/test_projects/proj_1/new-test-hahaha' --name 0d0a75a4-3459-4231-b6a5-9ba40b2ef5f9 \
    thanard/matplotlib /bin/bash -c 'echo "Running in docker (gpu)";pip install cloudpickle;export PYTHONPATH=$PYTHONPATH:/tmp/tmpdnv5tdkc:/tmp/tmpeghhceum;cd '/Users/ge/machine_learning/berkeley-playground/packages/jaynes/test_projects/proj_1';JAYNES_PARAMS_KEY=gAJ9cQAoWAUAAAB0aHVua3EBY21haW4KdHJhaW4KcQJYBAAAAGFyZ3NxAylYBgAAAGt3YXJnc3EEfXEFKFgBAAAAYXEGWAMAAABoZXlxB1gBAAAAYnEIXXEJKEsASwFLAmVYBwAAAGxvZ19kaXJxClgPAAAAbmV3LXRlc3QtaGFoYWhhcQtYAwAAAGRyeXEMiHV1Lg== python -u -m jaynes.entry'


} >> /home/ubuntu/new-test-hahaha/startup.log