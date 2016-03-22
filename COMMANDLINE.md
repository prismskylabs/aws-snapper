# Command Line Mode

> **Note:** You really, really, really should be running this as an 
> AWS Lambda function.
> 
> AWS Lambda lets you run the snapshot job as needed without a 
> server, virtual machine, or EC2 instance. It just runs In The 
> Cloud magically. It costs a **fraction of a cent per month** to 
> run this multiple times per day, compared to the 
> dollars-per-month for the least-expensive EC2 instance.

## Configuration

There are several [command line options](OPTIONS.md) that you can use
to alter the default behavior.

The snapshot schedule is managed by [EC2 tags](TAGS.md) on the
instances and volumes themselves.

## Authentication

aws-snapper authenticates using 
[botocore](http://botocore.readthedocs.org), so there's no reason 
to give it credentials directly.

If you are running it on an EC2 instance, you should run it from an 
instance with an instance profile associated with an IAM role; This 
way, no credentials will be stored on the EC2 instance itself. See 
[IAM Roles for Amazon 
EC2](http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html) 
for more details.

If you are running it on a non-EC2 platform, you should install the 
AWS CLI and use its `aws configure` to store your Access Key ID and 
Secret Access Key in `~/.aws`. See ["Configuring the AWS Command 
Line 
Interface"](http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html) 
for more details.

## Examples

Run across all instances in the default AWS CLI region:

    $ ./aws-snapper.py

Same as above, for instances in multiple Regions:

    $ ./aws-snapper.py us-west-2 eu-central-1 ap-northeast-1

Run across instances in default Region using a custom tag prefix:

    $ ./aws-snapper.py --prefix QA_snaps

Use default settings but send a report via SNS when finished:

    $ ./aws-snapper.py --sns-arn 
arn:aws:sns:us-east-1:123456789012:maintenance-alerts

Everything at once:

    $ ./aws-snapper.py --sns-arn arn:aws:sns:us-east-1:123456789012:maintenance-alerts
            --sns-region us-east-1 --prefix StagingSnapshotter eu-central-1 ap-northeast-1
            --name "Staging Hourly" --interval 3600
