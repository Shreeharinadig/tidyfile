#!/bin/bash
# Creates the S3 bucket and SQS queues in the local AWS emulator.
# Runs automatically when the emulator is ready (mounted into ready.d).
set -euo pipefail

awslocal s3 mb s3://tidyfile-files

DLQ_URL=$(awslocal sqs create-queue --queue-name tidyfile-jobs-dlq --query QueueUrl --output text)
DLQ_ARN=$(awslocal sqs get-queue-attributes --queue-url "$DLQ_URL" \
  --attribute-names QueueArn --query Attributes.QueueArn --output text)

cat > /tmp/main-queue-attributes.json <<EOF
{"RedrivePolicy": "{\"deadLetterTargetArn\":\"$DLQ_ARN\",\"maxReceiveCount\":\"3\"}"}
EOF

awslocal sqs create-queue --queue-name tidyfile-jobs --attributes file:///tmp/main-queue-attributes.json
echo "tidyfile: bucket and queues created"
