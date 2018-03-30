#!/bin/bash
rm -rf /root/code
echo 'Fetching code archive from  gs://openai-ge-bucket/archives/0cfp5hx6p8o1.zip'
gsutil cp gs://openai-ge-bucket/archives/0cfp5hx6p8o1.zip /root/code.zip
unzip -q -d /root/code /root/code.zip
mkdir -p "/root/results/maml-parameter-sweep/2017-10-20/1705-maml-parameter-sweep/170528.872132-maml-MediumWorld-v0-n_grad(1)-VPG-SGD-PPO-Adam-alpha(0.001)-beta(0.0001)-n_tasks(128)-env_norm(False)"; gsutil -m rsync -r -d "gs://openai-ge-bucket/results/maml-parameter-sweep/2017-10-20/1705-maml-parameter-sweep/170528.872132-maml-MediumWorld-v0-n_grad(1)-VPG-SGD-PPO-Adam-alpha(0.001)-beta(0.0001)-n_tasks(128)-env_norm(False)" "/root/results/maml-parameter-sweep/2017-10-20/1705-maml-parameter-sweep/170528.872132-maml-MediumWorld-v0-n_grad(1)-VPG-SGD-PPO-Adam-alpha(0.001)-beta(0.0001)-n_tasks(128)-env_norm(False)"
upload_results() {
    gsutil -q -m rsync -r -d "/root/results/maml-parameter-sweep/2017-10-20/1705-maml-parameter-sweep/170528.872132-maml-MediumWorld-v0-n_grad(1)-VPG-SGD-PPO-Adam-alpha(0.001)-beta(0.0001)-n_tasks(128)-env_norm(False)" "gs://openai-ge-bucket/results/maml-parameter-sweep/2017-10-20/1705-maml-parameter-sweep/170528.872132-maml-MediumWorld-v0-n_grad(1)-VPG-SGD-PPO-Adam-alpha(0.001)-beta(0.0001)-n_tasks(128)-env_norm(False)"
    echo 'startupscript.sh uploaded results to "gs://openai-ge-bucket/results/maml-parameter-sweep/2017-10-20/1705-maml-parameter-sweep/170528.872132-maml-MediumWorld-v0-n_grad(1)-VPG-SGD-PPO-Adam-alpha(0.001)-beta(0.0001)-n_tasks(128)-env_norm(False)"'
}
while [ ! -f /tmp/DONE ]
do
    upload_results
    sleep 30
done &
export OPENAI_USER=ge
export PATH=/opt/conda/bin:$PATH
export PKG_CONFIG_PATH=/opt/conda/lib/pkgconfig
curl -o /usr/bin/Xdummy https://gist.githubusercontent.com/jonasschneider/e69568ffa18c00278246e4c100bd9d54/raw/839adad1342be1ac7ed8b10e341dc11b02db602e
chmod +x /usr/bin/Xdummy
nohup Xdummy 2>/dev/null 1>/dev/null &
export DISPLAY=':0'

for cpunum in $(cat /sys/devices/system/cpu/cpu*/topology/thread_siblings_list | sed 's/-/,/g' | cut -s -d, -f2- | tr ',' '
' | sort -un); do
echo 0 > /sys/devices/system/cpu/cpu$cpunum/online
done

pip install -e /root/code/rl-algs-2 --ignore-installed
pip install ruamel.yaml mock pygame visdom
pip install cloudpickle --ignore-installed
export PYTHONPATH=/root/code/exploration_in_meta_learning_reproduction_code/e_maml_ge:$PYTHONPATH
export PYTHONPATH=/root/code/exploration_in_meta_learning_reproduction_code/packages:$PYTHONPATH
python -m jaynes.entry 3.6.1eJy1VUtzG0UQ3pX8kNfv2LxCgBBeEiDLNiG8QkxiBwGLHLOOk+VhhtHOeGejffXsysZUqSoXR84BDvAr+Bv+CfwELhw4cedAb8tlXClMFQdKVdvdMz0z39fz9eh+yfPCpCvSwOuEcuGUb7GdIAzZTjf28iCJLTCqZ6dGvCNZ1pGDfAvMs1Pb3SDMg5jl+6m0oORWDMNYTYS8jTGUD2DIgeGqbdCvbM95zMNJL7NkXDgWjLhTuOLo0Dw6xG/p6Adz04BRdwQHQ44bL0HlAYw5YK0fwHit5i7jRGMrkzpr+LIRcU8FsWSh5DoOYr+hwzoP/ay+3NAeD8NGNw/ChXQfJgjY1ZBHbcGvwaT9o8dOsDOrvZ/LzIKpmgPT7hBmcu1nMOOW0N2JYZbwdPZo9Fwf5mo5zDvwmF3uweN9eMKBJ3vw1HoPzm/D09WaMqrKVKdpq3+keUEht2cceBa5PYfclv4bN9+TBbWLatL+TU2rGTWrENvziO2SAy8U2F7sw0sOvNyDVxBbdRtqZ2CbwINzxGUI8+j7AtmrBbLXHHh93R3DOS+JdwKfYSXqB7DwABruKI7i+Ux3Y1g8gKWa2/l38PLbNEw0L7THsOSRzPnJJNMy1YnokjJJIA2JGoxChjtlng7SPGvgScdjA9rLSPsy0kZEbyDlyw68aZs9uNKHtxx4uwfvqEXveO3C6bXWMWwL3s2wKu9tw9VHalKimvyEfISZG/dMVhIlsmVRJjskhsgO402SMyKGyY6KEbIVMUp2TKDnD3IsLC8546gCcibEGNlJYZGdEuNkp8UE2Rk6bpadE5No59i8MPBq3i+u5poDK9V1UmrBCz4gebWkCLrR3USHor67CNcPWxfLdsUetk3bcMuYcGejCTfI22yuwSp5Gxu3YI12ui54BDcf5vBhlfQ+uHVouiYGTfiIWohKiTcEH1Mo410W80jCJ+540SuBznKWaCE12JQQM5kmnsrgU9IMPhQ862TQcqcpSrlGKeNDgxtlsE6jbZ57iuVBJLNcphncIn3GzNdcsMHQBiXKXR6eHv3MHS5aN0wVB4cotVFmsEkaDuJYaoYNBLdp8SBOUjwn+A7hbhFc0mWRdIcqSuHfOXdpJwcZaXw3fHCJtKYYJc1j+JwgrN28sdWEL9yZAndClFHjGY/SUMKXOXxVc3v/U7vgQqmxdDG2jK8DUd8jORR1xk2krmd7UqZFA22788fyYSezjGbha3sRO+ASThtm5ZHfxOmoVDGBFYL8xgGuHLWpWn1oYzt6DojiBZJ92HHA74FSzTP/RLJuO4iKGloQqOYB3HOgU/RmuA1Rtbmy0W798sfPfzZXzl/59fcLq3X7vswdnjs9iGXxTfC78BfGDijF '/root/results/maml-parameter-sweep/2017-10-20/1705-maml-parameter-sweep/170528.872132-maml-MediumWorld-v0-n_grad(1)-VPG-SGD-PPO-Adam-alpha(0.001)-beta(0.0001)-n_tasks(128)-env_norm(False)'
touch /tmp/DONE
sleep 1 # so serial port output is all there
gcloud compute instances get-serial-port-output "maml-parameter-sweep-2017-10-20-170528-872132" --zone us-west1-b 2>/dev/null | gzip -9 > "/root/results/maml-parameter-sweep/2017-10-20/1705-maml-parameter-sweep/170528.872132-maml-MediumWorld-v0-n_grad(1)-VPG-SGD-PPO-Adam-alpha(0.001)-beta(0.0001)-n_tasks(128)-env_norm(False)/serial-port-output.gz"
upload_results
 gcloud compute instances delete "maml-parameter-sweep-2017-10-20-170528-872132" --zone us-west1-b --delete-disks=all
