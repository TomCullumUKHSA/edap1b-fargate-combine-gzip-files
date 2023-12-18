# Logging Utility Package

This module enables JSON logging for the different components of the EDAP system.

Usage:

```python
import logging

from appinfo import APPLICATION_NAME, APPLICATION_STAGE, APPLICATION_VERSION, ENVIRONMENT_NAME
import loggingutil

loggingutil.setup_logging(
    application_name=APPLICATION_NAME,
    application_stage=APPLICATION_STAGE,
    application_version=APPLICATION_VERSION,
    environment_name=ENVIRONMENT_NAME
)

...

logger = logging.getLogger()
logger.info("My log message")
```

## Using the Package as a git submodule

One way to use this modules without requiring to pass GitHub tokens when creating the docker image, is to create a git
submodule pointing to this repository. For example, to make use of this repository in a lambda's code:

```bash
# change directory to lambda's repo code
cd lambda-ingest2raw-...
# add submodule (notice that the path is relative to the repository making use of the module)
git submodule add "../ukhsa-support-loggingutil.git" "app/modules/loggingutil"
# git submodule init??
```

Whenever there is an update in the submodule, all the components that make use of it need to update the submodule and
re-create the docker image:

```bash
# change directory to lambda's repo code
cd lambda-ingest2raw-...
# change directory to submodule
cd app/modules/loggingutil
git checkout main && git pull
# also, to update all submodules submodules:
# git submodule foreach git pull origin main
# go back to project's root
cd ../../..
# commit changes
git commit -am "Update loggingutil submodule"
```

The Dockerfile also needs a modification in order to install dependencies in the ``app/modules`` directory:

```diff
 COPY .. .

+# install local dependencies
+RUN for module in modules/*/; do pip install --no-cache-dir "$module"; done
```
