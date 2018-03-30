
        #!/bin/bash
        mkdir -p /home/ubuntu/dqn/some_experiment-gpu
        {
            # clear main_log
            truncate -s 0 /home/ubuntu/dqn/some_experiment-gpu/startup.log
            
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
        
            
            
            aws s3 cp s3://ge-bair/docker-gpu-test/tmp98hers6c.tar /tmp/tmp98hers6c.tar
            mkdir -p /tmp/tmp98hers6c
            tar -zxf /tmp/tmp98hers6c.tar -C /tmp/tmp98hers6c
            
            aws s3 cp s3://ge-bair/docker-gpu-test/tmphyg7yiiv.tar /tmp/tmphyg7yiiv.tar
            mkdir -p /tmp/tmphyg7yiiv
            tar -zxf /tmp/tmphyg7yiiv.tar -C /tmp/tmphyg7yiiv
            
            echo "making main_log directory /home/ubuntu/dqn/some_experiment-gpu"
            mkdir -p /home/ubuntu/dqn/some_experiment-gpu
            echo "made main_log directory" 
            while true; do
                echo "uploading..." 
                aws s3 cp --recursive /home/ubuntu/dqn/some_experiment-gpu s3://ge-bair/docker-gpu-test/dqn/some_experiment-gpu 
                sleep 15
            done & echo "sync /home/ubuntu/dqn/some_experiment-gpu initiated" 
            while true; do
                if [ -z $(curl -Is http://169.254.169.254/latest/meta-data/spot/termination-time | head -1 | grep 404 | cut -d \  -f 2) ]
                then
                    logger "Running shutdown hook." 
                aws s3 cp --recursive /home/ubuntu/dqn/some_experiment-gpu s3://ge-bair/docker-gpu-test/dqn/some_experiment-gpu 
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
            
            
                aws s3 cp --recursive /home/ubuntu/dqn/some_experiment-gpu s3://ge-bair/docker-gpu-test/dqn/some_experiment-gpu 
            
            
            echo 'Testing nvidia-smi inside docker'
            nvidia-docker run --rm thanard/matplotlib nvidia-smi
            
            
            echo 'Now run docker'
            nvidia-docker run  -v '/tmp/tmp98hers6c':'/tmp/tmp98hers6c' -v '/tmp/tmphyg7yiiv':'/tmp/tmphyg7yiiv' -v '/home/ubuntu/dqn/some_experiment-gpu':'/Users/ge/machine_learning/berkeley-playground/packages/jaynes/test_projects/proj_1/dqn/some_experiment-gpu' --name 0c61d357-b6d0-4d13-b829-fcc1cb219bdf \
            thanard/matplotlib /bin/bash -c 'echo "Running in docker (gpu)";pip install cloudpickle;export PYTHONPATH=$PYTHONPATH:/tmp/tmp98hers6c:/tmp/tmphyg7yiiv;cd '/Users/ge/machine_learning/berkeley-playground/packages/jaynes/test_projects/proj_1';JAYNES_PARAMS_KEY=gAJ9cQAoWAUAAAB0aHVua3EBY21haW4KdHJhaW4KcQJYBAAAAGFyZ3NxAylYBgAAAGt3YXJnc3EEfXEFKFgBAAAAYXEGWAMAAABoZXlxB1gBAAAAYnEIXXEJKEsASwFLAmVYBwAAAGxvZ19kaXJxClgXAAAAZHFuL3NvbWVfZXhwZXJpbWVudC1ncHVxC3V1Lg== python -u -m jaynes.entry'
            
            
            echo "Now terminate this instance"
            EC2_INSTANCE_ID="`wget -q -O - http://169.254.169.254/latest/meta-data/instance-id || die "wget instance-id has failed: $?"`"
            aws ec2 terminate-instances --instance-ids $EC2_INSTANCE_ID --region us-west-2
        
        } >> /home/ubuntu/dqn/some_experiment-gpu/startup.log
        