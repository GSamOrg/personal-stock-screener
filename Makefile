DOCKER_REGISTRY = "192.168.10.10:5000"

build-image:
	docker build -t ${DOCKER_REGISTRY}/screener:latest .

push-image:
	docker push ${DOCKER_REGISTRY}/screener:latest