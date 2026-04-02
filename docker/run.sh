#!/bin/bash

IMAGE="aipyapp/aipy:latest"
DOCKER="docker run -v $(pwd)/aipy.toml:/app/aipy.toml -v $(pwd)/work:/app/work"

mkdir -p work

# 配置可选的 mitmproxy 代理环境变量和网络隔离选项
# 如果需要开启网络隔离（比如只允许访问特定靶机网段），请在 DOCKER 变量中添加 --network ctf_net
# DOCKER="$DOCKER -e HTTP_PROXY=http://127.0.0.1:8080 -e HTTPS_PROXY=http://127.0.0.1:8080"

if [ "$1" = "--ttyd" ]; then
    ${DOCKER} -d --name aipy-ttyd -p 8080:80 $IMAGE --ttyd
elif [ "$1" = "--mitm" ]; then
    # 启动 mitmproxy 并行模式
    ${DOCKER} -it --rm --name aipy $IMAGE sh -c "mitmdump & aipy --role ctf_hacker"
else
    ${DOCKER} -it --rm --name aipy $IMAGE
fi
