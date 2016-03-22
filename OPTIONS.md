# Options

These settings can be passed to aws-snapper in three places, depending
on how you would like to run the script:

* By editing the DEFAULTS dict at the top of the script itself.

* Through command line options like `--name` or `--sns-arn`.

* By passing a JSON object as a parameter to the AWS Lambda function.

The setting names are the same no matter how the script is invoked.

### ec2_regions

This tells the script which regions to scan for EC2 instances with
the appropriate tags.

On the command line any parameter not prefixed with `--` is assumed
to be an EC2 region.

### sns-arn or sns_arn

aws-snapper generates a report when it finishes of all the snapshots
created and deleted during that run. By default this report is
printed to standard output.

You may also configure aws-snapper to send snapshot reports to an
AWS SNS topic, provided it has permission to do so.

SNS can then be configured to send the report to email, webhooks,
or other destinations.

To use SNS reporting, make sure the credentials (`~/.aws`) or IAM
role can publish to the SNS topic and specify the topic using
with the sns-arn option.

`--sns-arn` is the command line option.

### tag_prefix

aws-snapper uses AWS resource tags to keep track of instances,
volumes, and snapshots it is managing. By default, the Key for
these tags is prefixed with `autosnap`. If you would like the
script to use another prefix, you can use this setting.

If you use this option, the configuration tags on instances and
volumes will be changed to e.g. `foo_retain` and `foo_ignore`.

This option allows multiple instances of aws-snapper to operate on
the same Region without interfering with each other.

`--prefix` is the command line option.

### schedule_name

If you would like the report to specify which instance of
aws-snapper created the report you received, you can specify
this field. It will appear in the header of the report and
has no other effect on aws-snapper operation.

`--name` is the command line option.

### interval

If you run the script on a non-daily basis you may use this
setting to override the default run interval of 86400s. Setting
this won't change how frequently it runs, just the meaning of
the autosnap=N tag

For example: if interval=3600 and cron launches aws-snapper
hourly, N will be how many hours should be between snaps.

`--interval` is the command line option.
