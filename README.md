# Introduction

An Azure Service Principal is required for applications like Terraform to authenticate.

This is a quick start guide on bootstrapping Service Principal in Azure. All steps are done
using ``make``. It serves as both the admin interface as well as documentation
on how those steps are performed.

# Prerequities

Obtain login to Azure with owner permissions for at least one subscription. It
will be used to create a Service Principal that applications (like Terraform) will use 
to authenticate to Azure.

Install ``make``.

Install Docker.

Install ``docker-compose`` and make sure it's in *[PATH](https://kb.iu.edu/d/acar)*.

Install ``jp`` with ``pip install jmespath-terminal``.

Install ``jq``.

# Bootstrap

Export these environment variables before running ``make``. If any one of them is not set, ``make``
will fail.

* AZURE_CLI_VERSION - Which version of Azure CLI 2.0 to use. This guide was written with *2.0.21*.
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

        $ make

Once the bootstrap is complete, it will create a bunch of dot files in the current directory.
**Keep these safe because they may contain sensitive information.**

# Terraform

Some of the information from these dot files is required by Terraform.
Get this information:

        $ make export-terraform-values

The output of the above should be inserted in the appropriate file (e.g.
~/.profile, ~/.bashrc, whatever) and sourced to be used by Terraform.

        export TF_VAR_AZURE_SUBSCRIPTION_ID=SECRET_CHANGEME_1
        export TF_VAR_AZURE_TENANT_ID=SECRET_CHANGEME_2
        export TF_VAR_AZURE_CLIENT_ID=SECRET_CHANGEME_3
        export TF_VAR_AZURE_CLIENT_SECRET=SECRET_CHANGEME_4

# Teardown

To remove the Service Principal you can use the *service-principal-teardown* target.

        $ make service-principal-teardown

# Troubleshooting

``make`` can run into numerous errors. The first place to get an idea of what may
have gone wrong is to read the error. Then read Makefile to understand the steps performed
before the error occurred.

If the error is:

        Assign owner role to Service Principal in the subscription [REDACTED]
        make: *** [azure-bootstrap] Error 1

Check file *.azure_role_json* was created and it contains an error. If yes, remove the file
and run ``make`` again.
