import requests
from bs4 import BeautifulSoup
import json
import boto3
import cv2
import os
from botocore.exceptions import NoCredentialsError, ClientError
import time


def upload_image_and_get_id(data):
    result = {
        "testid": "Photo Upload Check",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }
    try:
        # Read the application configuration
        with open('data.json', 'r') as file:
            config_data = json.load(file)
            url = f"http://{config_data['public_ip']}:{config_data['port']}/"
        # Check if the URL is accessible
        start_time = time.time()
        while time.time() - start_time < 5:
            try: 
                response = requests.get(url)
                if response.status_code == 200: 
                    break 
            except requests.exceptions.RequestException: 
                time.sleep(1) 
        else: 
            result['message'] = f"Error: Failed to connect to the application at {url} within 5 seconds." 
            data.append(result) 
            return None

        # Upload the image
        files = {'file': ('valid_image.jpg', open('valid_image.jpg', 'rb'), 'image/jpeg')}
        response = requests.post(url, files=files)

        # Extract the image ID from the response URL
        if response.url and 'image_id' in response.url:
            image_id = response.url.split('image_id=')[1]
            # print(image_id)
            result['status'] = "success"
            result['score'] = 1
            result['message'] = "Image uploaded successfully"
            data.append(result)
            return image_id

        # If no image_id found in the response URL
        result['message'] = "Error: Image ID not found in the response."
        data.append(result)
        return None

    except FileNotFoundError:
        result['message'] = "Error: 'data.json' file not found."
        data.append(result)
        return None
    except Exception as e:
        result['message'] = f"An error occurred: {e}"
        data.append(result)
        return None



def check_bucket(data, uploaded_image_name):
    result = {
        "testid": "S3 Bucket Check",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }
    try:
        # Load the data.json file
        with open('data.json') as f:
            config_data = json.load(f)

        # Extract the necessary information
        access_key = config_data['INSTRUCTOR Access key ID']
        secret_key = config_data['INSTRUCTOR Secret Access Key']
        bucket_name = config_data['source s3 bucket name']
        region = config_data['Region']

        # Create a session using the provided IAM user credentials
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )

        # Create an S3 resource object using the above session
        s3 = session.resource('s3')

        # Check if the bucket exists
        try:
            s3.meta.client.head_bucket(Bucket=bucket_name)
        except ClientError:
            result["message"]= f'Bucket {bucket_name} does not exist.'
            data.append(result)
            return False
        # Download the uploaded image
        try:
            s3.Bucket(bucket_name).download_file(uploaded_image_name, 'uploaded_image.jpg')
        except NoCredentialsError:
            result["message"]= "Credentials not available"
            data.append(result)
            return False
        except ClientError:
            result["message"]= f"Object {uploaded_image_name} does not exist in the bucket."
            data.append(result)
            return False

        # Load the input image and the downloaded image
        input_image = cv2.imread('valid_image.jpg')
        uploaded_image = cv2.imread('uploaded_image.jpg')

        # Resize the input image to match the size of the uploaded image
        resized_input_image = cv2.resize(input_image, (uploaded_image.shape[1], uploaded_image.shape[0]))

        # Calculate the histograms of the images
        hist_input_image = cv2.calcHist([resized_input_image], [0], None, [256], [0, 256])
        hist_uploaded_image = cv2.calcHist([uploaded_image], [0], None, [256], [0, 256])

        # Normalize the histograms
        hist_input_image = cv2.normalize(hist_input_image, hist_input_image)
        hist_uploaded_image = cv2.normalize(hist_uploaded_image, hist_uploaded_image)

        # Compare the histograms
        comparison = cv2.compareHist(hist_input_image, hist_uploaded_image, cv2.HISTCMP_CORREL)
        
        if comparison >= 0.9:
            result['status'] = "success"
            result['score'] = 1
            result["message"]= "Bucket Checked Successfully"
            data.append(result)
            return True
        else:
            result["message"]= "The input image and the uploaded image are not the same."
            data.append(result)
            return False

    except FileNotFoundError:
        result["message"]= "The file 'data.json' was not found."
    except KeyError as e:
        result["message"]= f"The key {e} was not found in the data."
    except Exception as e:
        result["message"]= f"An error occurred: {e}"

    data.append(result)
    return False

def check_label_bucket(data, image_name):
    result = {
        "testid": "Label Bucket Check",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }
    try:
        # Load the data.json file
        with open('data.json') as f:
            config_data = json.load(f)

        # Extract the necessary information
        access_key = config_data['INSTRUCTOR Access key ID']
        secret_key = config_data['INSTRUCTOR Secret Access Key']
        bucket_name = config_data['labels s3 bucket name']
        region = config_data['Region']

        # Create a session using the provided IAM user credentials
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )

        # Create an S3 resource object using the above session
        s3 = session.resource('s3')

        # Check if the bucket exists
        try:
            s3.meta.client.head_bucket(Bucket=bucket_name)
        except ClientError:
            result["message"] = f'Bucket {bucket_name} does not exist.'
            data.append(result)
            return False

        # Check if the labels for the image exist
        try:
            labels_object = s3.Object(bucket_name, f"labels/{image_name}.json").get()
            stored_labels = json.loads(labels_object['Body'].read().decode())['Labels']
        except NoCredentialsError:
            result["message"] = "Credentials not available"
            data.append(result)
            return False
        except ClientError:
            result["message"] = f"Labels for {image_name} do not exist in labels S3 bucket."
            data.append(result)
            return False

        result['status'] = "success"
        result['score'] = 1
        result["message"] = "Label Bucket Checked Successfully"
        data.append(result)
        return True

    except FileNotFoundError:
        result["message"] = "The file 'data.json' was not found."
    except KeyError as e:
        result["message"] = f"The key {e} was not found in the data."
    except Exception as e:
        result["message"] = f"An error occurred: {e}"

    data.append(result)
    return False


def check_lambda_trigger(data, image):
    result = {
        "testid": "Lambda Trigger Check",
        "status": "failure",
        "score": 0,
        "maximum marks": 1,
        "message": ""
    }
    try:
        # Load the data.json file
        with open('data.json') as f:
            config_data = json.load(f)

        # Set AWS credentials
        os.environ['AWS_ACCESS_KEY_ID'] = config_data['INSTRUCTOR Access key ID']
        os.environ['AWS_SECRET_ACCESS_KEY'] = config_data['INSTRUCTOR Secret Access Key']
        os.environ['AWS_DEFAULT_REGION'] = config_data['Region']

        # Set log group name
        log_group_name = f'/aws/lambda/{config_data["Lambda Function Name"]}'

        # Fetch the last 5 log streams
        client = boto3.client('logs')
        streams_response = client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )

        log_lines = []

        # Fetch logs for each stream
        for stream in streams_response['logStreams']:
            stream_name = stream['logStreamName']
            response = client.get_log_events(
                logGroupName=log_group_name,
                logStreamName=stream_name
            )
            
            for event in response['events']:
                log_lines.append(event['message'])


        # Check if logs contain processing image message
        processing_message = f'Processing image: {image} from bucket: {config_data["source s3 bucket name"]}'
        if not any(processing_message in log_msg for log_msg in log_lines):
            result["message"] = f'Initial log not found for image: {image}'
            data.append(result)
            return

        # Check if logs contain generated labels message
        generated_labels_message = f'Generated labels for image: {image}'
        if not any(generated_labels_message in log_msg for log_msg in log_lines):
            result["message"]=f'Generated labels log not found for image: {image}'
            data.append(result)
            return
        
        # Check if logs contain successful processing message
        success_message = f'Successfully processed labels for image: {image} and stored in bucket: {config_data["labels s3 bucket name"]}'
        if not any(success_message in log_msg for log_msg in log_lines):
            result["message"]=f'Successful processing log not found for image: {image}'
            data.append(result)
            return

        result['status'] = "success"
        result['score'] = 1
        result["message"] = "Lambda Trigger Checked Successfully"
        data.append(result)
        return 

    except FileNotFoundError:
        result["message"] = "The file 'data.json' was not found."
    except KeyError as e:
        result["message"] = f"The key {e} was not found in the data."
    except Exception as e:
        result["message"] = f"An error occurred: {e}"

    data.append(result)


def main():
    overall = {"data": []}
    data = []
    default_bucket={
            "testid": "S3 Bucket Check",
            "status": "failure",
            "score": 0,
            "maximum marks": 1,
            "message": "Image ID not found, skipping Source Bucket check."
        }
    default_label={
                "testid": "Label Bucket Check",
                "status": "failure",
                "score": 0,
                "maximum marks": 1,
                "message": "Source Bucket check failed, skipping Label Bucket check."
            }
    default_lambda={
                "testid": "Lambda Trigger Check",
                "status": "failure",
                "score": 0,
                "maximum marks": 1,
                "message": "Source Bucket check failed, skipping Lambda trigger check."
            }
    # Example usage
    image_id = upload_image_and_get_id(data)
    if image_id:
        flag = check_bucket(data, image_id)
        if flag:
            check_label_bucket(data, image_id)
            time.sleep(5)
            check_lambda_trigger(data,image_id)
        else:
            data.append(default_label)
            data.append(default_lambda)
    else:
        data.append(default_bucket)
        data.append(default_label)
        data.append(default_lambda)

    overall['data'] = data
    # Save the result to evaluate.json
    with open('../evaluate.json', 'w') as f:
        json.dump(overall, f, indent=4)

if __name__ == "__main__":
    main()
