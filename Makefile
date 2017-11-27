DOCKER_COMPOSE_AZURECLI_SERVICE := "azurecli"
WHICH_AZURECLI := "/usr/local/bin/az"
DOCKER_COMPOSE_PROJECT_NAME := azurespbootstrap
# AZURE_CLI_VERSION := $(if $(AZURE_CLI_VERSION),$(AZURE_CLI_VERSION),2.0.21)


.PHONY: service-principal-bootstrap
service-principal-bootstrap: check-which-jq azure-prereqs
	@echo 'Capture ID of subscription "$(AZURE_SUBSCRIPTION_NAME)" in file .azure_subscription_id'
	@{ \
		if [ ! -f .azure_subscription_id ]; then \
			docker-compose --project-name $(DOCKER_COMPOSE_PROJECT_NAME) exec $(DOCKER_COMPOSE_AZURECLI_SERVICE) $(WHICH_AZURECLI) account show --subscription "$(AZURE_SUBSCRIPTION_NAME)" --query "id" | sed 's/"//g' > .azure_subscription_id ; \
		fi ; \
	}

	@echo 'Capture Tenant ID in file .azure_subscription_tenant_id'
	@{ \
		if [ ! -f .azure_subscription_tenant_id ]; then \
			docker-compose --project-name $(DOCKER_COMPOSE_PROJECT_NAME) exec $(DOCKER_COMPOSE_AZURECLI_SERVICE) $(WHICH_AZURECLI) account show --subscription "$(AZURE_SUBSCRIPTION_NAME)" --query "tenantId" | sed 's/"//g' > .azure_subscription_tenant_id ; \
		fi ; \
	}

	@echo 'Create AD App $(AZURE_AD_APP_NAME)'
	@# https://blogs.msdn.microsoft.com/eugene/2016/11/03/creating-azure-resources-with-terraform/
	@# https://docs.microsoft.com/en-us/azure/active-directory/develop/active-directory-protocols-oauth-code
	@# https://docs.microsoft.com/en-in/azure/azure-resource-manager/resource-group-create-service-principal-portal#check-azure-subscription-permissions
	@{ \
		if [ ! -f .azure_client_id_json ]; then \
			docker-compose --project-name $(DOCKER_COMPOSE_PROJECT_NAME) exec $(DOCKER_COMPOSE_AZURECLI_SERVICE) $(WHICH_AZURECLI) ad app create --display-name $(AZURE_AD_APP_NAME) --homepage http://$(AZURE_AD_APP_NAME) --identifier-uris http://$(AZURE_AD_APP_NAME) --password '$(AZURE_AD_APP_PASSWORD)' > .azure_client_id_json ; \
		fi ; \
	}

	@{ \
		if [ ! -f .azure_client_id ]; then \
			jq ".appId" .azure_client_id_json | sed 's/"//g' > .azure_client_id ; \
		fi ; \
	}

	@echo 'Create Service Principal for AD App $(AZURE_AD_APP_NAME)'
	@# https://stackoverflow.com/a/29085684
	@{ \
		if [ ! -f .azure_ad_sp_object_id_json ]; then \
			while read line; \
			do export CLIENT_ID="$$line"; \
			done < .azure_client_id; \
			echo $$CLIENT_ID; \
			docker-compose --project-name $(DOCKER_COMPOSE_PROJECT_NAME) exec $(DOCKER_COMPOSE_AZURECLI_SERVICE) $(WHICH_AZURECLI) ad sp create --id "$$CLIENT_ID" > .azure_ad_sp_object_id_json; \
		fi ; \
	}

	@{ \
		if [ ! -f .azure_ad_sp_object_id ]; then \
			jq ".objectId" .azure_ad_sp_object_id_json | sed 's/"//g' > .azure_ad_sp_object_id ; \
		fi ; \
	}

	@# https://docs.microsoft.com/en-us/cli/azure/role/assignment?view=azure-cli-latest
	@echo 'Assign owner role to Service Principal in the subscription $(AZURE_SUBSCRIPTION_NAME)'
	@{ \
		if [ ! -f .azure_role_json ]; then \
			while read line; \
			do export SP_OBJECT_ID="$$line"; \
			done < .azure_ad_sp_object_id; \
			while read line; \
			do export SUBSCRIPTION_ID="$$line"; \
			done < .azure_subscription_id; \
			docker-compose --project-name $(DOCKER_COMPOSE_PROJECT_NAME) exec $(DOCKER_COMPOSE_AZURECLI_SERVICE) $(WHICH_AZURECLI) role assignment create --assignee "$$SP_OBJECT_ID" --role "Owner" --scope "/subscriptions/$$SUBSCRIPTION_ID" > .azure_role_json ;\
		fi ; \
	}

	@echo 'Check all required local files are created'
	@{ \
		fail=FALSE ; \
		if [ ! -f .azure_subscription_id ]; then \
			echo "Could not find Subscription ID. File .azure_subscription_id is missing." ; \
			fail=TRUE ; \
		fi ; \
		if [ ! -f .azure_subscription_tenant_id ]; then \
			echo "Could not find Tenant ID. File .azure_subscription_tenant_id is missing." ; \
			fail=TRUE ; \
		fi ; \
		if [ ! -f .azure_client_id ]; then \
			echo "Could not find Service Principal ID. File .azure_client_id is missing." ; \
			fail=TRUE ; \
		fi ; \
		if [ ! -f .azure_role_json ]; then \
			echo "Could not find role assignment. File .azure_role_json is missing." ; \
			fail=TRUE ; \
		fi ; \
		if [ $$fail = TRUE ]; then \
			exit 500 ; \
		fi ; \
	}


.PHONY: check-which-docker-compose
check-which-docker-compose:
	which docker-compose 1>/dev/null


.PHONY: check-which-jp
check-which-jp:
	which jp.py 1>/dev/null


.PHONY: check-which-jq
check-which-jq:
	which jq 1>/dev/null


.PHONY: check-env-vars-are-set
check-env-vars-are-set: check-which-docker-compose
	@echo 'Check environment variable AZURE_CLI_VERSION is set on my machine'
	@test -n "$(AZURE_CLI_VERSION)"
	@echo 'Check environment variable AZURE_LOGIN_USER is set on my machine'
	@test -n "$(AZURE_LOGIN_USER)"
	@echo 'Check environment variable AZURE_LOGIN_PASSWD is set on my machine'
	@test -n "$(AZURE_LOGIN_PASSWD)"
	@echo 'Check environment variable AZURE_LOCATION is set on my machine'
	@test -n "$(AZURE_LOCATION)"
	@echo 'Check environment variable AZURE_AD_APP_NAME is set on my machine'
	@test -n "$(AZURE_AD_APP_NAME)"
	@echo 'Check environment variable AZURE_AD_APP_PASSWORD is set on my machine'
	@test -n "$(AZURE_AD_APP_PASSWORD)"
	@echo 'Check environment variable AZURE_SUBSCRIPTION_NAME is set on my machine'
	@test -n "$(AZURE_SUBSCRIPTION_NAME)"


.PHONY: update
update:
	@docker-compose --project-name $(DOCKER_COMPOSE_PROJECT_NAME) pull


.PHONY: up
up: check-env-vars-are-set
	@docker-compose --project-name $(DOCKER_COMPOSE_PROJECT_NAME) up -d azurecli


.PHONY: down
down:
	@docker-compose --project-name $(DOCKER_COMPOSE_PROJECT_NAME) down


.PHONY: exec
exec:
	@docker-compose --project-name $(DOCKER_COMPOSE_PROJECT_NAME) exec azurecli /bin/sh


.PHONY: start
start: check-env-vars-are-set
	@docker-compose --project-name $(DOCKER_COMPOSE_PROJECT_NAME) start azurecli


.PHONY: stop
stop: check-env-vars-are-set
	@docker-compose --project-name $(DOCKER_COMPOSE_PROJECT_NAME) stop azurecli


.PHONY: ps
ps:
	@docker-compose --project-name $(DOCKER_COMPOSE_PROJECT_NAME) ps


.PHONY: status
status: ps


.PHONY: azure-prereqs
azure-prereqs: check-env-vars-are-set
	@echo 'Start Azure CLI container'
	@docker-compose --project-name $(DOCKER_COMPOSE_PROJECT_NAME) up -d $(DOCKER_COMPOSE_AZURECLI_SERVICE) 1>/dev/null

	@echo 'Login with Azure CLI'
	@docker-compose --project-name $(DOCKER_COMPOSE_PROJECT_NAME) exec $(DOCKER_COMPOSE_AZURECLI_SERVICE) $(WHICH_AZURECLI) login -u "$(AZURE_LOGIN_USER)" -p "$(AZURE_LOGIN_PASSWD)" 1>/dev/null


.PHONY: export-terraform-values
export-terraform-values: service-principal-bootstrap
	@echo 'Run these `export` commands before running Terraform'
	@{ \
		while read line; \
				do echo "export TF_VAR_AZURE_SUBSCRIPTION_ID=$$line" ; \
		done < .azure_subscription_id; \
	}

	@{ \
		while read line; \
				do echo "export TF_VAR_AZURE_TENANT_ID=$$line" ; \
		done < .azure_subscription_tenant_id; \
	}

	@{ \
		while read line; \
				do echo "export TF_VAR_AZURE_CLIENT_ID=$$line" ; \
		done < .azure_client_id; \
	}

	@echo "export TF_VAR_AZURE_CLIENT_SECRET=$(AZURE_AD_APP_PASSWORD)"


.PHONY: service-principal-teardown
service-principal-teardown: check-which-jp check-which-jq azure-prereqs
	@{ \
		if [ ! -f .azure_teardown_role_ids ]; then \
			docker-compose --project-name $(DOCKER_COMPOSE_PROJECT_NAME) exec $(DOCKER_COMPOSE_AZURECLI_SERVICE) $(WHICH_AZURECLI) role assignment list | jp.py '[].{id: id, name: properties.principalName, scope: properties.scope, role: properties.roleDefinitionName}' | jp.py "[?name=='http://$(AZURE_AD_APP_NAME)']".id | jq .[] | sed 's/"//g' > .azure_teardown_role_ids ; \
		fi ; \
	}

	@{ \
		if [ -f .azure_teardown_role_ids ]; then \
			while read line; \
				do echo $$line ; \
				docker-compose --project-name $(DOCKER_COMPOSE_PROJECT_NAME) exec $(DOCKER_COMPOSE_AZURECLI_SERVICE) $(WHICH_AZURECLI) role assignment delete --ids "$$line" ; \
			done < .azure_teardown_role_ids; \
		fi ; \
	}

	@{ \
		if [ ! -f .azure_teardown_sp_ids ]; then \
			docker-compose --project-name $(DOCKER_COMPOSE_PROJECT_NAME) exec $(DOCKER_COMPOSE_AZURECLI_SERVICE) $(WHICH_AZURECLI) ad sp list --query '[].{id: appId, name: displayName, names: servicePrincipalNames}' | jp.py "[?name=='$(AZURE_AD_APP_NAME)']".id | jq .[] | sed 's/"//g' > .azure_teardown_sp_ids ; \
		fi ; \
	}

	{ \
		if [ -f .azure_teardown_sp_ids ]; then \
			while read line; \
				do echo $$line ; \
				docker-compose --project-name $(DOCKER_COMPOSE_PROJECT_NAME) exec $(DOCKER_COMPOSE_AZURECLI_SERVICE) $(WHICH_AZURECLI) ad sp delete --id "$$line" ; \
			done < .azure_teardown_sp_ids; \
		fi ; \
	}


# https://stackoverflow.com/a/26339924
.PHONY: list
list:
	@$(MAKE) -pRrq -f $(lastword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$' | xargs
