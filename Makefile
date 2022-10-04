IMG_NAME := bidenboye

current_dir = $(shell pwd)

build:
	docker build -t ${IMG_NAME} .

run:
	mkdir -p db
	docker stop bidenboye || true && docker rm bidenboye || true
	docker run --rm \
		--name bidenboye \
		-d \
		-v ${current_dir}:/repo -w /repo \
		-v db:/db \
		--env-file .env \
		${IMG_NAME} \
		python3 main.py
