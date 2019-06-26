import copy
import json
import logging
import os

import daiquiri
from invoke import task
from invoke.exceptions import UnexpectedExit, Failure

daiquiri.setup(
    level=logging.DEBUG,
    outputs=(
        daiquiri.output.STDERR,
        # daiquiri.output.Syslog(),
        daiquiri.output.File(directory="."),
    ),
)
logger = daiquiri.getLogger()

docker_compose_project_name = "azurespbootstrap"
docker_compose_azurecli_service = "azurecli"
docker_compose_cli = f"docker-compose --project-name {docker_compose_project_name}"
az_cli = f"{docker_compose_cli} exec -T {docker_compose_azurecli_service} /usr/local/bin/az"
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

    env_vars = [
        "AZURE_LOGIN_USER",
        "AZURE_LOGIN_PASSWORD",
        "AZURE_LOCATION",
        "AZURE_AD_APP_NAME",
        "AZURE_SUBSCRIPTION_NAME",
    ]

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
    print(result1.return_code)

    user = os.environ["AZURE_LOGIN_USER"]
    password = os.environ["AZURE_LOGIN_PASSWORD"]

    cmd = f"{az_cli} login -u '{user}' -p '{password}'"
    logger.debug(f"cmd -> {cmd}".replace(password, "*****"))
    result2 = ctx.run(cmd, hide=True)


@task()
def bootstrap(ctx, role="Reader"):
    logger.debug(f"Service Principal Role -> {role}")
    subscription_name = os.environ["AZURE_SUBSCRIPTION_NAME"]

    if subscription_name.strip() == "" or subscription_name.strip().upper() == "CHANGEME":
        subscription_name = "1fd71af7-cbb0-47c1-913d-e1f145b4c2b7"

    cache = {"subscription_name": subscription_name}

    cmd = f'{az_cli} account show --subscription "{subscription_name}"'
    logger.debug(f"cmd -> {cmd}")
    result = ctx.run(cmd, hide=True)
    logger.debug(f"Subscription info -> {result.stdout.strip()}")
    subscription_info = json.loads(result.stdout.strip())
    logger.debug(f"Subscription info -> {subscription_info}")

    subscription_id = subscription_info["id"]
    logger.debug(f"Subscription ID -> {subscription_id}")
    cache["subscription_id"] = subscription_id

    tenant_id = subscription_info["tenantId"]
    logger.debug(f"Tenant ID -> {tenant_id}")
    cache["tenant_id"] = tenant_id

    ad_app_name = os.environ["AZURE_AD_APP_NAME"]
    if ad_app_name.strip() == "" or ad_app_name.strip().upper() == "CHANGEME":
        ad_app_name = "HSHEIKH-BELRED-TEST"

    cmd = f"{az_cli} role assignment list --assignee='http://{ad_app_name}'"
    logger.debug(f"cmd -> {cmd}")
    try:
        result = ctx.run(cmd, hide=True)
    except UnexpectedExit as e:
        if (
            "ERROR: Operation failed with status: 'Bad Request'. Details: 400 Client Error: Bad Request for url"
            in e.result.stderr
        ):
            logger.debug(f"AD service principal can be created because it doesn't exist already '{ad_app_name}'")
            create_new_sp = True
        else:
            raise e
    else:
        logger.debug(f"Azure existing SP info (raw) -> {result.stdout}")
        ad_existing_sp_info = json.loads(result.stdout)
        ad_sp_info = ad_existing_sp_info[0]
        logger.debug(f"Azure sp ID info -> {ad_sp_info}")
        ad_sp_id = ad_sp_info["principalId"]
        ad_sp_name = ad_sp_info["principalName"]
        ad_sp_display_name = ad_sp_info["principalName"].replace("http://", "")
        ad_sp_password = "HIDDEN"
        create_new_sp = False

    if create_new_sp:
        ad_sp_id = None
        cmd = f"{az_cli} ad sp create-for-rbac --role='{role}' --name='{ad_app_name}'"
        logger.debug(f"cmd -> {cmd}")
        try:
            result = ctx.run(cmd, hide=True)
        except UnexpectedExit as e:
            if (
                "azure.graphrbac.models.graph_error.GraphErrorException: Another object with the same value for property servicePrincipalNames already exists."
                in e.result.stdout
            ):
                logger.warning(f"AD service principal exists for app '{ad_app_name}'")

                cmd = f"{az_cli} ad sp list"
                result = ctx.run(cmd, hide=True)

                logger.warning(f"Azure SP info (raw) -> {result.stdout}")
                ad_sp_list = json.loads(result.stdout)
                for sp in ad_sp_list:
                    if (
                        sp["additionalProperties"]["appDisplayName"] == ad_app_name
                        and ad_app_id in sp["servicePrincipalNames"]
                    ):
                        ad_sp_id = sp["objectId"]
                        # print(sp)
                        break
            else:
                raise e
        else:
            logger.debug(f"Azure sp ID info (raw) -> {result.stdout}")
            ad_sp_info = json.loads(result.stdout)
            logger.debug(f"Azure sp ID info -> {ad_sp_info}")
            ad_sp_id = ad_sp_info["appId"]
            ad_sp_name = ad_sp_info["name"]
            ad_sp_display_name = ad_sp_info["displayName"]
            ad_sp_password = ad_sp_info["password"]

    logger.debug(f"Azure AD sp ID -> {ad_sp_id}")
    cache["ad_sp_id"] = ad_sp_id
    cache["ad_sp_name"] = ad_sp_name
    cache["ad_sp_display_name"] = ad_sp_display_name
    cache["ad_sp_password"] = ad_sp_password

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

    if os.path.exists(cache_file) and cache["ad_sp_password"].upper() == "HIDDEN":
        logger.info(f"Not refreshing cache file {cache_file} because the password may be overwritten")
    else:
        json.dump(file_cache, open(cache_file, "w"), indent=2, sort_keys=True)
