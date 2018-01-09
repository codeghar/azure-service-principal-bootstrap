import copy
import json
import os

import daiquiri
from invoke import task
from invoke.exceptions import UnexpectedExit, Failure

daiquiri.setup(outputs=(
    daiquiri.output.STDERR,
    # daiquiri.output.Syslog(),
    daiquiri.output.File(directory="."),
))
logger = daiquiri.getLogger()

docker_compose_project_name = "azurespbootstrap"
docker_compose_azurecli_service = "azurecli"
docker_compose_cli = f"docker-compose --project-name {docker_compose_project_name}"
az_cli = f"{docker_compose_cli} exec {docker_compose_azurecli_service} /usr/local/bin/az"
cache_file = os.path.join(".", "cache.json")


@task
def prerequisites(ctx):
    clis = ["docker-compose"]
    for cli in clis:
        try:
            ctx.run("which {}".format(cli), hide=True)
        except UnexpectedExit as e:
            logger.error(f"Command not found -> {cli}")
            raise e

    env_vars = ["AZURE_CLI_VERSION",
                "AZURE_LOGIN_USER",
                "AZURE_LOGIN_PASSWORD",
                "AZURE_LOCATION",
                "AZURE_AD_APP_NAME",
                "AZURE_AD_APP_PASSWORD",
                "AZURE_SUBSCRIPTION_NAME"]

    errors = []
    for var in env_vars:
        try:
            os.environ[var]
        except KeyError:
            errors.append(f"Environment variable not set: {var}")

    try:
        assert not errors
    except AssertionError as e:
        logger.error("\n".join(errors))
        raise e


@task
def containerpull(ctx):
    cmd = f"{docker_compose_cli} pull {docker_compose_azurecli_service}"
    logger.debug(f"cmd -> {cmd}")
    result = ctx.run(cmd, hide=True)


@task(pre=[prerequisites, containerpull])
def containerup(ctx):
    cmd = f"{docker_compose_cli} up -d {docker_compose_azurecli_service}"
    logger.debug(f"cmd -> {cmd}")
    result1 = ctx.run(cmd, hide=True)

    user = os.environ["AZURE_LOGIN_USER"]
    password = os.environ["AZURE_LOGIN_PASSWORD"]

    cmd = f"{az_cli} login -u '{user}' -p '{password}'"
    logger.debug(f"cmd -> {cmd}".replace(password, '*****'))
    result2 = ctx.run(cmd, hide=True)


@task(pre=[containerup])
def bootstrap(ctx):
    subscription_name = os.environ["AZURE_SUBSCRIPTION_NAME"]

    cache = {"subscription_name": subscription_name}

    cmd = f"{az_cli} account show --subscription \"{subscription_name}\""
    logger.debug(f"cmd -> {cmd}")
    result = ctx.run(cmd, hide=True)
    subscription_info = json.loads(result.stdout)
    logger.debug(f"Subscription info -> {subscription_info}")

    subscription_id = subscription_info["id"]
    logger.debug(f"Subscription ID -> {subscription_id}")
    cache["subscription_id"] = subscription_id

    tenant_id = subscription_info["tenantId"]
    logger.debug(f"Tenant ID -> {tenant_id}")
    cache["tenant_id"] = tenant_id

    ad_app_id = None
    ad_app_name = os.environ["AZURE_AD_APP_NAME"]
    cache["ad_app_name"] = ad_app_name
    ad_app_password = os.environ["AZURE_AD_APP_PASSWORD"]
    # https://blogs.msdn.microsoft.com/eugene/2016/11/03/creating-azure-resources-with-terraform/
    # https://docs.microsoft.com/en-us/azure/active-directory/develop/active-directory-protocols-oauth-code
    # https://docs.microsoft.com/en-in/azure/azure-resource-manager/resource-group-create-service-principal-portal#check-azure-subscription-permissions
    cmd = f"{az_cli} ad app create --display-name {ad_app_name} --homepage http://{ad_app_name} --identifier-uris http://{ad_app_name} --password '{ad_app_password}'"
    logger.debug(f"cmd -> {cmd}")
    try:
        result = ctx.run(cmd, hide=True)
    except UnexpectedExit as e:
        if "azure.graphrbac.models.graph_error.GraphErrorException: Another object with the same value for property identifierUris already exists." in e.result.stdout:
            logger.warning(f"AD app '{ad_app_name}' exists")

            cmd = f"{az_cli} ad app list"
            result = ctx.run(cmd, hide=True)

            ad_app_list = json.loads(result.stdout)
            for app in ad_app_list:
                if app["displayName"] == ad_app_name:
                    ad_app_id = app["appId"]
                    break
        else:
            raise e
    else:
        ad_app_info = result.stdout
        logger.debug(f"Azure app ID info -> {ad_app_info}")
        ad_app_id = ad_app_info["appId"]
    logger.debug(f"AD app ID -> {ad_app_id}")
    cache["ad_app_id"] = ad_app_id

    ad_sp_id = None
    cmd = f"{az_cli} ad sp create --id {ad_app_id}"
    logger.debug(f"cmd -> {cmd}")
    try:
        result = ctx.run(cmd, hide=True)
    except UnexpectedExit as e:
        if "azure.graphrbac.models.graph_error.GraphErrorException: Another object with the same value for property servicePrincipalNames already exists." in e.result.stdout:
            logger.warning(f"AD service principal exists for app '{ad_app_name}' (ID '{ad_app_id}')")

            cmd = f"{az_cli} ad sp list"
            result = ctx.run(cmd, hide=True)

            ad_sp_list = json.loads(result.stdout)
            for sp in ad_sp_list:
                if sp["additionalProperties"]["appDisplayName"] == ad_app_name and ad_app_id in sp["servicePrincipalNames"]:
                    ad_sp_id = sp["objectId"]
                    # print(sp)
                    break
        else:
            raise e
    else:
        ad_sp_info = result.stdout
        logger.debug(f"Azure sp ID info -> {ad_sp_info}")
        ad_sp_id = ad_sp_info["objectId"]
    logger.debug(f"Azure AD sp ID -> {ad_sp_id}")
    cache["ad_sp_id"] = ad_sp_id

    role_assignment_id = None
    cmd = f"{az_cli} role assignment create --assignee '{ad_sp_id}' --role 'Owner' --scope '/subscriptions/{subscription_id}'"
    logger.debug(f"cmd -> {cmd}")
    try:
        result = ctx.run(cmd, hide=True)
    except UnexpectedExit as e:
        if "The role assignment already exists." in e.result.stdout:
            logger.warning(f"Role assignment exists for app '{ad_app_name}' (ID '{ad_app_id}') and service principal ID '{ad_sp_id}'")

            cmd = f"{az_cli} role assignment list"
            result = ctx.run(cmd, hide=True)

            role_assignment_list = json.loads(result.stdout)
            for ra in role_assignment_list:
                if ra["properties"]["principalId"] == ad_sp_id:
                    role_assignment_id = ra["id"]
                    break
        else:
            raise e
    else:
        role_assignment_info = result.stdout
        logger.debug(f"Azure role assignment info -> {role_assignment_info}")
        role_assignment_id = role_assignment_info["id"]
    logger.debug(f"Role assignment ID -> {role_assignment_id}")
    cache["role_assignment_id"] = role_assignment_id

    print(json.dumps(cache, sort_keys=True, indent=2))

    file_cache = dict()
    try:
        file_cache = json.load(open(cache_file))
    except FileNotFoundError:
        file_cache = {"bootstrap": copy.deepcopy(cache)}
    except json.decoder.JSONDecodeError:
        logger.error("Cache file {cache_file} exists but is not a valid JSON file. Fix it or remove it and retry.")
        exit(211)
    else:
        file_cache["bootstrap"] = cache

    json.dump(file_cache, open(cache_file, "w"))
