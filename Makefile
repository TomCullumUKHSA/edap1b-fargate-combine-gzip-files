.DEFAULT_GOAL := help
AWS_REGION = eu-west-2

# Make sure AWS_PROFILE is available in the environment when running locally
ifndef UKHSA_ENVIRONMENT
$(error UKHSA_ENVIRONMENT must be set to the deployment enviroment (lab/ibm/dev/pre/prod/...))
endif
# import config.
# You can change the default config with `make cnf="config_special.env" build`
cnf ?= config.env
include $(cnf)
export $(shell sed 's/=.*//' $(cnf))

.PHONY: all
all: build tag push clean ## Run all commands through to push and clean

.PHONY: help
help: ## Show this!
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' Makefile | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: build
build: ## Build a latest version of the container image
	@printf "Building new version of image...\n"
	docker build \
		-t $(LOCAL_IMAGE_NAME) ./app
	@printf "Build complete "
	@${MAKE} tick

.PHONY: test
test: ## Test the latest version of the container image
	true

test_docker: build ## Test the latest version of the container image
	docker run \
		-e AWS_PROFILE=$(AWS_PROFILE) \
		-v ~/.aws:/root/.aws \
		-e SOURCE_DIR=reference_sf_satellite_organisations \
		-e UKHSA_ENVIRONMENT=${UKHSA_ENVIRONMENT} \
		"$(LOCAL_IMAGE_NAME)"

test_unit: ## Run unit tests
	PYTHONPATH=app python3 -m unittest discover -s tests

.PHONY: tag
tag: ## Tag the latest version of the container image ready to push to ECR
	@printf "Fetching the AWS account number...\n"
	$(eval AWS_ACCOUNT_NUMBER=$(shell aws sts get-caller-identity --query "Account" --output text))
	@printf "Account number: ${AWS_ACCOUNT_NUMBER} "
	@${MAKE} tick
	@printf "Tagging new image as ${VERSION} and latest...\n"
	docker tag $(LOCAL_IMAGE_NAME):latest ${AWS_ACCOUNT_NUMBER}.dkr.ecr.${AWS_REGION}.amazonaws.com/ukhsa-${UKHSA_ENVIRONMENT}-fargate-${ECR_IMAGE_NAME}:${VERSION}
##	docker tag $(LOCAL_IMAGE_NAME):latest ${AWS_ACCOUNT_NUMBER}.dkr.ecr.${AWS_REGION}.amazonaws.com/ukhsa-${UKHSA_ENVIRONMENT}-fargate-${ECR_IMAGE_NAME}:latest
	@printf "Tagging complete "
	@${MAKE} tick

.PHONY: push
push: ## Push the latest version of the container image to ECR
	@printf "Fetching the AWS account number...\n"
	$(eval AWS_ACCOUNT_NUMBER=$(shell aws sts get-caller-identity --query "Account" --output text))
	@printf "Account number: ${AWS_ACCOUNT_NUMBER} "
	@${MAKE} tick
	@printf "Logging into ECR...\n"
	@aws ecr get-login-password --region eu-west-2 | docker login --password-stdin --username AWS "$(AWS_ACCOUNT_NUMBER).dkr.ecr.eu-west-2.amazonaws.com"
	@printf "Pushing image version: ${VERSION} and latest...\n"
	docker push ${AWS_ACCOUNT_NUMBER}.dkr.ecr.${AWS_REGION}.amazonaws.com/ukhsa-${UKHSA_ENVIRONMENT}-fargate-${ECR_IMAGE_NAME}:${VERSION}
## docker push ${AWS_ACCOUNT_NUMBER}.dkr.ecr.${AWS_REGION}.amazonaws.com/ukhsa-${UKHSA_ENVIRONMENT}-fargate-${ECR_IMAGE_NAME}:latest
	@printf "Push complete "
	@${MAKE} tick

.PHONY: clean
clean: ## Clean up the docker environment
	@printf "Cleaning up docker..."
	@printf "\nDead containers... "
	@docker ps -a -q -f 'status=dead' -f 'status=exited' | xargs docker rm --force
	@printf "\nDead containers cleand up..."
	@${MAKE} tick
	@printf "\nDangling images... "
	@docker images -f "dangling=true" -q | xargs docker rmi
	@printf "\nDangling images cleand up..."
	@${MAKE} tick

.PHONY: tick
tick:
	@printf "\033[36m\xE2\x9C\x94\033[0m \n"
