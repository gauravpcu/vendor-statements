# EC2 Deployment Commands Log

This file documents the exact commands executed during our recent EC2 deployment process on August 4, 2025. This serves as a reference for future deployments and troubleshooting.

## Initial Deployment Attempt

```bash
# Check the EC2 instance status
./ec2-management.sh status

# Attempt to update the application
./ec2-management.sh update
```

## Encountered Issue: Disk Space

During the update process, we encountered a "no space left on device" error when Docker tried to pull the latest image. The EC2 instance had insufficient disk space.

## Disk Resize Process

```bash
# Check the resize_ec2_disk.sh script
cat resize_ec2_disk.sh

# Execute the resize script to increase the EBS volume size to 32GB
./resize_ec2_disk.sh

# SSH into the EC2 instance to complete the filesystem resize
# (These commands were executed on the EC2 instance)
sudo growpart /dev/nvme0n1 1
sudo xfs_growfs -d /

# Verify the resize worked
df -h
```

The disk was successfully resized from 8GB to 32GB, with usage decreasing from ~37% to ~10%.

## Docker Cleanup

```bash
# (On EC2 instance) Clean up Docker resources to free additional space
sudo docker system prune -af
```

## Docker Build Fix

We modified the `deploy_to_ecr.sh` script to specify the AMD64 platform for EC2 compatibility:

```bash
# Changed from
# docker build -t $ECR_REPOSITORY:$IMAGE_TAG .
# to
docker build --platform linux/amd64 -t $ECR_REPOSITORY:$IMAGE_TAG .
```

This ensures that the Docker image is built for the correct architecture for our EC2 instance.

## Successful Deployment

```bash
# Run the update command again after disk resize
./ec2-management.sh update
```

The update was successful, with the application container started with ID ababfd3923e7.

## Verification

```bash
# Verify the application is running correctly
./ec2-management.sh status
```

The status command showed that the application was running correctly at http://44.211.183.42:8000

## Summary of Key Modifications

1. **deploy_to_ecr.sh**: Added `--platform linux/amd64` to the Docker build command to ensure EC2 compatibility
2. **EBS Volume**: Increased from 8GB to 32GB using resize_ec2_disk.sh
3. **Filesystem**: Extended using XFS-specific tools (xfs_growfs) rather than ext4 tools (resize2fs)

## Future Update Process

For future updates, follow these steps:

1. Check available disk space: `./ec2-management.sh ssh "df -h"`
2. Clean Docker resources if needed: `./ec2-management.sh ssh "sudo docker system prune -af"`
3. Update the application: `./ec2-management.sh update`
4. Verify deployment: `./ec2-management.sh status`

If disk space becomes an issue again, follow the disk resize process documented above.
