## What is this?

*aws-iot-baseline* is an implementation starter kit of a python-based [Internet of Things](https://aws.amazon.com/iot) (IoT) device and [Amazon Web Services](https://aws.amazon.com) (AWS) cloud stack.

The device firmware is packaged as a [Docker](https://www.docker.com/get-started) image so that it can run on any hardware that supports the Docker Engine. This also makes testing the code on your development machine a lot easier.

The cloud stack is deployed using the [AWS Cloud Development Kit](https://docs.aws.amazon.com/cdk/latest/guide/home.html) (AWS CDK), which generates an AWS CloudFormation template and deploys the stack to the configured account and region.

## What do I need?

In order to build and deploy the code, you must meet certain prerequisites. This includes installing Docker, the AWS CDK, and ensuring that your AWS credentials are configured. This guide does not provide the setup for those tools, but does have links below to help you get to them.

#### Docker

https://docs.docker.com/get-docker

#### AWS Cloud Development Kit

See [Getting Started](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html) in the AWS Cloud Development Kit User Guide for details.

#### AWS Credentials

See [Configuration Basics](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html) in the AWS Command Line Interface User Guide for details.

## How do I use it?

Before you get started building, there are a few configurations available at the root of the project. You can edit the file `<project-root>/config.json` with the options below, or leave the defaults until you have a need for them to change:

* `app_name` - String; The name of the AWS CloudFormation Stack. This will also be used when packaging the device firmware and cloud lambdas. Defaults to "iot-baseline".

* `topic_prefix` - String; The name that will be used in the MQTT topic (e.g. `$aws/rules/<topic_prefix>/#`). This is different than `app_name` as it has character restrictions: `^[a-zA-Z0-9_]+$`. Defaults to "baseline".

* `cacert` - Dictionary; Certificate subject fields to be used when generating an AWS IoT CA Certificate. The same subject fields will be used for device certificates. The `days` field is the validity length of the certificates.

* `debug_lambda_roles` - Boolean; When set to true, all users in the account will be able to assume the lambda roles. This is used for testing lambda code through local docker.

* `debug_api_gateway_errors` - Boolean; When set to true, Amazon API Gateway errors will return a stacktrace.

### The Cloud Stack

#### Features

1) Building, Deploying, and Integration Testing (see next sections).

2) AWS IoT Rules Engine; A Topic Rule is deployed that listens on the MQTT topic `$aws/rules/<topic_prefix>/#`. From there the payload is sent to an AWS Lambda for handling. This lambda supports provisioning, and log messages that go into Amazon CloudWatch.

3) AWS IoT CA Certificate; The custom root CA will be generated using an AWS CloudFormation Custom Resource. The certificate will be registered with AWS IoT Core, and it's private key will be stored in the AWS Secrets Manager.

4) AWS IoT Policies; There are three policies that are created: Initial, Intermediate, and Standard. The initial policy is attached to the birthing certificate used during provisioning, and only has permissions for using the provisioning API. The intermediate policy is attached to the "unverified" Thing Group and also only has permissions for using the provisioning API. The difference between the initial and intermediate policies is related to the `iot:ClientId` used when connecting an MQTT client. The initial policy requires a 128 character ClientId, while the intermediate policy requires the ClientId to be the Thing name associated with the newly signed certificate. The standard policy is attached to the "verified" Thing Group and allows for regular use of the AWS IoT Core features.

5) AWS Systems Manager Parameter Store; Since the AWS CDK creates the AWS Lambda packages before the AWS CloudFormation template is deployed, any dynamic settings like resource ARNs are stored in the AWS Systems Manager Parameter Store instead of the JSON config file embedded in the lambda packages.

6) Amazon VPC; The entire cloud stack is deployed into it's own Amazon VPC. This makes initial development and testing easier as you don't need to worry about breaking any existing resources.

7) Web Frontend; A Thing management website is written with React and gets deployed to S3. The password for login is generated randomly and stored in the AWS Systems Manager Parameter Store, or you can specify it through the root config.json file.

8) Amazon API Gateway; REST APIs for the Web Frontend are available, along with a custom Authorizer that checks JWT session credentials.

#### Building

To build the AWS CloudFormation template and assets, without deploying:

```bash
$ cd <project-root>
$ bash scripts/cloud-build.sh
```

The template will be written to `.build/cloud/template.yaml`.

#### Deploying

To build and deploy the AWS CloudFormation Stack:

```bash
$ cd <project-root>
$ bash scripts/cloud-deploy.sh
```

Any input prompts you receive are part of the AWS CDK.

#### Testing

To test AWS Lambda code changes locally without deploying every time, you can run them in Docker. Example test scripts are available for the ingest lambda, which is used for the AWS IoT Rules Engine. The scripts will first create the lambda ZIP packages by executing the same code the AWS CDK runs during a build / deployment. The ZIP packages will then be unpacked and mounted to a Docker container which mimics the runtime environment of a real AWS Lambda. 

```bash
$ cd <project-root>
$ bash scripts/cloud-test-integration-lambda-provision.sh
```

### The Device Firmware

#### Features

1) Building, Deploying, and Integration Testing (see next sections).

2) Mosquitto MQTT Bridge; An MQTT bridge will run in its own process which connect to AWS IoT Core's Message Broker. This allows you to have multiple local MQTT clients across multiple processors as needed. All you need to do is connect to localhost, and you will be bridge into AWS IoT Core.

3) Provisioning; The provisioning provided is very similar to the AWS IoT Core Fleet Provisioning, however it is a custom implementation. This is because the fleet provisioning does not support a custom root CA, which is used here. Each build of the device firmware includes the initial (birthing) certificate to make an authorized and secure first connection. The device uses initial connection to submit a certificate signing request and receive back a Thing name, and the certificate signed by the custom root CA. At this point the Thing is placed into an "unverified" Thing Group which signifies that it has not connected with the new credentials yet. The device then reconnects with the new credentials and is placed into the "verified" Thing Group, which allows it to use the regular AWS IoT Core features. Both the initial certificate, and the *unverified* group are restricted by an IoT Policy that only allows communication with the provisioning API.

4) Jobs; Each of the device firmware services run as a separate process. The jobs are the same. When a new job is received through the MQTT topics, the details will be persisted and it will get started through Supervisor. The job process can then read the details from file, perform any action, and then report the success or failure. Included are two sample jobs, one that keeps open an MQTT client, and another that only creates the client when it needs to send the result.

5) Named Shadows; The shadows service will handling persisting the details to file and reporting back that it has been received. Included is a sample shadow service, however if multiple shadows are used, it can be modified to handling persistence generically.

6) Logging; Provided is an MQTT Logging Handler which will send all log messages to the Rules Engine, and then get stored into Amazon CloudWatch.

7) Secure Tunnels - SSH; The tunnels service will handle notifications from AWS IoT Core for starting up a Secure Tunnel for SSH. The pre-built `localproxy` binary is built for Alpine Linux, however there is a `localproxy-build.sh` script that can be modified for other distributions. There are also two scripts provided for testing Secure Tunnels under the host directory: `localproxy-ssh.sh` and `localproxy-ssh-destination.sh`. **WARNING**: Each tunnel opened costs $5 USD (as of this writing), so be careful when testing as the cost can add up quickly.

8) Over-The-Air Updates; TBD

9) Packaging as DEB or RPM; TBD

#### Building

To package the device firmware, run:

```bash
$ cd <project-root>
$ bash scripts/device-build.sh
```

The device build script will lookup some values from AWS IoT Core, the AWS Systems Manager Parameter Store, and the AWS Secrets Manager... namely, the MQTT endpoint, and initial certificate for connecting and provisioning. This means you must deploy the stack first.

The package will be written to `.build/device/<app_name>.tar.gz`. This includes the Docker image and all host-side scripts (e.g. installing the Docker image, and starting it up). To have the device firmware autostart on host reboots, you will need to set it up as a systemd service, init.d script, cronjob, or whatever your host operating system supports.

#### Testing

After deploying the cloud stack and building the device firmware package, you can run device integration tests using Docker. The device firmware will startup in Docker and provision like a device, and then you can use the AWS CLI to interact with it. Example scripts are available which test the jobs and shadow services.

```bash
$ cd <project-root>
$ bash scripts/device-test-integration-jobs-sample1.sh
```

#### Host Files

Included in the device firmware package are scripts that can be found under `<project-root>/device/host/files`. These scripts help facilitate the Docker image installation and startup. During installation there are also pre/post-install scripts that will get triggered. You can add additional logic into these scripts to easily check any host conditions and fail or rollback an update as necessary. When an update is installed, first a snapshot will be taken of the Docker volume, and if there needs to be a rollback, the snapshot will be restored so that any changes made are undone. Also included is an `attach.sh` script which can be used to connect into a running container to perform debugging or other tasks.

## Project Structure

```text
aws-iot-baseline
├── cloud
│   ├── cdk
│   │   ├── baseline_cdk
│   │   │   ├── resources  ........................... AWS CloudFormation Stack resources
│   │   │   │   ├── cfnres  .......................... custom resource lambdas
│   │   │   │   │   └── XXXX
│   │   │   │   │       ├── index.py
│   │   │   │   │       └── requirements.txt
│   │   │   │   ├── cfnres_XXXX.py  .................. custom resource
│   │   │   │   ├── lambda_XXXX.py  .................. lambda resource
│   │   │   │   ├── lambda_XXXX.txt  ................. lambda dependencies
│   │   │   │   └── [...]
│   │   │   ├── util
│   │   │   └── cdk.py
│   │   └── requirements.txt  ........................ cdk dependencies
│   ├── scripts
│   ├── src
│   │   └── baseline_cloud
│   │       ├── authorizer  .......................... lambda that can be used for an API Gateway Authorizer
│   │       ├── core
│   │       └── ingest  .............................. lambda that will be used with the AWS IoT Rules Engine
│   │           ├── clients
│   │           │   ├── log.py  ...................... lambda for receiving log entries to put into Amazon CloudWatch
│   │           │   └── provision.py  ................ lambda for provisioning, to sign the certificate request and create the thing entry
│   │           └── handler.py
│   └── config.json  ................................. cloud / lambda settings that will get merged with the root config.json
├── device
│   ├── container
│   │   ├── files  ................................... templates / scripts that will get merged into the Docker image
│   │   │   └── alpine
│   │   │       ├── localproxy  ...................... AWS Local Proxy built using an Alpine Docker container
│   │   │       └── localproxytest
│   │   ├── scripts
│   │   │   ├── connect-usbserial.sh  ................ script for connecting to Raspberry Pi OS through a console cable
│   │   │   └── localproxy-build.sh  ................. build AWS Local Proxy built using an Alpine Docker container
│   │   ├── src
│   │   │   └── baseline_device
│   │   │       ├── service
│   │   │       │   ├── provision.py  ................ provisioning called on first boot to register device with AWS IoT Core
│   │   │       │   ├── jobs.py  ..................... tracks jobs from AWS IoT Core, and then runs them as separate processes through supervisor
│   │   │       │   ├── jobs  ........................ jobs from AWS IoT Core, triggered by jobs.py
│   │   │       │   ├── shadows  ..................... named shadows from AWS IoT Core
│   │   │       │   ├── supervisor 
│   │   │       │   │   └── events.py  ............... tracks supervisor events like process stop / exit, and logging
│   │   │       │   └── main.py
│   │   │       └── util
│   │   ├── config.json  ............................. device settings that will get merged with the root config.json
│   │   └── requirements.txt  ........................ the device firmware dependencies
│   └── host
│       ├── files  ................................... templates / scripts that will get merged into the firmware package
│       └── scripts
│           ├── localproxy-ssh.sh  ................... run AWS Local Proxy (ssh source) using an Alpine Docker container
│           └── localproxy-ssh-destination.sh  ....... run AWS Local Proxy (ssh destination) using an Alpine Docker container
├── web  ............................................. web frontend built with React
├── scripts
│   ├── cloud-build.sh  .............................. build, but not deploy, the AWS CloudFormation Stack
│   ├── cloud-deploy.sh  ............................. build and deploy the AWS CloudFormation Stack
│   ├── cloud-test-integration-lambda.sh  ............ build the ingest lambda package and run it in docker with a test event
│   ├── cloud-test-integration-lambda-log.sh  ........ run an integration test in docker against the /things/<thing-name>/log topic
│   ├── cloud-test-integration-lambda-provision.sh  .. run an integration test in docker against the /clients/<client-id>/provision topic
│   ├── device-build.sh  ............................. build the device firmware package
│   ├── device-test-integration.sh  .................. provision a device in docker, run the integration test, and cleanup the thing entry
│   ├── device-test-integration-jobs-sample1.sh  ..... run an integration test in docker against the device jobs service
│   ├── device-test-integration-jobs-sample2.sh  ..... run an integration test in docker against the device jobs service
│   └── device-test-integration-shadows-sample.sh  ... run an integration test in docker against the device shadow service
├── .build
├── LICENSE
├── README.md
└── config.json  ..................................... settings that will be merged into the AWS CDK, cloud lambdas, and device firmware configs
```

## Known Issues

Some versions of NodeJS cause problems with the AWS Cloud Development Kit. You can workaround this by downgrading NodeJS to version 12.13.1:

```bash
rm -rf /usr/local/lib/node_modules
brew install nvm
nvm install 12.13.1
npm install -g n
npm install -g aws-cdk
```

You can add this to your user profile:

```bash
export NVM_DIR="$HOME/.nvm"
[ -s "$(brew --prefix nvm)/nvm.sh" ] && . "$(brew --prefix nvm)/nvm.sh"
[ -s "$(brew --prefix nvm)/etc/bash_completion.d/nvm" ] && . "$(brew --prefix nvm)/etc/bash_completion.d/nvm"
```

Related error messages:

```bash
jsii-runtime.js throws "RangeError: Maximum call stack size exceeded"
```

```bash
jsii throws BrokenPipeError if subprocess was previously called
```