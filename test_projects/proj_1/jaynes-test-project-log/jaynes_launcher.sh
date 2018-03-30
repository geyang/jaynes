#!/bin/bash
mkdir -p /home/ubuntu/jaynes-test-project-log
{
    # clear main_log
    truncate -s 0 /home/ubuntu/jaynes-test-project-log/startup.log

    die() { status=$1; shift; echo "FATAL: $*"; exit $status; }

    curl "https://s3.amazonaws.com/aws-cli/awscli-bundle.zip" -o "awscli-bundle.zip"
    yes A | unzip awscli-bundle.zip
    echo "finished unziping the awscli bundle"
    ./awscli-bundle/install -i /usr/local/aws -b /usr/local/bin/aws
    echo "aws cli is installed"


    export AWS_DEFAULT_REGION=us-west-1

    EC2_INSTANCE_ID="`wget -q -O - http://169.254.169.254/latest/meta-data/instance-id`"
    aws ec2 create-tags --resources $EC2_INSTANCE_ID --tags Key=Name,Value=docker-gpu-test --region us-west-2
    aws ec2 create-tags --resources $EC2_INSTANCE_ID --tags Key=exp_prefix,Value=docker-gpu-test --region us-west-2



    aws s3 cp s3://ge-bair/docker-gpu-test/tmpj9wxp9hy.tar /tmp/tmpj9wxp9hy.tar
    mkdir -p /tmp/tmpj9wxp9hy
    tar -zxf /tmp/tmpj9wxp9hy.tar -C /tmp/tmpj9wxp9hy

    aws s3 cp s3://ge-bair/docker-gpu-test/tmpfj2t66tu.tar /tmp/tmpfj2t66tu.tar
    mkdir -p /tmp/tmpfj2t66tu
    tar -zxf /tmp/tmpfj2t66tu.tar -C /tmp/tmpfj2t66tu

    echo "making main_log directory /home/ubuntu/jaynes-test-project-log"
    mkdir -p /home/ubuntu/jaynes-test-project-log
    echo "made main_log directory" 
    while true; do
        echo "uploading..." 
        aws s3 cp --recursive /home/ubuntu/jaynes-test-project-log s3://ge-bair/docker-gpu-test/jaynes-test-project-log 
        sleep 15
    done & echo "sync /home/ubuntu/jaynes-test-project-log initiated" 
    while true; do
        if [ -z $(curl -Is http://169.254.169.254/latest/meta-data/spot/termination-time | head -1 | grep 404 | cut -d \  -f 2) ]
        then
            logger "Running shutdown hook." 
        aws s3 cp --recursive /home/ubuntu/jaynes-test-project-log s3://ge-bair/docker-gpu-test/jaynes-test-project-log 
            break
        else
            # Spot instance not yet marked for termination. This is hoping that there's at least 3 seconds
            # between when the spot instance gets marked for termination and when it actually terminates.
            sleep 3
        fi
    done & echo main_log sync initiated


    # service docker start
    # pull docker
    docker pull thanard/matplotlib


        aws s3 cp --recursive /home/ubuntu/jaynes-test-project-log s3://ge-bair/docker-gpu-test/jaynes-test-project-log 


    echo 'Testing nvidia-smi inside docker'
    nvidia-docker run --rm thanard/matplotlib nvidia-smi


    echo 'Now run docker'
    nvidia-docker run  -v '/tmp/tmpj9wxp9hy':'/tmp/tmpj9wxp9hy' -v '/tmp/tmpfj2t66tu':'/tmp/tmpfj2t66tu' -v '/home/ubuntu/jaynes-test-project-log':'/Users/ge/machine_learning/berkeley-playground/packages/jaynes/test_projects/proj_1/jaynes-test-project-log' --name 2186b183-b9a2-48ff-a633-71df54994b27 \
    thanard/matplotlib /bin/bash -c 'echo "Running in docker (gpu)";pip install cloudpickle;export PYTHONPATH=$PYTHONPATH:/tmp/tmpj9wxp9hy:/tmp/tmpfj2t66tu;cd '/Users/ge/machine_learning/berkeley-playground/packages/jaynes/test_projects/proj_1';JAYNES_PARAMS_KEY=gAJ9cQAoWAUAAAB0aHVua3EBY21haW4KdHJhaW4KcQJYBAAAAGFyZ3NxAylYBgAAAGt3YXJnc3EEfXEFKFgBAAAAYXEGWAMAAABoZXlxB1gBAAAAYnEIXXEJKEsASwFLAmVYBwAAAGxvZ19kaXJxClgXAAAAamF5bmVzLXRlc3QtcHJvamVjdC1sb2dxC3V1Lg== python -u -m jaynes.entry'


    echo "Now terminate this instance"
    EC2_INSTANCE_ID="`wget -q -O - http://169.254.169.254/latest/meta-data/instance-id || die "wget instance-id has failed: $?"`"
    aws ec2 terminate-instances --instance-ids $EC2_INSTANCE_ID --region us-west-2

} >> /home/ubuntu/jaynes-test-project-log/startup.log