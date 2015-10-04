# aws-snapper

This is a script for managing automated snapshots of disk volumes attached to EC2 instances. It was
originally a fork of [x-lhan's aws-autosnap](https://github.com/x-lhan/aws-autosnap), itself a fork
of [evannuil's aws-snapshot-tool](https://github.com/evannuil/aws-snapshot-tool).
Both of these have been incredibly useful for many people over the years.

aws-snapper is intended to be run as a daily cron job. When it is run, it scans EC2 Instances that
you have marked for backup and creates snapshots accordingly. It will also delete old snapshots
based on your preferences.

This version has been converted to use the boto3 package (which is used by the current official
AWS CLI) and therefore requires slightly less effort to configure than the earlier tools.

## Usage

### Authentication

aws-snapper authenticates using botocore, so there's no reason to give it credentials directly.

If you are running it on a non-EC2 platform, you should install the AWS CLI and use its
`aws configure` to store your Access Key ID and Secret Access Key in `~/.aws`. See
["Configuring the AWS Command Line Interface"](http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html)
for more details.

If you are running it on an EC2 instance, you should run it from an instance with an IAM Role
attached; This way, no credentials will be stored on the EC2 instance itself. See
[IAM Roles for Amazon EC2](http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html)
for more details.

### Region(s)

aws-snapper will default to using the region you specify as the AWS CLI default when running
`aws configure`. You may override this on the command line by providing a Region or list of Regions
to manage.

Each Region you include will be checked for pending Snapshots and create them as necessary.

### Snapshot Schedule

Configuration of the snapshot schedule is performed on EC2 resources themselves: Instances and
Volumes.

Any Instance you would like snapshotted should have a tag with a key of `autosnap` and a value of
the backup frequency in days (e.g. `1` for daily, `7` for weekly) and another tag with a key of
`autosnap_retain` with a value of the number of snapshots to keep (e.g. `30` for a full month of
nightly snapshots).

All Volumes attached to an Instance with a snapshot schedule will be snapshotted on that schedule,
unless the Volumes have tags that override the Instance's values. For example, if an Instance has
an `autosnap_retain` value of `7` but one of its Volumes has an `autosnap_retain` of `20`, twenty
snapshots of that volume will be kept and seven of the other volumes.

Any resource tagged with a key of `autosnap_ignore` (the value doesn't matter) will be skipped by
aws-snapper. This can be used to avoid scanning of Instances with many Volumes, or to skip specific
Volumes on an Instance that has a snapshot schedule (such as the root device on a database server).

Note: aws-snapper will not delete any snapshots that it did not make itself (as indicated by the
`snapshot_tool` tag on snapshots), nor will it include them in the retention/frequency calculations.

### SNS (optional)

You may also configure aws-snapper to send snapshot reports when it has completed. It will publish
the reports to an SNS Topic of your choice, provided it has permission to do so.

SNS can be configured to send to email, webhooks, or other destinations.

To use SNS reporting, make sure the credentials (`~/.aws`) or EC2 IAM Role can publish to the SNS
Topic and specify the topic using its ARN on the command line with
`--sns-topic arn:aws:sns:region:account-id:topicname`.

### Tag Prefix (optional)

aws-snapper uses AWS resource tags to keep track of Instances, Volumes, and Snapshots it is
managing. By default, the Key for these tags is prefixed with `autosnap`. If you would like the
script to use another prefix, you can change it on the command line with `--prefix foo`.

If you use this option, the configuration tags on Instances and Volumes will be changed to e.g.
`foo_retain` and `foo_ignore`.

This option allows multiple instances of aws-snapper to operate on the same Region without
interfering with each other.

## Examples

## Running In A Container

### Docker

### Vagrant
