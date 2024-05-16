#!/usr/bin/env bash
set -e
echo "cleaning docker."
docker builder prune -a -f
docker system prune -a -f
echo "building the docker image."
version=$(cat VERSION)
branch=$(git rev-parse --abbrev-ref HEAD)
if [[ "${branch}" != "main" || "$(git status -s)" != "" ]]; then
  version="${version}-dev"
fi
rev=$(git rev-parse --short HEAD)
echo "${version}" > server/VERSION
echo "${rev}" >> server/VERSION
registry="registry.argawaen.net"
image_name="argawaen/owl-delivery-server"
tag="${version}-${rev}"

echo "Creating image: ${registry}/${image_name}:${tag}"

docker build --progress=plain -t ${registry}/${image_name}:${tag} .

if [[ "${branch}" == "main" && "$(git status -s)" == "" ]]; then
  echo "Branch is 'main'-pure, tag it to 'latest'."
  docker tag ${registry}/${image_name}:${tag} ${registry}/${image_name}:latest
  echo "Push the images to registry."
#  docker push ${registry}/${image_name}:${tag}
#  docker push ${registry}/${image_name}:latest
else
  echo "Branch is modified! changes remains local."
fi

