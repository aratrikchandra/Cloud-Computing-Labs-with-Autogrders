import json
import boto3
from botocore.exceptions import ClientError

def read_data():
    try:
        with open('data.json') as f:
            return json.load(f)
    except Exception as e:
        return {"error": f"Error reading data.json: {e}"}

def get_iam_client(access_key, secret_key, region):
    try:
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        return session.client('iam')
    except Exception as e:
        return None

def get_user_name(iam_client, access_key):
    try:
        response = iam_client.get_access_key_last_used(AccessKeyId=access_key)
        return response['UserName']
    except ClientError as e:
        return None

def check_policy_attachment(iam_client, user_name, policy_arn):
    try:
        response = iam_client.list_attached_user_policies(UserName=user_name)
        for policy in response.get('AttachedPolicies', []):
            if policy['PolicyArn'] == policy_arn:
                return True
        return False
    except ClientError as e:
        return False

def simulate_actions(iam_client, user_arn, actions):
    try:
        response = iam_client.simulate_principal_policy(
            PolicySourceArn=user_arn,
            ActionNames=actions
        )
        return response.get('EvaluationResults', [])
    except ClientError as e:
        return None

def evaluate_test_case(iam_client, user_arn, allowed_actions, denied_actions, testid):
    result = {
        'testid': testid,
        'status': 'failure',
        'score': 0,
        'maximum marks': 1,
        'message': ''
    }
    try:
        # Check allowed actions
        if allowed_actions:
            allowed_results = simulate_actions(iam_client, user_arn, allowed_actions)
            if allowed_results is None:
                result['message'] = 'Failed to simulate allowed actions'
                return result
            for res in allowed_results:
                if res.get('EvalDecision') != 'allowed':
                    result['message'] = 'Permissions not correctly configured'
                    return result
        
        # Check denied actions
        if denied_actions:
            denied_results = simulate_actions(iam_client, user_arn, denied_actions)
            if denied_results is None:
                result['message'] = 'Failed to simulate denied actions'
                return result
            for res in denied_results:
                if res.get('EvalDecision') == 'allowed':
                    result['message'] = 'Permissions not correctly configured'
                    return result
        
        result['status'] = 'success'
        result['score'] = 1
        result['message'] = 'Permissions correctly configured'
    except Exception as e:
        result['message'] = f"Test case error: {str(e)}"
    return result

def main():
    data = []
    student_data = read_data()
    if not student_data or 'ACCESS_KEY_ID' not in student_data:
        data.append({
            'testid': 'Policy Attachment',
            'status': 'failure',
            'score': 0,
            'maximum marks': 1,
            'message': 'Invalid data.json'
        })
        test_cases = ['S3', 'EC2', 'Load Balancer', 'Lambda', 'CloudWatch']
        for tc in test_cases:
            data.append({
                'testid': f"{tc} Permissions",
                'status': 'failure',
                'score': 0,
                'maximum marks': 1,
                'message': 'Invalid data.json'
            })
        with open('evaluate.json', 'w') as f:
            json.dump({'data': data}, f, indent=4)
        return
    
    access_key = student_data['ACCESS_KEY_ID']
    secret_key = student_data['SECRET_ACCESS_KEY']
    region = student_data['region']
    policy_arn = student_data['policy-arn']

    iam_client = get_iam_client(access_key, secret_key, region)
    if not iam_client:
        data.append({
            'testid': 'Policy Attachment',
            'status': 'failure',
            'score': 0,
            'maximum marks': 1,
            'message': 'Failed to initialize IAM client'
        })
        test_cases = ['S3', 'EC2', 'Load Balancer', 'Lambda', 'CloudWatch']
        for tc in test_cases:
            data.append({
                'testid': f"{tc} Permissions",
                'status': 'failure',
                'score': 0,
                'maximum marks': 1,
                'message': 'IAM client initialization failed'
            })
        with open('evaluate.json', 'w') as f:
            json.dump({'data': data}, f, indent=4)
        return
    
    user_name = get_user_name(iam_client, access_key)
    if not user_name:
        data.append({
            'testid': 'Policy Attachment',
            'status': 'failure',
            'score': 0,
            'maximum marks': 1,
            'message': 'Failed to retrieve user name from access key'
        })
        test_cases = ['S3', 'EC2', 'Load Balancer', 'Lambda', 'CloudWatch']
        for tc in test_cases:
            data.append({
                'testid': f"{tc} Permissions",
                'status': 'failure',
                'score': 0,
                'maximum marks': 1,
                'message': 'User name retrieval failed'
            })
        with open('evaluate.json', 'w') as f:
            json.dump({'data': data}, f, indent=4)
        return
    
    is_attached = check_policy_attachment(iam_client, user_name, policy_arn)
    policy_test = {
        'testid': 'Policy Attachment',
        'status': 'success' if is_attached else 'failure',
        'score': 1 if is_attached else 0,
        'maximum marks': 1,
        'message': 'Policy is attached' if is_attached else f'Policy {policy_arn} is not attached to user {user_name}'
    }
    data.append(policy_test)

    if not is_attached:
        test_cases = ['S3', 'EC2', 'Load Balancer', 'Lambda', 'CloudWatch']
        for tc in test_cases:
            data.append({
                'testid': f"{tc} Permissions",
                'status': 'failure',
                'score': 0,
                'maximum marks': 1,
                'message': f'Policy {policy_arn} is not attached to user {user_name}'
            })
        with open('evaluate.json', 'w') as f:
            json.dump({'data': data}, f, indent=4)
        return
    
    try:
        user = iam_client.get_user(UserName=user_name)
        user_arn = user['User']['Arn']
    except ClientError as e:
        data.append({
            'testid': 'Policy Attachment',
            'status': 'failure',
            'score': 0,
            'maximum marks': 1,
            'message': f'Failed to get user ARN: {str(e)}'
        })
        test_cases = ['S3', 'EC2', 'Load Balancer', 'Lambda', 'CloudWatch']
        for tc in test_cases:
            data.append({
                'testid': f"{tc} Permissions",
                'status': 'failure',
                'score': 0,
                'maximum marks': 1,
                'message': 'User ARN retrieval failed'
            })
        with open('evaluate.json', 'w') as f:
            json.dump({'data': data}, f, indent=4)
        return
    
    test_cases = [
        {
            'testid': 'S3 Permissions',
            'allowed': [ "s3:ListAllMyBuckets", "s3:CreateBucket", "s3:GetObject", "s3:DeleteObject"],
            'denied': ['s3:DeleteBucket', 's3:PutObject']
        },
        {
            'testid': 'EC2 Permissions',
            'allowed': ['ec2:DescribeInstances', 'ec2:DescribeVpcs', 'ec2:DescribeSecurityGroups'],
            'denied': [ "ec2:StartInstances", "ec2:StopInstances"]
        },
        {
            'testid': 'Load Balancer Permissions',
            'allowed': [ "elasticloadbalancing:CreateLoadBalancer", "elasticloadbalancing:DeleteLoadBalancer"],
            'denied': ["elasticloadbalancing:DescribeLoadBalancers"]
        },
        {
            'testid': 'Lambda Permissions',
            'allowed': [ "lambda:CreateFunction", "lambda:InvokeFunction"],
            'denied': ["lambda:DeleteFunction", "lambda:UpdateFunctionCode"]
        },
        {
            'testid': 'CloudWatch Permissions',
            'allowed': [ "logs:CreateLogGroup", "logs:GetLogEvents"],
            'denied': ["logs:DeleteLogGroup", "logs:PutLogEvents"]
        }
    ]

    for tc in test_cases:
        test_result = evaluate_test_case(
            iam_client,
            user_arn,
            tc['allowed'],
            tc['denied'],
            tc['testid']
        )
        data.append(test_result)
    
    with open('../evaluate.json', 'w') as f:
        json.dump({'data': data}, f, indent=4)

if __name__ == '__main__':
    main()