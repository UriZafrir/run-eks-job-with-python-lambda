import boto3
from kubernetes import client
import yaml
from botocore.exceptions import ClientError
import os
from eks_token import get_token
import logging
import tempfile
import base64

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    cluster_name = "eks"
    region = "il-central-1"
    namespace = "default"
    manifest_file = os.path.join(os.path.dirname(__file__), "job_manifest.yaml")

    try:
        logger.info("Starting Lambda handler.")
        
        # Step 1: Initialize EKS client and retrieve cluster details
        eks_client = boto3.client("eks", region_name=region)
        logger.info(f"Retrieving EKS cluster details for cluster: {cluster_name}")
        
        cluster_info = eks_client.describe_cluster(name=cluster_name)
        logger.info(f"EKS cluster details retrieved: {cluster_info}")

        cluster_endpoint = cluster_info["cluster"]["endpoint"]
        cluster_cert = cluster_info["cluster"]["certificateAuthority"]["data"]
        logger.info(f"Cluster endpoint: {cluster_endpoint}")
        logger.info(f"Cluster certificate (base64-encoded): {cluster_cert}")

        # Step 2: Generate authentication token
        logger.info("Generating authentication token for Kubernetes.")
        token = get_token(cluster_name)['status']['token']
        logger.info(f"Authentication token generated successfully: {token[:10]}...")  # Mask token for security

        # Step 3: Configure Kubernetes client
        logger.info("Configuring Kubernetes client.")
        configuration = client.Configuration()
        configuration.host = cluster_endpoint

        # Write the CA cert to a temporary file
        logger.info("Decoding and writing CA certificate to temporary file.")
        with tempfile.NamedTemporaryFile(delete=False) as temp_cert:
            temp_cert.write(base64.b64decode(cluster_cert))
            temp_cert_path = temp_cert.name
            logger.info(f"CA certificate written to: {temp_cert_path}")

        # Step 4: Load Kubernetes job manifest
        logger.info(f"Loading job manifest from file: {manifest_file}")
        if not os.path.exists(manifest_file):
            logger.error(f"Manifest file does not exist: {manifest_file}")
            raise FileNotFoundError(f"Manifest file not found: {manifest_file}")
        
        with open(manifest_file, "r") as f:
            job_manifest = yaml.safe_load(f)
        logger.info(f"Job manifest loaded successfully: {job_manifest}")

        # Step 5: load Configuration to the client
        configuration.ssl_ca_cert = temp_cert_path
        configuration.api_key = {"authorization": f"Bearer {token}"}
        client.Configuration.set_default(configuration)
        logger.info(f"Full Configuration: {vars(configuration)}")


        # logger.info("Attempting to list pods in the namespace.")
        # v1 = client.CoreV1Api()
        
        # try:
        #     pods = v1.list_namespaced_pod(namespace)
        #     logger.info(f"Successfully listed pods. Count: {len(pods.items)}")
        #     return {"statusCode": 200, "body": f"Successfully listed {len(pods.items)} pods in namespace {namespace}"}
        # except client.rest.ApiException as e:
        #     logger.error(f"Kubernetes API error: {e.reason}")
        #     logger.error(f"HTTP response body: {e.body}")
        #     raise
        
        # Step 6: Create Kubernetes job
        logger.info("Creating Kubernetes job.")
        batch_v1 = client.BatchV1Api()

        try:
            response = batch_v1.create_namespaced_job(namespace=namespace, body=job_manifest)
            logger.info(f"Job created successfully: {response.metadata.name}")
        except client.rest.ApiException as e:
            logger.error(f"Kubernetes API error: {e.reason}")
            logger.error(f"HTTP response body: {e.body}")
            raise

        # Step 7: Clean up temporary certificate file
        logger.info("Cleaning up temporary CA certificate file.")
        os.unlink(temp_cert_path)

        return {"statusCode": 200, "body": f"Job created successfully: {response.metadata.name}"}

    except ClientError as e:
        logger.error(f"Failed to describe cluster: {str(e)}")
        return {"statusCode": 500, "body": f"Failed to describe cluster: {str(e)}"}
    except client.rest.ApiException as e:
        logger.error(f"Kubernetes API error: {str(e)}")
        return {"statusCode": 500, "body": f"Kubernetes API error: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {"statusCode": 500, "body": f"Unexpected error: {str(e)}"}
