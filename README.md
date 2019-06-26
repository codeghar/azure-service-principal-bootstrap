# Introduction

An Azure Service Principal is required for applications like Terraform to authenticate.

This is a quick start guide on bootstrapping Service Principal in Azure. All steps are done using *tasks.py* with
the [Invoke](http://docs.pyinvoke.org/en/latest/) library. It serves as both the admin interface as well as
documentation on how those steps are performed.

# Prerequities

Obtain login to Azure with owner permissions for at least one subscription. It will be used to create a Service
Principal that applications (like Terraform) will use to authenticate to Azure.

Install:

* Python (3.7+ recommended)
* pipenv
* Docker
* [direnv](https://github.com/direnv/direnv)

# pipenv

After cloning this repo, cd into this directory and use ``pipenv`` to install required Python packages.

    $ pipenv install

# Bootstrap

Export these environment variables before running ``invoke``. If any one of them is not set, ``invoke`` will fail.

* AZURE_LOGIN_USER - Login user name for Azure CLI (same as Azure Portal)
* AZURE_LOGIN_PASSWD - Login password for Azure CLI
* AZURE_LOCATION - Name of location in Azure to stand up the environment
* AZURE_AD_APP_NAME - Name of the Active Directory (AD) app to create in Azure (any unique name)
* AZURE_SUBSCRIPTION_NAME - Name of the Azure subscription to use (look it up on Azure Portal)

For your convenience, the file *.envrc* contains empty values for these variables. Add the values to suit your needs
and source the file.

    $ direnv allow .
    $ #edit .envrc
    $ direnv reload

Create Service Principal and Application in Azure.

    $ pipenv shell
    $ invoke containerup
    $ invoke bootstrap
    $ exit

Once the bootstrap is complete, it will:

- Create a Service Principal with _Reader_ role. To override the default role, run it as
``invoke bootstrap --role Contributor``, for example.
- Create a *cache.json* file in the current directory. **Keep this information safe.**

# Teardown

Get the Azure AD App ID,

    $ az role assignment list --assignee http://"${AZURE_AD_APP_NAME}"

Delete the service principal using the _principalId_ from above step,

    $ az ad sp delete --id PRINCIPALID_FROM_ABOVE

# Troubleshooting

*tasks.py* can run into numerous errors. The first place to get an idea of what may have gone wrong is to read the
error on stdout and *invoke.log*. Then read *tasks.py* to understand the steps performed before the error occurred.

# Interactive Setup

Read official documentation first: [Create an Azure service principal with Azure CLI](https://docs.microsoft.com/en-us/cli/azure/create-an-azure-service-principal-azure-cli?view=azure-cli-latest)

Use interactive login and follow instructions. You'll be asked to enter a code on some dynamically generated link.

    $ az login

The output of the interactive login process will contain some important information.

* _name_ is the subscription name
* _id_ is the subscription ID
* _tenantId_ is the tenant ID

    $ export AZURE_SUBSCRIPTION_NAME
    $ AZURE_SUBSCRIPTION_NAME=name_FROM_OUTPUT_OF_PREVIOUS_STEP

    $ export AZURE_SUBSCRIPTION_ID
    $ AZURE_SUBSCRIPTION_ID=id_FROM_OUTPUT_OF_PREVIOUS_STEP

    $ export AZURE_LOCATION
    $ AZURE_LOCATION='eastus2'

    $ export AZURE_AD_APP_NAME
    $ AZURE_AD_APP_NAME=UNIQUE_NAME_OF_YOUR_CHOICE

    $ export AZURE_TENANT_ID
    $ AZURE_TENANT_ID=tenantId_FROM_OUTPUT_OF_PREVIOUS_STEP

Create Service Principal. If you're a *Contributor* yourself, you cannot run this command successfully. An *Owner*
needs to do it for you.

    $ az ad sp create-for-rbac --role='Reader/or/Contributor' --name="${AZURE_AD_APP_NAME}"

The output from above contains _appId_, which is to be exported as an environment variable. This _appId_ is the ID of
the newly created Service Principal.

    $ export AZURE_AD_SP_ID
    $ AZURE_AD_SP_ID=appId_FROM_OUTPUT_OF_PREVIOUS_STEP
