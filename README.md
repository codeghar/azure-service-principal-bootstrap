# Introduction

An Azure Service Principal is required for applications like Terraform to authenticate.

This is a quick start guide on bootstrapping Service Principal in Azure. All steps are done
using *tasks.py* with the [Invoke](http://docs.pyinvoke.org/en/latest/) library. It serves as both the admin interface
as well as documentation on how those steps are performed.

# Prerequities

Obtain login to Azure with owner permissions for at least one subscription. It
will be used to create a Service Principal that applications (like Terraform) will use 
to authenticate to Azure.

Install:

* Python (3.6+ recommended)
* pipenv
* Docker

# pipenv

After cloning this repo, cd into this directory and use ``pipenv`` to install prereq Python packages.

        $ pipenv install

# Bootstrap

Export these environment variables before running ``make``. If any one of them is not set, ``make``
will fail.

* AZURE_CLI_VERSION - Which version of Azure CLI 2.0 to use. This guide was written with *2.0.20*.
* AZURE_LOGIN_USER - Login user name for Azure CLI (same as Azure Portal)
* AZURE_LOGIN_PASSWD - Login password for Azure CLI
* AZURE_LOCATION - Name of location in Azure to stand up the environment
* AZURE_AD_APP_NAME - Name of the Active Directory (AD) app to create in Azure (any unique name)
* AZURE_AD_APP_PASSWORD - Come up with a password for the AD app to create in Azure
* AZURE_SUBSCRIPTION_NAME - Name of the Azure subscription to use (look it up on Azure Portal)

For your convenience, the file *environment_variables* contains dummy values for these variables but
they're commented out. Change the values to suit your needs, uncomment the lines as needed, and 
source the file.

        $ #edit environment_variables
        $ source ./environment_variables

Create Service Principal and Application in Azure.

        $ pipenv shell
        $ inv bootstrap
        $ exit

Once the bootstrap is complete, it will create a *cache.json* file in the current directory.
**Keep this information safe because it may contain sensitive information.**

# Teardown

TODO

# Troubleshooting

*tasks.py* can run into numerous errors. The first place to get an idea of what may
have gone wrong is to read the error and *inv.log* file. Then read *tasks.py* to understand the steps performed
before the error occurred.
