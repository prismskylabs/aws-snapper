# aws-snapper

This is a tool for creating automated snapshots of EBS disk volumes
attached to AWS EC2 instances and deleting old snapshots it created.

aws-snapper is intended to be run as an AWS Lambda job triggered by
an AWS CloudWatch scheduled event. It can also be run as a
command-line script by cron/atd.

## History

This was originally a fork of [x-lhan's aws-autosnap](https://github.com/x-lhan/aws-autosnap), itself a
fork of [evannuil's aws-snapshot-tool](https://github.com/evannuil/aws-snapshot-tool).
Both of these have been incredibly useful for many people over the years.

It has been largely rewritten since then, mostly to use the boto3
package (which is used by the current official AWS CLI) and therefore
requires slightly less effort to configure than the earlier tools.

## Permissions

The IAM user (or IAM role associated with your EC2 instance
profile or AWS Lambda function) will need permission to retrieve
tags on EC2 instances, volumes, and snapshots; create and delete
snapshots; and modify snapshot tags.

If you chose to generate SNS reports, the user/role will also need
permission to publish to the configured SNS topic.

An example IAM policy for all these privileges is [included with
this package](iam.policy.json).

## Command Line Mode

For those who would like to run this on a traditional server using
cron or atd, see [the old documentation](COMMANDLINE.md).

If you are comfortable with the AWS console and want to snapshot
your instances without launching *another* instance, continue
reading this document.

## AWS Lambda Mode

Lambda is a code execution service offered by Amazon Web Services.
When you configure a single Lambda behavior, it runs based on events
you specify **without needing a server of any kind**.

### Lambda Quickstart

For more detailed procedure see [the Lambda instructions](LAMBDA.md).

1. Create an IAM Role that can be assumed by AWS Lambda. Apply
a policy to it similar to the example.

2. Create a new AWS Lambda function with the contents of
aws-snapper.py. Configure the DEFAULTS as appropriate for your
environment.

3. Add a new CloudWatch Schedule Trigger for the Lambda function
at the interval you require.

4. Configure the [tags](TAGS.md) on your EC2 instances (and,
potentially, EBS volumes) that the script will look for.

5. Wait for CloudWatch to trigger the scheduled event or use the
AWS Lambda "Test" button to run manually.
