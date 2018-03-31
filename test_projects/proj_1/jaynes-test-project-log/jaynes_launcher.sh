#!/bin/bash
mkdir -p /home/ubuntu/jaynes-test-project-log
{
    # clear main_log
    truncate -s 0 /home/ubuntu/jaynes-test-project-log/startup.log

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



    aws s3 cp s3://ge-bair/jaynes-ssh-exec-test/tmp284ey6mh.tar /tmp/tmp284ey6mh.tar
    mkdir -p /tmp/tmp284ey6mh
    tar -zxf /tmp/tmp284ey6mh.tar -C /tmp/tmp284ey6mh

    aws s3 cp s3://ge-bair/jaynes-ssh-exec-test/tmp4kheqpk5.tar /tmp/tmp4kheqpk5.tar
    mkdir -p /tmp/tmp4kheqpk5
    tar -zxf /tmp/tmp4kheqpk5.tar -C /tmp/tmp4kheqpk5

    echo "making main_log directory /home/ubuntu/jaynes-test-project-log"
    mkdir -p /home/ubuntu/jaynes-test-project-log
    echo "made main_log directory" 

    # sudo service docker start
    # pull docker
    docker pull thanard/matplotlib


        aws s3 cp --recursive /home/ubuntu/jaynes-test-project-log s3://ge-bair/jaynes-ssh-exec-test/jaynes-test-project-log 


    echo 'Testing nvidia-smi inside docker'
    nvidia-docker run --rm thanard/matplotlib nvidia-smi


    echo 'Now run docker'
    nvidia-docker run  -v '/tmp/tmp284ey6mh':'/tmp/tmp284ey6mh' -v '/tmp/tmp4kheqpk5':'/tmp/tmp4kheqpk5' -v '/home/ubuntu/jaynes-test-project-log':'/Users/ge/machine_learning/berkeley-playground/packages/jaynes/test_projects/proj_1/jaynes-test-project-log' --name 5420aa31-fb79-4e1d-85c5-93c61d0e028a \
    thanard/matplotlib /bin/bash -c 'echo "Running in docker (gpu)";pip install cloudpickle;export PYTHONPATH=$PYTHONPATH:/tmp/tmp284ey6mh:/tmp/tmp4kheqpk5;cd '/Users/ge/machine_learning/berkeley-playground/packages/jaynes/test_projects/proj_1';JAYNES_PARAMS_KEY=gAJ9cQAoWAUAAAB0aHVua3EBY21haW4KdHJhaW4KcQJYBAAAAGFyZ3NxAylYBgAAAGt3YXJnc3EEfXEFKFgBAAAAYXEGWAMAAABoZXlxB1gBAAAAYnEIXXEJKEsASwFLAmVYBwAAAGxvZ19kaXJxClgXAAAAamF5bmVzLXRlc3QtcHJvamVjdC1sb2dxC1gDAAAAZHJ5cQyIdXUu python -u -m jaynes.entry'


} >> /home/ubuntu/jaynes-test-project-log/startup.log